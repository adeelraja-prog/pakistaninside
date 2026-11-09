import asyncio
import hashlib
import os
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageOps

from engine.designer import DesignerAgent


class VideoAgent:
    """Create 9:16 narrated reels with motion, animated ticker and progress line."""

    WIDTH = 1080
    HEIGHT = 1920
    VOICE = os.getenv("URDU_TTS_VOICE", "ur-PK-UzmaNeural")

    def __init__(self):
        self.designer = DesignerAgent()
        self.output_dir = Path("assets/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def _make_voice(self, text, output_path):
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.VOICE,
            rate=os.getenv("URDU_TTS_RATE", "+0%"),
            volume="+0%",
        )
        await communicate.save(str(output_path))

    @staticmethod
    def _duration(audio_path):
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
            ],
            check=True, capture_output=True, text=True,
        )
        return max(8, min(60, float(result.stdout.strip()) + 1.0))

    def _render_frame(self, story, output_path):
        photo = self.designer._download_image(story.get("image_url", ""))
        frame = ImageOps.fit(
            photo,
            (self.WIDTH, self.HEIGHT),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.35),
        ).convert("RGBA")

        shade = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        shade_draw = ImageDraw.Draw(shade)
        for y in range(self.HEIGHT):
            alpha = int(25 + 195 * max(0, (y - 620) / 1300))
            shade_draw.line((0, y, self.WIDTH, y), fill=(5, 12, 22, min(225, alpha)))
        frame = Image.alpha_composite(frame, shade)
        draw = ImageDraw.Draw(frame)

        draw.rectangle((0, 0, self.WIDTH, 14), fill=self.designer.RED)
        draw.rounded_rectangle((54, 54, 500, 138), radius=12, fill=(5, 17, 32, 225))
        draw.text((82, 75), "ADEEL RAJA", font=self.designer.english_font(42), fill=self.designer.WHITE)

        tag = self.designer.CATEGORY_LABELS.get(str(story.get("tag", "GENERAL")).upper(), "LATEST NEWS")
        draw.text((1010, 1040), tag, font=self.designer.english_font(27), fill=self.designer.WHITE, anchor="ra")

        headline = str(story.get("headline") or "")
        font = self.designer.urdu_font(65)
        lines = self.designer._wrap(draw, headline, font, 940, direction="rtl")
        if len(lines) > 4:
            font = self.designer.urdu_font(53)
            lines = self.designer._wrap(draw, headline, font, 940, direction="rtl")
        if len(lines) > 4:
            raise ValueError("Urdu reel headline exceeds four lines; shorten before rendering")

        y = 1110
        for line in lines:
            draw.text(
                (1010, y), line, font=font, fill=self.designer.WHITE,
                anchor="ra", direction="rtl", language="ur",
            )
            y += int(font.size * 1.5)

        summary = str(story.get("body") or story.get("urdu_text") or "")[:280]
        body_font = self.designer.urdu_font(36)
        body_lines = self.designer._wrap(draw, summary, body_font, 940, direction="rtl")[:5]
        y += 24
        for line in body_lines:
            if y > 1740:
                break
            draw.text(
                (1010, y), line, font=body_font, fill=self.designer.MUTED,
                anchor="ra", direction="rtl", language="ur",
            )
            y += 56

        draw.line((54, 1810, 1026, 1810), fill=(220, 230, 240, 170), width=2)
        draw.text(
            (54, 1845), str(story.get("source_name") or "NEWS SOURCE")[:32].upper(),
            font=self.designer.english_font(20), fill=self.designer.MUTED,
        )
        draw.text(
            (1026, 1840), "ADEEL RAJA", font=self.designer.english_font(24),
            fill=self.designer.WHITE, anchor="ra",
        )
        frame.convert("RGB").save(output_path, quality=94)

    def generate_reel(self, story):
        key = str(story.get("source_url") or story.get("headline") or "story")
        slug = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
        frame_path = self.output_dir / f"frame_{slug}.jpg"
        audio_path = self.output_dir / f"voice_{slug}.mp3"
        video_path = self.output_dir / f"adeel_raja_reel_{slug}.mp4"

        try:
            self._render_frame(story, frame_path)
            narration = (
                f"{story.get('headline', '')}. "
                f"{story.get('body') or story.get('urdu_text', '')}"
            )
            asyncio.run(self._make_voice(narration[:1600], audio_path))
            duration = self._duration(audio_path)
            frames = int(duration * 30)

            # Zoom movement + animated progress line + continuously scrolling newsroom ticker.
            ticker = "ADEEL RAJA  |  PAKISTAN NEWS  |  COURTS  |  PUBLIC INTEREST  |  WORLD"
            escaped_ticker = ticker.replace("'", "\\'")
            filter_graph = (
                f"zoompan=z='min(zoom+0.00045,1.07)':d={frames}:s=1080x1920:fps=30,"
                "format=yuv420p,"
                "drawbox=x=0:y=0:w='18*t':h=9:color=0xCA232F@0.98:t=fill,"
                "drawbox=x=0:y=1850:w=1080:h=70:color=0xCA232F@0.96:t=fill,"
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{escaped_ticker}':fontcolor=white:fontsize=25:"
                "x=w-mod(t*145\\,w+tw):y=1870"
            )

            command = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(frame_path),
                "-i", str(audio_path),
                "-vf", filter_graph,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "128k", "-shortest", "-t", str(duration),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path),
            ]
            subprocess.run(command, check=True, timeout=240)
            if not video_path.is_file() or video_path.stat().st_size < 50_000:
                raise RuntimeError("FFmpeg did not produce a valid reel file")
            return str(video_path)
        finally:
            frame_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)

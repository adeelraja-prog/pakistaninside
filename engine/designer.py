import glob
import hashlib
import os
import re
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, features


class DesignerAgent:
    WIDTH = 1080
    HEIGHT = 1350
    OUTPUT_DIR = "assets/output"

    NAVY = (8, 18, 32)
    WHITE = (250, 250, 247)
    MUTED = (210, 219, 228)
    RED = (220, 38, 52)
    GOLD = (218, 181, 99)

    CATEGORY_LABELS = {
        "POLITICS": "POLITICS",
        "COURT": "COURTS & JUSTICE",
        "PUBLIC_INTEREST": "PUBLIC INTEREST",
        "ECONOMY": "ECONOMY",
        "DEFENSE": "NATIONAL SECURITY",
        "HEALTH": "HEALTH",
        "TECH": "TECHNOLOGY",
        "WORLD": "WORLD",
        "GENERAL": "LATEST NEWS",
    }

    def __init__(self):
        self.urdu_font_path = self._find_font([
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/**/*Naskh*Regular*.ttf",
            "/usr/share/fonts/**/*Nastaliq*.ttf",
        ])
        self.english_font_path = self._find_font([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/**/*DejaVuSans-Bold.ttf",
        ])
        if not features.check("raqm"):
            raise RuntimeError("Pillow RAQM is required for correct Urdu shaping; refusing broken Urdu poster.")
        if not self.urdu_font_path:
            raise RuntimeError("No supported Urdu font found. Install fonts-noto-core before rendering.")

    @staticmethod
    def _find_font(patterns):
        for pattern in patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                return matches[0]
        return None

    def urdu_font(self, size):
        return ImageFont.truetype(self.urdu_font_path, size, layout_engine=ImageFont.Layout.RAQM)

    def english_font(self, size):
        if not self.english_font_path:
            raise RuntimeError("English display font missing")
        return ImageFont.truetype(self.english_font_path, size)

    @staticmethod
    def _wrap(draw, text, font, max_width, direction=None):
        words = str(text or "").split()
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            kwargs = {"direction": direction} if direction else {}
            width = draw.textbbox((0, 0), candidate, font=font, **kwargs)[2]
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _download_image(self, url):
        if not url or not url.startswith("https://"):
            raise ValueError("No HTTPS editorial image URL supplied; poster publication blocked")
        host = urlparse(url).hostname or ""
        if not host or host in ("localhost", "127.0.0.1"):
            raise ValueError("Invalid image host")
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "AdeelRajaNewsroom/1.0"},
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            raise ValueError(f"Image URL did not return an image (content-type={content_type})")
        if len(response.content) > 12 * 1024 * 1024:
            raise ValueError("Image exceeds 12 MB safety limit")
        image = Image.open(BytesIO(response.content)).convert("RGB")
        if image.width < 500 or image.height < 300:
            raise ValueError("Editorial image resolution is too small")
        return image

    @staticmethod
    def _cover_crop(image, size):
        return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.38))

    def generate_card(self, data):
        headline = str(data.get("headline") or "").strip()
        body = str(data.get("body") or data.get("urdu_text") or "").strip()
        if not headline or not re.search(r"[\u0600-\u06FF]", headline):
            raise ValueError("A valid Urdu headline is required")
        if data.get("language") != "ur":
            raise ValueError("Urdu-first poster gate failed")

        # A relevant image is mandatory. No empty colour-card fallback.
        photo = self._download_image(data.get("image_url", ""))
        tag = str(data.get("tag") or "GENERAL").upper()
        category = self.CATEGORY_LABELS.get(tag, "LATEST NEWS")

        image = self._cover_crop(photo, (self.WIDTH, 790)).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        for y in range(790):
            alpha = int(20 + 210 * (y / 790) ** 1.8)
            overlay_draw.line((0, y, self.WIDTH, y), fill=(4, 12, 24, alpha))
        image = Image.alpha_composite(image, overlay)

        canvas = Image.new("RGBA", (self.WIDTH, self.HEIGHT), self.NAVY + (255,))
        canvas.alpha_composite(image, (0, 0))
        draw = ImageDraw.Draw(canvas)

        # Restrained international-newsroom identity.
        draw.rectangle((0, 0, self.WIDTH, 12), fill=self.RED)
        draw.rounded_rectangle((52, 48, 430, 112), radius=12, fill=(7, 18, 34, 220))
        draw.text((76, 60), "ADEEL RAJA", font=self.english_font(34), fill=self.WHITE)
        draw.text((1025, 70), "NEWS", font=self.english_font(27), fill=self.GOLD, anchor="ra")

        if data.get("urgency") == "POTENTIAL_BREAKING":
            draw.rounded_rectangle((56, 660, 340, 724), radius=8, fill=self.RED)
            draw.text((198, 692), "BREAKING NEWS", font=self.english_font(25), fill=self.WHITE, anchor="mm")

        # Lower information panel.
        draw.rectangle((0, 790, self.WIDTH, self.HEIGHT), fill=self.NAVY)
        draw.rectangle((56, 838, 62, 900), fill=self.RED)
        draw.text((100, 850), category, font=self.english_font(25), fill=self.GOLD)

        headline_font = None
        headline_lines = None
        for size in (66, 60, 54, 48, 44):
            candidate_font = self.urdu_font(size)
            candidate_lines = self._wrap(draw, headline, candidate_font, 940, direction="rtl")
            if len(candidate_lines) <= 3:
                headline_font, headline_lines = candidate_font, candidate_lines
                break
        if headline_font is None:
            raise ValueError("Headline is too long for the premium poster layout; editor must shorten it")

        y = 930
        for line in headline_lines:
            draw.text((1020, y), line, font=headline_font, fill=self.WHITE, anchor="ra", direction="rtl", language="ur")
            y += int(headline_font.size * 1.42)

        body_text = body[:230]
        body_font = self.urdu_font(31)
        body_lines = self._wrap(draw, body_text, body_font, 930, direction="rtl")
        body_lines = body_lines[:2]
        y += 8
        for line in body_lines:
            if y > 1190:
                break
            draw.text((1020, y), line, font=body_font, fill=self.MUTED, anchor="ra", direction="rtl", language="ur")
            y += 48

        source = str(data.get("source_name") or "SOURCE").upper()[:36]
        draw.line((56, 1240, 1024, 1240), fill=(57, 75, 96), width=2)
        draw.text((56, 1270), source, font=self.english_font(19), fill=self.MUTED)
        draw.text((1024, 1270), "ADEEL RAJA", font=self.english_font(22), fill=self.GOLD, anchor="ra")

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        key = data.get("source_url") or headline
        suffix = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:10]
        output_path = os.path.join(self.OUTPUT_DIR, f"adeel_raja_news_{suffix}.jpg")
        canvas.convert("RGB").save(output_path, "JPEG", quality=94, optimize=True)
        return output_path

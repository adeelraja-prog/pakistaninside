import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from engine.video import VideoAgent


class AnimatedReelRenderTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg tools required")
    def test_animated_reel_filter_produces_vertical_video(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame = root / "frame.jpg"
            audio = root / "voice.wav"
            output = root / "reel.mp4"
            Image.new("RGB", (1080, 1920), (25, 55, 85)).save(frame, quality=90)

            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:a", "pcm_s16le", str(audio),
            ], check=True, timeout=30)

            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(frame), "-i", str(audio),
                "-vf", VideoAgent.build_video_filter(30),
                "-map", "0:v:0", "-map", "1:a:0",
                "-t", "1", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                str(output),
            ], check=True, timeout=60)

            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 10_000)
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                "-of", "json", str(output),
            ], check=True, capture_output=True, text=True)
            streams = json.loads(probe.stdout)["streams"]
            video = next(stream for stream in streams if stream["codec_type"] == "video")
            self.assertEqual((video["width"], video["height"]), (1080, 1920))


if __name__ == "__main__":
    unittest.main()

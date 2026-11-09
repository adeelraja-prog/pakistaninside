import glob
import hashlib
import ipaddress
import os
import re
import socket
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, features


class DesignerAgent:
    """Premium, image-first 4:5 international newsroom poster renderer."""

    WIDTH = 1080
    HEIGHT = 1350
    OUTPUT_DIR = "assets/output"

    INK = (19, 25, 32)
    PAPER = (248, 248, 245)
    WHITE = (255, 255, 255)
    MUTED = (101, 110, 119)
    RED = (202, 35, 47)
    LINE = (222, 225, 228)

    CATEGORY_LABELS = {
        "POLITICS": "POLITICS",
        "COURT": "COURTS & JUSTICE",
        "PUBLIC_INTEREST": "PUBLIC INTEREST",
        "ECONOMY": "ECONOMY",
        "DEFENSE": "SECURITY",
        "HEALTH": "HEALTH",
        "TECH": "TECHNOLOGY",
        "WORLD": "WORLD",
        "GENERAL": "LATEST NEWS",
    }

    def __init__(self):
        self.urdu_font_path = self._find_font([
            "/usr/share/fonts/**/*NastaliqUrdu*Regular*.ttf",
            "/usr/share/fonts/**/*Nastaliq*Regular*.ttf",
            "/usr/share/fonts/**/*Naskh*Regular*.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
        ])
        self.english_font_path = self._find_font([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/**/*DejaVuSans-Bold.ttf",
        ])
        self.english_regular_path = self._find_font([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/**/*DejaVuSans.ttf",
        ])
        if not features.check("raqm"):
            raise RuntimeError("Pillow RAQM is required for correct Urdu shaping.")
        if not self.urdu_font_path:
            raise RuntimeError("No Urdu-capable Nastaliq/Naskh font found.")

    @staticmethod
    def _find_font(patterns):
        for pattern in patterns:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                return matches[0]
        return None

    def urdu_font(self, size):
        return ImageFont.truetype(self.urdu_font_path, size, layout_engine=ImageFont.Layout.RAQM)

    def english_font(self, size, regular=False):
        path = self.english_regular_path if regular else self.english_font_path
        if not path:
            raise RuntimeError("English display font missing")
        return ImageFont.truetype(path, size)

    @staticmethod
    def _public_https_url(url):
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                return False
            host = parsed.hostname.lower()
            if host in {"localhost", "localhost.localdomain"}:
                return False
            try:
                addresses = {ipaddress.ip_address(host)}
            except ValueError:
                addresses = {
                    ipaddress.ip_address(item[4][0])
                    for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
                }
            return bool(addresses) and all(address.is_global for address in addresses)
        except (ValueError, OSError):
            return False

    def _download_image(self, url):
        if not self._public_https_url(url):
            raise ValueError("A public HTTPS editorial image is required; unsafe or missing URL blocked.")
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "AdeelRajaNewsroom/2.0"},
            allow_redirects=True,
        )
        response.raise_for_status()
        if not self._public_https_url(response.url):
            raise ValueError("Image redirected to a non-public or unsafe destination.")
        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            raise ValueError(f"Image URL did not return an image (content-type={content_type})")
        if len(response.content) > 12 * 1024 * 1024:
            raise ValueError("Image exceeds 12 MB safety limit")
        image = ImageOps.exif_transpose(Image.open(BytesIO(response.content))).convert("RGB")
        if image.width < 500 or image.height < 300:
            raise ValueError("Editorial image resolution is too small")
        return image

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

    @staticmethod
    def _published_label(value):
        if not value:
            return datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y  •  PKT").upper()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y  •  PKT").upper()
        except (ValueError, TypeError):
            return datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y  •  PKT").upper()

    def generate_card(self, data):
        headline = str(data.get("headline") or "").strip()
        body = str(data.get("body") or data.get("urdu_text") or "").strip()
        if not headline or not re.search(r"[\u0600-\u06FF]", headline):
            raise ValueError("A valid Urdu headline is required")
        if data.get("language") != "ur":
            raise ValueError("Urdu-first poster gate failed")
        if not data.get("source_url"):
            raise ValueError("Source URL is mandatory")

        photo = self._download_image(data.get("image_url", ""))
        canvas = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.PAPER)
        draw = ImageDraw.Draw(canvas)

        # Clean masthead — identity is the publisher, not the old project codename.
        draw.text((58, 26), "ADEEL RAJA", font=self.english_font(43), fill=self.INK)
        draw.text((1020, 43), "INDEPENDENT NEWSROOM", font=self.english_font(17, regular=True), fill=self.MUTED, anchor="ra")
        draw.rectangle((58, 91, 1022, 97), fill=self.RED)

        # Full-width editorial photograph is the dominant visual element.
        photo = ImageOps.fit(
            photo,
            (self.WIDTH, 690),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.38),
        )
        canvas.paste(photo, (0, 110))
        draw = ImageDraw.Draw(canvas)

        # Subtle lower gradient keeps the image legible without hiding it.
        gradient = Image.new("RGBA", (self.WIDTH, 230), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gradient)
        for y in range(230):
            alpha = int(8 + 145 * (y / 229) ** 1.8)
            gd.line((0, y, self.WIDTH, y), fill=(7, 12, 18, alpha))
        canvas_rgba = canvas.convert("RGBA")
        canvas_rgba.alpha_composite(gradient, (0, 570))
        canvas = canvas_rgba.convert("RGB")
        draw = ImageDraw.Draw(canvas)

        category = self.CATEGORY_LABELS.get(str(data.get("tag", "GENERAL")).upper(), "LATEST NEWS")
        draw.rounded_rectangle((58, 145, 390, 205), radius=8, fill=self.RED)
        draw.text((82, 163), category, font=self.english_font(22), fill=self.WHITE)

        if data.get("urgency") == "POTENTIAL_BREAKING":
            draw.rounded_rectangle((760, 145, 1022, 205), radius=8, fill=(16, 22, 30))
            draw.text((891, 175), "BREAKING", font=self.english_font(23), fill=self.WHITE, anchor="mm")

        # The lower editorial panel is deliberately quiet and highly readable.
        draw.rectangle((0, 800, self.WIDTH, self.HEIGHT), fill=self.PAPER)
        draw.rectangle((58, 842, 65, 918), fill=self.RED)

        headline_font = None
        headline_lines = None
        for size in (72, 66, 60, 54, 48):
            candidate_font = self.urdu_font(size)
            candidate_lines = self._wrap(draw, headline, candidate_font, 900, direction="rtl")
            if len(candidate_lines) <= 3:
                headline_font, headline_lines = candidate_font, candidate_lines
                break
        if headline_font is None:
            raise ValueError("Urdu headline is too long for the international poster layout.")

        y = 838
        for line in headline_lines:
            draw.text((1018, y), line, font=headline_font, fill=self.INK, anchor="ra", direction="rtl", language="ur")
            y += int(headline_font.size * 1.42)

        summary = body[:210]
        body_font = self.urdu_font(31)
        summary_lines = self._wrap(draw, summary, body_font, 930, direction="rtl")[:2]
        y += 12
        for line in summary_lines:
            if y > 1175:
                break
            draw.text((1018, y), line, font=body_font, fill=(76, 84, 92), anchor="ra", direction="rtl", language="ur")
            y += 47

        # Compact source/date footer and clear publisher credit.
        draw.line((58, 1230, 1022, 1230), fill=self.LINE, width=2)
        source = str(data.get("source_name") or "NEWS SOURCE").upper()[:34]
        draw.text((58, 1262), source, font=self.english_font(18), fill=self.MUTED)
        draw.text((1022, 1260), self._published_label(data.get("published_at")), font=self.english_font(17, regular=True), fill=self.MUTED, anchor="ra")
        draw.text((58, 1310), "ADEEL RAJA", font=self.english_font(19), fill=self.INK)
        draw.text((1022, 1310), "FOLLOW FOR VERIFIED UPDATES", font=self.english_font(15, regular=True), fill=self.RED, anchor="ra")

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        key = data.get("source_url") or headline
        suffix = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:10]
        output_path = os.path.join(self.OUTPUT_DIR, f"adeel_raja_news_{suffix}.jpg")
        canvas.save(output_path, "JPEG", quality=95, optimize=True)
        return output_path

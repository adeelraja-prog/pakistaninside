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
    """Three premium, image-first international newsroom poster directions."""

    WIDTH = 1080
    HEIGHT = 1350
    OUTPUT_DIR = "assets/output"

    INK = (19, 25, 32)
    PAPER = (248, 248, 245)
    WHITE = (255, 255, 255)
    MUTED = (101, 110, 119)
    NAVY = (10, 19, 31)
    RED = (202, 35, 47)
    LINE = (222, 225, 228)

    CATEGORY_LABELS = {
        "POLITICS": "POLITICS",
        "COURT": "COURTS & JUSTICE",
        "PUBLIC_INTEREST": "PUBLIC INTEREST",
        "ECONOMY": "ECONOMY",
        "DEFENSE": "SECURITY",
        "WORLD": "WORLD",
        "HEALTH": "HEALTH",
        "EDUCATION": "EDUCATION",
        "TECHNOLOGY": "TECHNOLOGY",
        "BUSINESS": "BUSINESS",
        "SPORTS": "SPORTS",
        "ENTERTAINMENT": "ENTERTAINMENT",
        "CRIME": "CRIME",
        "ENVIRONMENT": "ENVIRONMENT",
        "ENERGY": "ENERGY",
        "TRANSPORT": "TRANSPORT",
        "GOVERNANCE": "GOVERNANCE",
        "ELECTIONS": "ELECTIONS",
        "DIPLOMACY": "DIPLOMACY",
        "HUMAN_RIGHTS": "HUMAN RIGHTS",
        "CLIMATE": "CLIMATE",
        "INVESTIGATION": "INVESTIGATION",
        "LOCAL": "LOCAL NEWS",
        "GENERAL": "LATEST NEWS",
    }

    CATEGORY_COLORS = {
        "POLITICS": (69, 104, 143),
        "COURT": (83, 91, 105),
        "PUBLIC_INTEREST": (42, 123, 119),
        "ECONOMY": (95, 119, 91),
        "DEFENSE": (112, 92, 91),
        "WORLD": (88, 98, 150),
        "HEALTH": (66, 126, 103),
        "EDUCATION": (84, 111, 139),
        "TECHNOLOGY": (66, 116, 153),
        "BUSINESS": (117, 119, 78),
        "SPORTS": (154, 112, 65),
        "ENTERTAINMENT": (133, 91, 126),
        "CRIME": (116, 84, 88),
        "ENVIRONMENT": (69, 123, 85),
        "ENERGY": (150, 122, 69),
        "TRANSPORT": (89, 112, 127),
        "GOVERNANCE": (91, 104, 122),
        "ELECTIONS": (105, 91, 143),
        "DIPLOMACY": (73, 97, 135),
        "HUMAN_RIGHTS": (63, 124, 125),
        "CLIMATE": (78, 127, 103),
        "INVESTIGATION": (87, 92, 98),
        "LOCAL": (104, 111, 119),
        "GENERAL": (105, 110, 116),
    }

    STYLES = ("light_editorial", "dark_editorial", "white_red")

    def __init__(self):
        self.urdu_font_path = self._find_font([
            "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf",
            "/usr/share/fonts/**/*NastaliqUrdu*Regular*.ttf",
            "/usr/share/fonts/**/*Nastaliq*Regular*.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/**/*Naskh*Regular*.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
            raise RuntimeError("No Arabic-script font suitable for Urdu rendering found.")

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

    def _headline_block(self, draw, headline, color, right=1018, top=840, width=900, max_lines=3):
        chosen_font, chosen_lines = None, None
        for size in (72, 66, 60, 54, 48):
            font = self.urdu_font(size)
            lines = self._wrap(draw, headline, font, width, direction="rtl")
            if len(lines) <= max_lines:
                chosen_font, chosen_lines = font, lines
                break
        if chosen_font is None:
            raise ValueError("Urdu headline is too long for the premium poster layout.")
        y = top
        for line in chosen_lines:
            draw.text((right, y), line, font=chosen_font, fill=color, anchor="ra", direction="rtl", language="ur")
            y += int(chosen_font.size * 1.42)
        return y

    def _footer(self, draw, data, dark=False):
        color = (177, 187, 197) if dark else self.MUTED
        line = (55, 70, 87) if dark else self.LINE
        draw.line((58, 1240, 1022, 1240), fill=line, width=2)
        source = str(data.get("source_name") or "NEWS SOURCE").upper()[:32]
        draw.text((58, 1262), source, font=self.english_font(17), fill=color)
        draw.text((1022, 1260), self._published_label(data.get("published_at")), font=self.english_font(16, regular=True), fill=color, anchor="ra")
        draw.text((58, 1310), "ADEEL RAJA", font=self.english_font(19), fill=(255, 255, 255) if dark else self.INK)

    def _breaking_badge(self, draw, dark=False):
        draw.rounded_rectangle((760, 145, 1022, 205), radius=8, fill=self.RED)
        draw.text((891, 175), "BREAKING NEWS", font=self.english_font(21), fill=self.WHITE, anchor="mm")

    def _render_light_editorial(self, photo, data, category, accent):
        canvas = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.PAPER)
        draw = ImageDraw.Draw(canvas)
        draw.text((58, 26), "ADEEL RAJA", font=self.english_font(43), fill=self.INK)
        draw.text((1020, 43), "INDEPENDENT NEWSROOM", font=self.english_font(17, regular=True), fill=self.MUTED, anchor="ra")
        draw.rectangle((58, 91, 1022, 97), fill=accent)

        hero = ImageOps.fit(photo, (self.WIDTH, 690), method=Image.Resampling.LANCZOS, centering=(0.5, 0.38))
        canvas.paste(hero, (0, 110))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((58, 145, 390, 205), radius=8, fill=accent)
        draw.text((82, 163), category, font=self.english_font(22), fill=self.WHITE)
        if data.get("urgency") == "POTENTIAL_BREAKING":
            self._breaking_badge(draw)

        draw.rectangle((0, 800, self.WIDTH, self.HEIGHT), fill=self.PAPER)
        draw.rectangle((58, 842, 65, 918), fill=accent)
        y = self._headline_block(draw, data["headline"], self.INK, top=838)
        body_font = self.urdu_font(31)
        for line in self._wrap(draw, data.get("body") or data.get("urdu_text", ""), body_font, 930, direction="rtl")[:2]:
            if y < 1185:
                draw.text((1018, y + 10), line, font=body_font, fill=(76, 84, 92), anchor="ra", direction="rtl", language="ur")
                y += 47
        self._footer(draw, data)
        return canvas

    def _render_dark_editorial(self, photo, data, category, accent):
        canvas = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.NAVY)
        draw = ImageDraw.Draw(canvas)
        draw.text((58, 26), "ADEEL RAJA", font=self.english_font(43), fill=self.WHITE)
        draw.text((1020, 43), "NEWS  /  ANALYSIS", font=self.english_font(17, regular=True), fill=(170, 181, 193), anchor="ra")
        draw.rectangle((58, 91, 1022, 97), fill=accent)

        hero = ImageOps.fit(photo, (self.WIDTH, 690), method=Image.Resampling.LANCZOS, centering=(0.5, 0.38))
        canvas.paste(hero, (0, 110))
        overlay = Image.new("RGBA", (self.WIDTH, 260), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for y in range(260):
            alpha = int(10 + 155 * (y / 259) ** 1.8)
            od.line((0, y, self.WIDTH, y), fill=(4, 9, 16, alpha))
        rgba = canvas.convert("RGBA")
        rgba.alpha_composite(overlay, (0, 540))
        canvas = rgba.convert("RGB")
        draw = ImageDraw.Draw(canvas)

        draw.rounded_rectangle((58, 145, 390, 205), radius=8, fill=(12, 25, 40))
        draw.text((82, 163), category, font=self.english_font(22), fill=accent)
        if data.get("urgency") == "POTENTIAL_BREAKING":
            self._breaking_badge(draw)

        draw.rectangle((0, 800, self.WIDTH, self.HEIGHT), fill=self.NAVY)
        draw.rectangle((58, 842, 65, 918), fill=accent)
        y = self._headline_block(draw, data["headline"], self.WHITE, top=838)
        body_font = self.urdu_font(31)
        for line in self._wrap(draw, data.get("body") or data.get("urdu_text", ""), body_font, 930, direction="rtl")[:2]:
            if y < 1185:
                draw.text((1018, y + 10), line, font=body_font, fill=(190, 199, 208), anchor="ra", direction="rtl", language="ur")
                y += 47
        self._footer(draw, data, dark=True)
        return canvas

    def _render_white_red(self, photo, data, category, accent):
        canvas = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.WHITE)
        draw = ImageDraw.Draw(canvas)
        draw.text((58, 26), "ADEEL RAJA", font=self.english_font(43), fill=self.INK)
        draw.text((1020, 43), "THE STORY BEHIND THE STORY", font=self.english_font(15, regular=True), fill=self.MUTED, anchor="ra")
        draw.rectangle((58, 91, 1022, 97), fill=self.RED)

        hero = ImageOps.fit(photo, (964, 620), method=Image.Resampling.LANCZOS, centering=(0.5, 0.38))
        mask = Image.new("L", hero.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 963, 619), radius=18, fill=255)
        canvas.paste(hero, (58, 120), mask)
        draw = ImageDraw.Draw(canvas)

        draw.rounded_rectangle((82, 150, 390, 207), radius=7, fill=self.WHITE)
        draw.text((104, 166), category, font=self.english_font(20), fill=accent)
        if data.get("urgency") == "POTENTIAL_BREAKING":
            self._breaking_badge(draw)

        draw.rectangle((58, 790, 66, 920), fill=self.RED)
        y = self._headline_block(draw, data["headline"], self.INK, top=790)
        body_font = self.urdu_font(30)
        for line in self._wrap(draw, data.get("body") or data.get("urdu_text", ""), body_font, 930, direction="rtl")[:2]:
            if y < 1185:
                draw.text((1018, y + 10), line, font=body_font, fill=(76, 84, 92), anchor="ra", direction="rtl", language="ur")
                y += 46
        self._footer(draw, data)
        return canvas

    def generate_card(self, data):
        headline = str(data.get("headline") or "").strip()
        if not headline or not re.search(r"[\u0600-\u06FF]", headline):
            raise ValueError("A valid Urdu headline is required")
        if data.get("language") != "ur":
            raise ValueError("Urdu-first poster gate failed")
        if not data.get("source_url"):
            raise ValueError("Source URL is mandatory")

        photo = self._download_image(data.get("image_url", ""))
        tag = str(data.get("tag") or "GENERAL").upper()
        category = self.CATEGORY_LABELS.get(tag, "LATEST NEWS")
        accent = self.CATEGORY_COLORS.get(tag, self.CATEGORY_COLORS["GENERAL"])
        style = str(data.get("poster_style") or "light_editorial").lower()
        renderers = {
            "light_editorial": self._render_light_editorial,
            "dark_editorial": self._render_dark_editorial,
            "white_red": self._render_white_red,
        }
        if style not in renderers:
            style = "light_editorial"
        canvas = renderers[style](photo, data, category, accent)

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        key = data.get("source_url") or headline
        suffix = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:10]
        output_path = os.path.join(self.OUTPUT_DIR, f"adeel_raja_news_{suffix}.jpg")
        canvas.save(output_path, "JPEG", quality=95, optimize=True)
        return output_path

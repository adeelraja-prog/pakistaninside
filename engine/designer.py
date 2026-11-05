import os
import re
import glob
from PIL import Image, ImageDraw, ImageFont, features


class DesignerAgent:
    WIDTH = 1080
    HEIGHT = 1350
    OUTPUT_PATH = "assets/output/latest_news_card.png"

    CATEGORY_COLORS = {
        "POLITICS": (180, 40, 40),
        "DEFENSE": (160, 30, 30),
        "ECONOMY": (180, 140, 40),
        "TECH": (30, 80, 160),
        "HEALTH": (30, 120, 80),
        "COURT": (120, 60, 140),
        "GENERAL": (12, 27, 23),
    }

    GOLD = (218, 181, 99)
    WHITE = (250, 248, 241)
    MUTED = (205, 215, 207)

    def __init__(self):
        self.urdu_font_path = (self._find_font("Nastaliq") or self._find_font("NaskhArabic") or self._find_font("Arabic"))
        self.english_font_path = self._find_font("DejaVu")
        if not features.check("raqm"):
            print("[DESIGNER] Warning: RAQM not available, Urdu may render poorly")

    def _find_font(self, keyword):
        candidates = glob.glob(f"/usr/share/fonts/**/*{keyword}*", recursive=True)
        for path in candidates:
            if path.lower().endswith((".ttf", ".otf")):
                return path
        return None

    def urdu_font(self, size):
        if self.urdu_font_path:
            return ImageFont.truetype(self.urdu_font_path, size, layout_engine=ImageFont.Layout.RAQM)
        return ImageFont.load_default()

    def english_font(self, size):
        if self.english_font_path:
            return ImageFont.truetype(self.english_font_path, size)
        return ImageFont.load_default()

    def generate_card(self, data):
        tag = data.get("tag", "GENERAL").upper()
        language = data.get("language", "ur")
        headline = data.get("headline", "")
        body = data.get("body", "")
        attribution = data.get("source_attribution", "")

        bg_color = self.CATEGORY_COLORS.get(tag, self.CATEGORY_COLORS["GENERAL"])

        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), bg_color)
        draw = ImageDraw.Draw(image)

        # Top gold bar
        draw.rectangle((0, 0, self.WIDTH, 12), fill=self.GOLD)

        # Brand
        draw.text((40, 40), "PI", font=self.english_font(42), fill=self.GOLD)
        draw.text((1000, 45), "PAKISTAN INSIDE", font=self.english_font(36), fill=self.WHITE, anchor="ra")
        draw.text((1000, 95), "THE STORY BEHIND THE STORY", font=self.english_font(16), fill=self.GOLD, anchor="ra")

        # Category badge
        draw.rectangle((40, 140, 280, 190), fill=self.GOLD)
        draw.text((160, 152), tag, font=self.english_font(28), fill=(20, 20, 20), anchor="mm")

        y = 230

        if language == "ur" and self.urdu_font_path:
            font = self.urdu_font(64)
            # Simple right-aligned Urdu (basic)
            draw.text((1000, y), headline, font=font, fill=self.WHITE, anchor="ra")
            y += 180
            if body:
                draw.text((1000, y), body, font=self.urdu_font(36), fill=self.MUTED, anchor="ra")
                y += 120
        else:
            # English fallback
            font = self.english_font(48)
            draw.text((60, y), headline, font=font, fill=self.WHITE)
            y += 160
            if body:
                draw.text((60, y), body, font=self.english_font(32), fill=self.MUTED)
                y += 100

        # Source
        if attribution:
            draw.text((60, 1180), attribution, font=self.english_font(22), fill=self.GOLD)

        # Footer
        draw.text((1000, 1260), "PAKISTAN INSIDE", font=self.english_font(22), fill=self.GOLD, anchor="ra")

        os.makedirs(os.path.dirname(self.OUTPUT_PATH), exist_ok=True)
        image.save(self.OUTPUT_PATH, "PNG", optimize=True)
        return self.OUTPUT_PATH

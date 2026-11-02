
import os
import re
from PIL import Image, ImageDraw, ImageFont, features


class DesignerAgent:
    WIDTH = 1080
    HEIGHT = 1350
    OUTPUT_PATH = "assets/output/latest_news_card.png"

    BG = (12, 24, 21)
    BG_LIGHT = (21, 43, 34)
    GOLD = (218, 181, 99)
    WHITE = (250, 248, 240)
    MUTED = (207, 213, 204)
    GREEN = (37, 83, 61)

    FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def __init__(self):
        self.font_path = next(
            (p for p in self.FONT_CANDIDATES if os.path.isfile(p)),
            None
        )

        if not self.font_path:
            raise FileNotFoundError(
                "Noto Urdu font not found. Install fonts-noto-core."
            )

        if not features.check("raqm"):
            raise RuntimeError(
                "Pillow RAQM is required for proper Urdu text rendering."
            )

        print(f"[DESIGNER] Using font: {self.font_path}")

    def font(self, size):
        return ImageFont.truetype(
            self.font_path,
            size,
            layout_engine=ImageFont.Layout.RAQM
        )

    @staticmethod
    def clean_text(value):
        if value is None:
            return ""

        value = str(value)
        value = re.sub(r"https?://\S+", "", value)
        value = re.sub(r"www\.\S+", "", value)
        value = re.sub(r"<[^>]+>", "", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    @staticmethod
    def normalise(value):
        value = str(value or "").lower()
        value = re.sub(r"[^\w\s]", "", value)
        return re.sub(r"\s+", " ", value).strip()

    def is_duplicate(self, a, b):
        a = self.normalise(a)
        b = self.normalise(b)

        if not a or not b:
            return False

        return a == b or a in b or b in a

    def remove_duplicate_sentences(self, text):
        sentences = re.split(r"(?<=[۔.!؟])\s+", text)
        output = []
        seen = set()

        for sentence in sentences:
            sentence = sentence.strip()
            key = self.normalise(sentence)

            if key and key not in seen:
                seen.add(key)
                output.append(sentence)

        return " ".join(output)

    def wrap_text(self, draw, text, font, max_width):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()

            box = draw.textbbox(
                (0, 0),
                candidate,
                font=font,
                direction="rtl",
                language="ur"
            )

            if box[2] - box[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def line_height(self, draw, font):
        box = draw.textbbox(
            (0, 0),
            "پاکستان",
            font=font,
            direction="rtl",
            language="ur"
        )
        return max(1, box[3] - box[1])

    def fit_text(self, draw, text, max_width, max_height,
                 starting_size, minimum_size, spacing):
        """
        Find a font size that fits all text without silently
        dropping lines or cutting off the story.
        """
        for size in range(starting_size, minimum_size - 1, -2):
            font = self.font(size)
            lines = self.wrap_text(draw, text, font, max_width)
            height = (
                len(lines) * self.line_height(draw, font)
                + max(0, len(lines) - 1) * spacing
            )

            if height <= max_height:
                return font, lines, height

        font = self.font(minimum_size)
        lines = self.wrap_text(draw, text, font, max_width)
        height = (
            len(lines) * self.line_height(draw, font)
            + max(0, len(lines) - 1) * spacing
        )

        return font, lines, height

    def draw_rtl_lines(self, draw, lines, font, y, fill, spacing):
        for line in lines:
            draw.text(
                (995, y),
                line,
                font=font,
                fill=fill,
                anchor="ra",
                direction="rtl",
                language="ur"
            )
            y += self.line_height(draw, font) + spacing

        return y

    def create_background(self):
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG)
        draw = ImageDraw.Draw(image)

        # Subtle editorial background treatment.
        draw.rectangle(
            (0, 0, self.WIDTH, 14),
            fill=self.GOLD
        )

        draw.ellipse(
            (-420, 780, 350, 1550),
            fill=self.BG_LIGHT
        )

        draw.ellipse(
            (850, -350, 1450, 300),
            fill=(17, 34, 28)
        )

        return image

    def draw_masthead(self, draw):
        # Custom PI monogram logo.
        draw.ellipse(
            (78, 66, 170, 158),
            outline=self.GOLD,
            width=4
        )

        draw.text(
            (124, 111),
            "PI",
            font=self.font(35),
            fill=self.GOLD,
            anchor="mm"
        )

        # Brand name.
        draw.text(
            (995, 75),
            "PAKISTAN INSIDE",
            font=self.font(48),
            fill=self.WHITE,
            anchor="ra"
        )

        draw.text(
            (995, 137),
            "THE STORY BEHIND THE STORY",
            font=self.font(20),
            fill=self.GOLD,
            anchor="ra"
        )

        draw.line(
            (80, 205, 1000, 205),
            fill=self.GREEN,
            width=3
        )

    def prepare_content(self, data):
        headline = self.clean_text(data.get("headline"))
        urdu_text = self.clean_text(data.get("urdu_text"))
        body = self.clean_text(data.get("body"))

        if not headline:
            headline = urdu_text or body

        if not headline:
            raise ValueError("No editorial headline or story was provided.")

        # Select one distinct summary, not repeated copies.
        candidates = [urdu_text, body]
        candidates = [
            item for item in candidates
            if item and not self.is_duplicate(item, headline)
        ]

        summary = max(candidates, key=len) if candidates else ""

        if summary:
            summary = self.remove_duplicate_sentences(summary)

        return headline, summary

    def generate_card(self, edited_data):
        if not isinstance(edited_data, dict):
            raise TypeError("Editorial data must be a dictionary.")

        headline, summary = self.prepare_content(edited_data)

        image = self.create_background()
        draw = ImageDraw.Draw(image)

        self.draw_masthead(draw)

        # Main headline.
        headline_top = 275
        headline_area_height = 390

        headline_font, headline_lines, headline_height = self.fit_text(
            draw=draw,
            text=headline,
            max_width=900,
            max_height=headline_area_height,
            starting_size=76,
            minimum_size=43,
            spacing=19
        )

        headline_end = self.draw_rtl_lines(
            draw,
            headline_lines,
            headline_font,
            headline_top,
            self.WHITE,
            19
        )

        # Gold editorial divider.
        divider_y = max(710, headline_end + 35)

        draw.line(
            (80, divider_y, 1000, divider_y),
            fill=self.GOLD,
            width=4
        )

        # Summary.
        if summary:
            summary_top = divider_y + 48
            summary_area_height = 1230 - summary_top - 45

            summary_font, summary_lines, summary_height = self.fit_text(
                draw=draw,
                text=summary,
                max_width=900,
                max_height=summary_area_height,
                starting_size=39,
                minimum_size=25,
                spacing=16
            )

            self.draw_rtl_lines(
                draw,
                summary_lines,
                summary_font,
                summary_top,
                self.MUTED,
                16
            )

        # Footer identity. No source name, URL or duplicate headline.
        draw.line(
            (80, 1230, 1000, 1230),
            fill=self.GREEN,
            width=2
        )

        draw.text(
            (995, 1260),
            "PAKISTAN INSIDE",
            font=self.font(27),
            fill=self.GOLD,
            anchor="ra"
        )

        draw.text(
            (995, 1305),
            "THE STORY BEHIND THE STORY",
            font=self.font(18),
            fill=self.MUTED,
            anchor="ra"
        )

        os.makedirs(
            os.path.dirname(self.OUTPUT_PATH),
            exist_ok=True
        )

        image.save(
            self.OUTPUT_PATH,
            "PNG",
            optimize=True
        )

        print(
            f"[DESIGNER] Poster successfully generated: "
            f"{self.OUTPUT_PATH}"
        )

        return self.OUTPUT_PATH

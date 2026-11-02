
import os
import re
import hashlib
from PIL import Image, ImageDraw, ImageFont, features


class DesignerAgent:
    WIDTH = 1080
    HEIGHT = 1350

    BACKGROUND = (12, 25, 22)
    GREEN = (24, 57, 43)
    GOLD = (218, 181, 99)
    WHITE = (248, 246, 238)
    MUTED = (183, 194, 184)

    OUTPUT_PATH = "assets/output/latest_news_card.png"

    FONT_PATHS = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def __init__(self):
        self.font_path = self._find_font()

        if not features.check("raqm"):
            raise RuntimeError(
                "Pillow RAQM support is required for correct Urdu rendering."
            )

        print(f"[DESIGNER] Using font: {self.font_path}")

    def _find_font(self):
        for path in self.FONT_PATHS:
            if os.path.isfile(path):
                return path

        raise FileNotFoundError(
            "No suitable Urdu font found. Install Noto Naskh Arabic."
        )

    def _font(self, size):
        return ImageFont.truetype(
            self.font_path,
            size,
            layout_engine=ImageFont.Layout.RAQM
        )

    @staticmethod
    def _clean(value):
        if not value:
            return ""

        text = str(value)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"www\.\S+", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _normalise(value):
        value = str(value or "").lower()
        value = re.sub(r"[^\w\s]", "", value)
        return re.sub(r"\s+", " ", value).strip()

    def _is_duplicate(self, first, second):
        a = self._normalise(first)
        b = self._normalise(second)

        if not a or not b:
            return True

        if a == b or a in b or b in a:
            return True

        return False

    def _remove_duplicate_sentences(self, text):
        sentences = re.split(r"(?<=[۔.!؟])\s+", text)
        result = []
        seen = set()

        for sentence in sentences:
            sentence = sentence.strip()
            key = self._normalise(sentence)

            if key and key not in seen:
                seen.add(key)
                result.append(sentence)

        return " ".join(result)

    def _wrap_rtl(self, draw, text, font, max_width):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            test = f"{current} {word}".strip()

            bbox = draw.textbbox(
                (0, 0),
                test,
                font=font,
                direction="rtl",
                language="ur"
            )

            width = bbox[2] - bbox[0]

            if width <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def _draw_rtl_block(
        self,
        draw,
        text,
        y,
        font,
        max_width,
        fill,
        line_gap=20,
        max_lines=None
    ):
        lines = self._wrap_rtl(draw, text, font, max_width)

        if max_lines:
            lines = lines[:max_lines]

        for line in lines:
            draw.text(
                (self.WIDTH - 85, y),
                line,
                font=font,
                fill=fill,
                anchor="ra",
                direction="rtl",
                language="ur"
            )

            bbox = draw.textbbox(
                (0, 0),
                line,
                font=font,
                direction="rtl",
                language="ur"
            )

            y += (bbox[3] - bbox[1]) + line_gap

        return y

    def _gradient_background(self):
        image = Image.new(
            "RGB",
            (self.WIDTH, self.HEIGHT),
            self.BACKGROUND
        )

        pixels = image.load()

        for y in range(self.HEIGHT):
            ratio = y / self.HEIGHT

            for x in range(self.WIDTH):
                glow = max(0, 1 - abs(x - 160) / 1000)
                pixels[x, y] = (
                    int(12 + 8 * ratio + 3 * glow),
                    int(25 + 14 * ratio + 5 * glow),
                    int(22 + 5 * ratio)
                )

        return image

    def _draw_brand(self, draw):
        # Top editorial masthead: no enclosing box.
        draw.text(
            (85, 65),
            "PI",
            font=self._font(48),
            fill=self.GOLD
        )

        draw.line(
            (85, 132, 995, 132),
            fill=self.GOLD,
            width=3
        )

        draw.text(
            (995, 70),
            "PAKISTAN INSIDE",
            font=self._font(48),
            fill=self.WHITE,
            anchor="ra"
        )

        draw.text(
            (995, 145),
            "THE STORY BEHIND THE STORY",
            font=self._font(21),
            fill=self.GOLD,
            anchor="ra"
        )

    def _draw_bottom_brand(self, draw):
        draw.line(
            (85, 1230, 995, 1230),
            fill=self.GOLD,
            width=2
        )

        draw.text(
            (995, 1260),
            "PAKISTAN INSIDE",
            font=self._font(25),
            fill=self.GOLD,
            anchor="ra"
        )

        draw.text(
            (995, 1300),
            "THE STORY BEHIND THE STORY",
            font=self._font(17),
            fill=self.MUTED,
            anchor="ra"
        )

    def _prepare_content(self, data):
        headline = self._clean(data.get("headline"))
        urdu_text = self._clean(data.get("urdu_text"))
        body = self._clean(data.get("body"))

        if not headline:
            headline = urdu_text or body

        if not headline:
            raise ValueError("No headline or story content supplied.")

        # Never print the same text twice.
        if self._is_duplicate(urdu_text, headline):
            urdu_text = ""

        if self._is_duplicate(body, headline):
            body = ""

        if urdu_text and body and self._is_duplicate(urdu_text, body):
            body = ""

        # Prefer the longer distinct editorial text.
        summary = max(
            [item for item in (urdu_text, body) if item],
            key=len,
            default=""
        )

        summary = self._remove_duplicate_sentences(summary)

        return headline, summary

    def generate_card(self, edited_data):
        if not isinstance(edited_data, dict):
            raise ValueError("Designer expected editorial data as a dictionary.")

        headline, summary = self._prepare_content(edited_data)

        image = self._gradient_background()
        draw = ImageDraw.Draw(image)

        self._draw_brand(draw)

        # Editorial accent, not a generic Breaking News banner.
        draw.text(
            (995, 235),
            "خصوصی رپورٹ",
            font=self._font(27),
            fill=self.GOLD,
            anchor="ra",
            direction="rtl",
            language="ur"
        )

        # Main headline.
        headline_font = self._font(65)
        headline_y = 310

        headline_end = self._draw_rtl_block(
            draw,
            headline,
            headline_y,
            headline_font,
            900,
            self.WHITE,
            line_gap=25,
            max_lines=5
        )

        # A restrained gold separator.
        separator_y = min(headline_end + 35, 790)

        draw.line(
            (85, separator_y, 995, separator_y),
            fill=self.GOLD,
            width=3
        )

        # Original editorial summary: shown only once.
        if summary:
            summary_font = self._font(37)

            self._draw_rtl_block(
                draw,
                summary,
                separator_y + 55,
                summary_font,
                900,
                self.MUTED,
                line_gap=19,
                max_lines=8
            )

        self._draw_bottom_brand(draw)

        os.makedirs(os.path.dirname(self.OUTPUT_PATH), exist_ok=True)

        image.save(
            self.OUTPUT_PATH,
            format="PNG",
            optimize=True
        )

        print(f"[DESIGNER] News graphic generated: {self.OUTPUT_PATH}")

        return self.OUTPUT_PATH

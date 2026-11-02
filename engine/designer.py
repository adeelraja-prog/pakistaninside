
import os
import re
import glob
from PIL import Image, ImageDraw, ImageFont, features


class DesignerAgent:

    WIDTH = 1080
    HEIGHT = 1350

    OUTPUT_PATH = "assets/output/latest_news_card.png"

    # Pakistan Inside visual identity
    BG = (12, 27, 23)
    BG_ACCENT = (20, 43, 34)
    GOLD = (218, 181, 99)
    WHITE = (250, 248, 241)
    MUTED = (205, 215, 207)
    LINE = (73, 104, 83)

    URDU_FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Bold.ttf",
    ]

    ENGLISH_FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def __init__(self):

        self.urdu_font_path = self._find_urdu_font()
        self.english_font_path = self._find_english_font()

        if not features.check("raqm"):
            raise RuntimeError(
                "Pillow RAQM is unavailable. "
                "Correct Urdu text shaping cannot be guaranteed."
            )

        print("[DESIGNER] Urdu font:", self.urdu_font_path)
        print("[DESIGNER] English font:", self.english_font_path)
        print("[DESIGNER] RAQM support: enabled")

    def _find_urdu_font(self):

        for path in self.URDU_FONT_CANDIDATES:
            if os.path.isfile(path):
                return path

        matches = glob.glob(
            "/usr/share/fonts/**/*Nastaliq*",
            recursive=True
        )

        for path in matches:
            if path.lower().endswith((".ttf", ".otf")):
                return path

        raise FileNotFoundError(
            "Noto Nastaliq Urdu font not found. "
            "Install Ubuntu package fonts-noto-extra. "
            "Poster generation stopped to prevent unreadable Urdu."
        )

    def _find_english_font(self):

        for path in self.ENGLISH_FONT_CANDIDATES:
            if os.path.isfile(path):
                return path

        raise FileNotFoundError(
            "DejaVu English font not found."
        )

    def urdu_font(self, size):

        return ImageFont.truetype(
            self.urdu_font_path,
            size,
            layout_engine=ImageFont.Layout.RAQM
        )

    def english_font(self, size):

        return ImageFont.truetype(
            self.english_font_path,
            size
        )

    @staticmethod
    def clean(value):

        if not value:
            return ""

        value = str(value)

        value = re.sub(
            r"https?://\S+|www\.\S+",
            "",
            value
        )

        value = re.sub(r"<[^>]+>", "", value)
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    @staticmethod
    def has_urdu(text):

        return bool(
            re.search(
                r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]",
                text or ""
            )
        )

    @staticmethod
    def normalise(text):

        text = str(text or "").lower()
        text = re.sub(r"[^\w\s]", "", text)

        return re.sub(r"\s+", " ", text).strip()

    def is_duplicate(self, first, second):

        a = self.normalise(first)
        b = self.normalise(second)

        if not a or not b:
            return False

        return a == b or a in b or b in a

    def remove_duplicate_sentences(self, text):

        sentences = re.split(
            r"(?<=[۔.!؟])\s+",
            text
        )

        result = []
        seen = set()

        for sentence in sentences:

            sentence = sentence.strip()
            key = self.normalise(sentence)

            if key and key not in seen:
                seen.add(key)
                result.append(sentence)

        return " ".join(result)

    def prepare_content(self, data):

        headline = self.clean(data.get("headline"))
        urdu_text = self.clean(data.get("urdu_text"))
        body = self.clean(data.get("body"))

        # Prefer an actual Urdu headline.
        if not self.has_urdu(headline):
            if self.has_urdu(urdu_text):
                headline = urdu_text
                urdu_text = ""
            elif self.has_urdu(body):
                headline = body
                body = ""

        if not headline:
            raise ValueError(
                "No usable headline was supplied by the Editor."
            )

        candidates = []

        for item in (urdu_text, body):

            if not item:
                continue

            if not self.has_urdu(item):
                continue

            if self.is_duplicate(item, headline):
                continue

            if any(self.is_duplicate(item, old) for old in candidates):
                continue

            candidates.append(item)

        summary = max(candidates, key=len) if candidates else ""

        summary = self.remove_duplicate_sentences(summary)

        return headline, summary

    def wrap_urdu(self, draw, text, font, max_width):

        words = text.split()
        lines = []
        current = ""

        for word in words:

            candidate = f"{current} {word}".strip()

            bbox = draw.textbbox(
                (0, 0),
                candidate,
                font=font,
                direction="rtl",
                language="ur"
            )

            width = bbox[2] - bbox[0]

            if width <= max_width:
                current = candidate

            else:
                if current:
                    lines.append(current)

                current = word

        if current:
            lines.append(current)

        return lines

    def text_height(self, draw, text, font):

        bbox = draw.textbbox(
            (0, 0),
            text or "پاکستان",
            font=font,
            direction="rtl",
            language="ur"
        )

        return max(1, bbox[3] - bbox[1])

    def fit_urdu(
        self,
        draw,
        text,
        max_width,
        max_height,
        starting_size,
        minimum_size
    ):

        for size in range(
            starting_size,
            minimum_size - 1,
            -2
        ):

            font = self.urdu_font(size)

            lines = self.wrap_urdu(
                draw,
                text,
                font,
                max_width
            )

            heights = [
                self.text_height(draw, line, font)
                for line in lines
            ]

            total_height = sum(heights) + max(
                0,
                len(lines) - 1
            ) * 24

            if total_height <= max_height:

                return font, lines, heights

        raise ValueError(
            "Urdu text is too long for the poster. "
            "The Designer will not silently truncate the story."
        )

    def draw_urdu(
        self,
        draw,
        lines,
        heights,
        font,
        start_y,
        color
    ):

        y = start_y

        for line, height in zip(lines, heights):

            draw.text(
                (995, y),
                line,
                font=font,
                fill=color,
                anchor="ra",
                direction="rtl",
                language="ur"
            )

            y += height + 24

        return y

    def create_background(self):

        image = Image.new(
            "RGB",
            (self.WIDTH, self.HEIGHT),
            self.BG
        )

        draw = ImageDraw.Draw(image)

        # Subtle geometric editorial background.
        draw.rectangle(
            (0, 0, self.WIDTH, 13),
            fill=self.GOLD
        )

        draw.polygon(
            [
                (0, 920),
                (0, 1350),
                (420, 1350)
            ],
            fill=self.BG_ACCENT
        )

        draw.line(
            (80, 134, 1000, 134),
            fill=self.LINE,
            width=2
        )

        return image

    def draw_brand(self, draw):

        # Proper English wordmark, separate from Urdu font.
        draw.text(
            (80, 55),
            "PI",
            font=self.english_font(48),
            fill=self.GOLD
        )

        draw.text(
            (1000, 57),
            "PAKISTAN INSIDE",
            font=self.english_font(43),
            fill=self.WHITE,
            anchor="ra"
        )

        draw.text(
            (1000, 112),
            "THE STORY BEHIND THE STORY",
            font=self.english_font(17),
            fill=self.GOLD,
            anchor="ra"
        )

    def draw_footer(self, draw):

        draw.line(
            (80, 1230, 1000, 1230),
            fill=self.LINE,
            width=2
        )

        draw.text(
            (1000, 1260),
            "PAKISTAN INSIDE",
            font=self.english_font(23),
            fill=self.GOLD,
            anchor="ra"
        )

        draw.text(
            (1000, 1300),
            "THE STORY BEHIND THE STORY",
            font=self.english_font(15),
            fill=self.MUTED,
            anchor="ra"
        )

    def generate_card(self, edited_data):

        if not isinstance(edited_data, dict):
            raise TypeError(
                "Designer expected a dictionary from the Editor."
            )

        headline, summary = self.prepare_content(
            edited_data
        )

        image = self.create_background()
        draw = ImageDraw.Draw(image)

        self.draw_brand(draw)

        # Main Urdu headline.
        headline_font, headline_lines, headline_heights = (
            self.fit_urdu(
                draw=draw,
                text=headline,
                max_width=900,
                max_height=380,
                starting_size=76,
                minimum_size=40
            )
        )

        headline_end = self.draw_urdu(
            draw,
            headline_lines,
            headline_heights,
            headline_font,
            215,
            self.WHITE
        )

        # Story separator.
        divider_y = headline_end + 25

        if divider_y > 700:
            raise ValueError(
                "Headline is too long for the available poster layout."
            )

        draw.line(
            (80, divider_y, 1000, divider_y),
            fill=self.GOLD,
            width=3
        )

        # Original Urdu summary.
        if summary:

            summary_top = divider_y + 45
            summary_space = 1220 - summary_top - 25

            summary_font, summary_lines, summary_heights = (
                self.fit_urdu(
                    draw=draw,
                    text=summary,
                    max_width=900,
                    max_height=summary_space,
                    starting_size=39,
                    minimum_size=24
                )
            )

            self.draw_urdu(
                draw,
                summary_lines,
                summary_heights,
                summary_font,
                summary_top,
                self.MUTED
            )

        self.draw_footer(draw)

        os.makedirs(
            os.path.dirname(self.OUTPUT_PATH),
            exist_ok=True
        )

        image.save(
            self.OUTPUT_PATH,
            format="PNG",
            optimize=True
        )

        print(
            "[DESIGNER] Urdu rendering completed successfully."
        )

        print(
            f"[DESIGNER] Poster generated: {self.OUTPUT_PATH}"
        )

        return self.OUTPUT_PATH


import os
from PIL import Image, ImageDraw, ImageFont, features


class DesignerAgent:

    def __init__(self):
        self.output_dir = "assets/output"
        os.makedirs(self.output_dir, exist_ok=True)

        self.width = 1080
        self.height = 1080

        self.background = (18, 22, 28)
        self.white = (255, 255, 255)
        self.red = (205, 35, 48)
        self.gold = (245, 190, 55)
        self.muted = (190, 195, 205)

        self.font_paths = [
            "assets/fonts/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

        # Proper Urdu/Arabic shaping requires Pillow's RAQM support.
        if not features.check("raqm"):
            raise RuntimeError(
                "Pillow does not have RAQM support. "
                "Cannot safely render Urdu text."
            )

        self.font_path = self.find_font()

    def find_font(self):
        for path in self.font_paths:
            if os.path.isfile(path):
                try:
                    ImageFont.truetype(
                        path,
                        32,
                        layout_engine=ImageFont.Layout.RAQM
                    )
                    print(f"[DESIGNER] Using font: {path}")
                    return path
                except Exception:
                    continue

        raise RuntimeError(
            "No suitable Urdu font found. "
            "Install Noto Naskh Arabic or add it to assets/fonts."
        )

    def load_font(self, size):
        return ImageFont.truetype(
            self.font_path,
            size,
            layout_engine=ImageFont.Layout.RAQM
        )

    def text_width(self, draw, text, font):
        return draw.textlength(
            text,
            font=font,
            direction="rtl",
            language="ur"
        )

    def wrap_urdu_text(self, draw, text, font, max_width):
        words = str(text).split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()

            if self.text_width(draw, test_line, font) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)

                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def draw_rtl_lines(
        self,
        draw,
        lines,
        font,
        right,
        top,
        fill,
        line_spacing=20
    ):
        y = top

        for line in lines:
            draw.text(
                (right, y),
                line,
                font=font,
                fill=fill,
                anchor="ra",
                direction="rtl",
                language="ur"
            )

            bbox = draw.textbbox(
                (right, y),
                line,
                font=font,
                anchor="ra",
                direction="rtl",
                language="ur"
            )

            y += max(45, bbox[3] - bbox[1]) + line_spacing

        return y

    def generate_card(self, processed_data):

        if not isinstance(processed_data, dict):
            raise ValueError(
                "Invalid editorial data supplied to Designer."
            )

        headline = str(
            processed_data.get("headline", "")
        ).strip()

        body = str(
            processed_data.get("body", "")
        ).strip()

        tag = str(
            processed_data.get("tag", "PAKISTAN INSIDE")
        ).strip()

        if not headline:
            raise ValueError(
                "Cannot design a card without a headline."
            )

        if not body:
            raise ValueError(
                "Cannot design a card without news body text."
            )

        img = Image.new(
            "RGB",
            (self.width, self.height),
            self.background
        )

        draw = ImageDraw.Draw(img)

        # Header band
        draw.rectangle(
            [0, 0, self.width, 145],
            fill=self.red
        )

        brand_font = self.load_font(48)

        draw.text(
            (55, 43),
            "PAKISTAN INSIDE",
            font=brand_font,
            fill=self.white
        )

        # News category tag
        draw.rounded_rectangle(
            [55, 185, 520, 250],
            radius=12,
            fill=self.gold
        )

        tag_font = self.load_font(30)

        draw.text(
            (75, 198),
            tag,
            font=tag_font,
            fill=(20, 20, 20),
            direction="rtl",
            language="ur"
        )

        # Headline
        headline_font = self.load_font(68)

        headline_lines = self.wrap_urdu_text(
            draw,
            headline,
            headline_font,
            950
        )

        headline_end = self.draw_rtl_lines(
            draw,
            headline_lines[:4],
            headline_font,
            1025,
            310,
            self.white,
            22
        )

        # Divider
        divider_y = min(
            max(headline_end + 20, 600),
            690
        )

        draw.rectangle(
            [55, divider_y, 1025, divider_y + 5],
            fill=self.red
        )

        # News summary
        body_font = self.load_font(43)

        body_lines = self.wrap_urdu_text(
            draw,
            body,
            body_font,
            950
        )

        self.draw_rtl_lines(
            draw,
            body_lines[:7],
            body_font,
            1025,
            divider_y + 45,
            self.muted,
            14
        )

        # Footer band
        draw.rectangle(
            [0, 1000, self.width, self.height],
            fill=(10, 13, 18)
        )

        footer_font = self.load_font(27)

        draw.text(
            (55, 1030),
            "THE STORY BEHIND THE STORY",
            font=footer_font,
            fill=self.gold
        )

        card_path = os.path.join(
            self.output_dir,
            "latest_news_card.png"
        )

        img.save(card_path, format="PNG")

        if not os.path.isfile(card_path):
            raise RuntimeError(
                "News graphic could not be saved."
            )

        if os.path.getsize(card_path) == 0:
            raise RuntimeError(
                "Generated news graphic is empty."
            )

        print(
            f"[DESIGNER] News graphic generated: {card_path}"
        )

        return card_path

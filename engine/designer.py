from PIL import Image, ImageDraw
import os

class DesignerAgent:
    def __init__(self):
        self.output_dir = "assets/output"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_card(self, processed_data):
        img = Image.new('RGB', (1080, 1080), color=(18, 18, 18))
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, 1080, 120], fill=(215, 38, 56))
        draw.text((40, 35), "PAKISTAN INSIDE", fill=(255, 255, 255))

        tag_text = processed_data.get('tag', 'BREAKING NEWS')
        draw.rectangle([40, 160, 320, 220], fill=(255, 215, 0))
        draw.text((50, 175), tag_text, fill=(0, 0, 0))

        card_path = os.path.join(self.output_dir, "latest_news_card.png")
        img.save(card_path)
        print(f"🎨 [Agent 3: Designer] High-contrast card generated: {card_path}")
        return card_path

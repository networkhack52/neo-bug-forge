"""
generate_icon.py — creates the Neo Bug Forge VS Code extension icon
Run: python generate_icon.py
Outputs: media/icon.png (128x128)
Requires: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def generate_icon(output_path="media/icon.png", size=128):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: dark rounded square
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=20,
        fill="#0d0d0d"
    )

    # Amber accent bar at top
    draw.rounded_rectangle(
        [margin, margin, size - margin, margin + 8],
        radius=4,
        fill="#ffb400"
    )

    # "NBF" text
    cx, cy = size // 2, size // 2

    # Large N
    draw.text((cx - 28, cy - 22), "N", fill="#ffb400", font=None)
    # Smaller BF
    draw.text((cx - 2, cy - 14), "BF", fill="#666666", font=None)

    # Bottom dot — forge spark
    draw.ellipse([cx - 4, cy + 22, cx + 4, cy + 30], fill="#ffb400")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Icon saved to {output_path} ({size}x{size}px)")

if __name__ == "__main__":
    generate_icon()

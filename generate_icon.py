"""生成应用图标 assets/glm.ico（风格与悬浮球一致：绿环 + 白内圆 + 中心 G）。

运行：python generate_icon.py
产出：assets/glm.ico（含 16/32/48/64/256 多尺寸）
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 配色与悬浮球 / 托盘一致
GREEN = (52, 199, 89, 255)       # #34C759 进度绿
TRACK = (229, 229, 234, 255)     # #E5E5EA 轨道灰
INNER_LIGHT = (255, 255, 255, 255)   # 内圆白
BORDER = (229, 229, 234, 255)    # 内圆描边
TEXT = (28, 28, 30, 255)         # 中心文字近黑

FONT_PATH = r"C:\Windows\Fonts\segoeuib.ttf"  # Segoe UI Bold


def draw(size: int) -> Image.Image:
    """绘制指定尺寸的图标。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = size / 2

    # 环宽与边距按尺寸缩放
    rw = max(2, size // 12)
    m = rw

    # 外环：先画灰色轨道，再叠绿色（这里直接用绿色，作为品牌主色）
    bbox_ring = [m, m, size - m, size - m]
    d.ellipse(bbox_ring, outline=TRACK, width=rw)
    d.ellipse(bbox_ring, outline=GREEN, width=rw)

    # 内圆（白底 + 描边）
    ir = cx - m - rw
    d.ellipse([cx - ir, cx - ir, cx + ir, cx + ir], fill=INNER_LIGHT, outline=BORDER, width=max(1, size // 96))

    # 中心字母 G
    try:
        font = ImageFont.truetype(FONT_PATH, int(ir * 1.1))
    except Exception:
        font = ImageFont.load_default()
    text = "G"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - tw / 2 - bbox[0], cx - th / 2 - bbox[1]), text, fill=TEXT, font=font)
    return img


def main():
    out = Path(__file__).parent / "assets" / "glm.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    base = draw(256)  # 以 256 为基准，PIL 自动缩放到各尺寸
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)]
    base.save(out, format="ICO", sizes=sizes)
    print(f"已生成 {out}  尺寸: {sizes}  ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

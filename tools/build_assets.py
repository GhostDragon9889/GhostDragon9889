"""Build the profile's local geometric banner assets with Pillow."""

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
INK = (232, 241, 248)
MUTED = (151, 175, 196)
CYAN = (105, 232, 215)
GRID = (21, 40, 58)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else BOLD if bold else FONT, size)


def tracked(draw, xy, text, size, color, spacing=3):
    x, y = xy
    face = font(size, mono=True)
    for char in text:
        draw.text((x, y), char, font=face, fill=color)
        x += draw.textlength(char, font=face) + spacing


def make_base(mobile=False):
    width, height = (640, 350) if mobile else (1200, 320)
    image = Image.new("RGB", (width, height), (10, 18, 29))
    draw = ImageDraw.Draw(image)
    # A subtle field, with the geometry carrying the visual weight.
    for y in range(height):
        t = y / height
        draw.line((0, y, width, y), fill=(10 + int(3*t), 18 + int(5*t), 29 + int(7*t)))
    for x in range(0, width, 32):
        for y in range(0, height, 32):
            draw.point((x, y), fill=GRID)
    draw.line((0, height-1, width, height-1), fill=(49, 82, 98))
    if mobile:
        tracked(draw, (32, 28), "RESEARCH / CODE / SIMULATION", 13, CYAN, 2)
        draw.text((29, 69), "GhostDragon", font=font(70, bold=True), fill=INK)
        draw.text((32, 165), "Reinforcement Learning", font=font(22), fill=INK)
        draw.text((32, 198), "Embodied AI / Robotics", font=font(22), fill=MUTED)
        tracked(draw, (32, 279), "READ. REPRODUCE. BUILD.", 15, MUTED, 2)
        route = [(450, 275), (486, 244), (524, 270), (555, 235), (606, 263)]
        draw.line(route, fill=(49, 107, 114), width=2)
        for x, y in route:
            draw.ellipse((x-5, y-5, x+5, y+5), fill=(13, 23, 36), outline=(68, 139, 144), width=2)
    else:
        tracked(draw, (48, 39), "RESEARCH / CODE / SIMULATION", 14, CYAN, 3)
        draw.text((43, 84), "GhostDragon", font=font(77, bold=True), fill=INK)
        draw.text((48, 195), "Reinforcement Learning / Embodied AI / Robotics", font=font(20), fill=MUTED)
        tracked(draw, (48, 265), "READ. REPRODUCE. BUILD.", 14, MUTED, 2)
        draw.line((752, 36, 752, 284), fill=GRID, width=1)
        layers = [[(815, 93), (815, 152), (815, 211)],
                  [(932, 73), (932, 132), (932, 191), (932, 250)],
                  [(1094, 113), (1094, 192)]]
        for group, next_group in zip(layers, layers[1:]):
            for x, y in group:
                for nx, ny in next_group:
                    if abs(y-ny) < 100:
                        draw.line((x, y, nx, ny), fill=(32, 60, 76), width=1)
        route = [(815, 152), (932, 132), (1094, 192)]
        draw.line(route, fill=(80, 170, 166), width=2)
        for group in layers:
            for x, y in group:
                draw.ellipse((x-8, y-8, x+8, y+8), fill=(13, 23, 36), outline=(69, 107, 125), width=2)
        for x, y in route:
            draw.ellipse((x-8, y-8, x+8, y+8), fill=(17, 51, 57), outline=CYAN, width=2)
        tracked(draw, (792, 277), "OBSERVE / LEARN / ACT", 11, MUTED, 1)
    return image, route


def route_point(route, progress):
    lengths = [math.dist(a, b) for a, b in zip(route, route[1:])]
    distance = sum(lengths) * progress
    for i, length in enumerate(lengths):
        if distance <= length:
            t = distance / length
            a, b = route[i:i+2]
            return a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t
        distance -= length
    return route[-1]


def build(mobile=False):
    base, route = make_base(mobile)
    name = "header-mobile" if mobile else "header"
    base.save(ASSETS / f"{name}.png", optimize=True)
    # Keep a shared palette to avoid color flicker; no flashes or large motion.
    palette_image = base.copy()
    palette_draw = ImageDraw.Draw(palette_image)
    for i, color in enumerate([CYAN, INK, (34, 76, 79), (26, 53, 63)]):
        palette_draw.rectangle((i*16, 0, i*16+15, 15), fill=color)
    palette = palette_image.quantize(colors=128)
    frames = []
    count = 36
    for i in range(count):
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        x, y = route_point(route, i / (count-1))
        # Fade the point at either end so the loop has no visible jump.
        alpha = min(1.0, i/4, (count-1-i)/4)
        for radius, color in [(10, (26, 53, 63)), (6, (34, 76, 79)), (3, CYAN)]:
            color = tuple(int(c*alpha+(13 if j==0 else 23 if j==1 else 36)*(1-alpha)) for j, c in enumerate(color))
            if alpha > 0:
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
        frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
    frames[0].save(ASSETS / f"{name}.gif", save_all=True, append_images=frames[1:], duration=140, loop=0, optimize=True, disposal=1)
    print(name, base.size, (ASSETS/f"{name}.gif").stat().st_size, "bytes")


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    build()
    build(mobile=True)

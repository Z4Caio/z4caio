"""One-off renderer for the profile banner. Not part of the published profile."""
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2400, 780
SCALE = 2
SW, SH = W * SCALE, H * SCALE

NAVY = (5, 10, 18)
CYAN = (103, 232, 249)
TEAL = (34, 211, 238)
AMBER = (245, 180, 70)
SAND = (18, 48, 46)
WHITE = (236, 246, 255)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def s(n):
    return int(n * SCALE)


def new_layer():
    return Image.new("RGBA", (SW, SH), (0, 0, 0, 0))


def glow(layer, radius):
    return layer.filter(ImageFilter.GaussianBlur(radius * SCALE))


def main():
    base = Image.new("RGBA", (SW, SH), (*NAVY, 255))
    px = base.load()
    top = (6, 12, 22)
    bottom = (4, 8, 14)
    for y in range(SH):
        c = lerp(top, bottom, y / (SH - 1))
        for x in range(0, SW, 2):
            px[x, y] = (*c, 255)
            if x + 1 < SW:
                px[x + 1, y] = (*c, 255)

    # Ambient light: cyan over the tank, amber over the iron.
    wash = new_layer()
    wd = ImageDraw.Draw(wash)
    wd.ellipse((s(-80), s(40), s(1280), s(820)), fill=(14, 116, 144, 70))
    wd.ellipse((s(1400), s(80), s(2500), s(760)), fill=(120, 72, 16, 46))
    base = Image.alpha_composite(base, glow(wash, 70))

    # Fine grid, stronger on the right so the tank stays calm.
    grid = new_layer()
    gd = ImageDraw.Draw(grid)
    step = s(48)
    for x in range(0, SW, step):
        alpha = 18 if x > s(1320) else 8
        gd.line([(x, 0), (x, SH)], fill=(148, 196, 214, alpha))
    for y in range(0, SH, step):
        gd.line([(0, y), (SW, y)], fill=(148, 196, 214, 8))
    base = Image.alpha_composite(base, grid)

    # Tank glass and water.
    tank = (s(96), s(132), s(1188), s(648))
    glass = new_layer()
    d = ImageDraw.Draw(glass)
    d.rounded_rectangle(tank, radius=s(36), fill=(8, 28, 38, 255), outline=(103, 232, 249, 150), width=s(3))
    inner = (tank[0] + s(16), tank[1] + s(16), tank[2] - s(16), tank[3] - s(16))
    d.rounded_rectangle(inner, radius=s(24), fill=(6, 42, 54, 255))
    base = Image.alpha_composite(base, glass)

    water = new_layer()
    wd = ImageDraw.Draw(water)
    for i, y in enumerate(range(inner[1], inner[3])):
        t = i / max(1, inner[3] - inner[1])
        col = lerp((18, 110, 132), (4, 36, 48), t)
        wd.line([(inner[0], y), (inner[2], y)], fill=(*col, 255))
    mask = Image.new("L", (SW, SH), 0)
    ImageDraw.Draw(mask).rounded_rectangle(inner, radius=s(24), fill=255)
    colored = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    colored.paste(water, mask=mask)
    base = Image.alpha_composite(base, colored)

    # Light shafts and surface.
    shafts = new_layer()
    sd = ImageDraw.Draw(shafts)
    surface_y = inner[1] + s(36)
    for x0, width in ((s(280), s(70)), (s(520), s(110)), (s(860), s(54))):
        sd.polygon(
            [
                (x0, surface_y),
                (x0 + width, surface_y),
                (x0 + width + s(80), inner[3] - s(70)),
                (x0 + s(30), inner[3] - s(70)),
            ],
            fill=(186, 244, 255, 28),
        )
    sd.rectangle((inner[0] + s(8), surface_y, inner[2] - s(8), surface_y + s(3)), fill=(236, 254, 255, 170))
    base = Image.alpha_composite(base, glow(shafts, 6))

    # Substrate and plants, clipped to the water.
    life = new_layer()
    ld = ImageDraw.Draw(life)
    ground = inner[3] - s(78)
    ld.rounded_rectangle(
        (inner[0], ground, inner[2], inner[3]),
        radius=s(8),
        fill=(*SAND, 255),
    )
    for i, gx in enumerate(range(inner[0] + s(30), inner[2] - s(20), s(46))):
        h = s(10 + (i * 17) % 14)
        ld.ellipse((gx, ground - h // 2, gx + s(22), ground + h), fill=(32, 78, 72, 255))

    def kelp(x, height, lean):
        pts = []
        steps = 14
        for i in range(steps):
            t = i / (steps - 1)
            yy = ground - int(height * t)
            xx = x + int(math.sin(t * 3.2) * lean)
            pts.append((xx, yy))
        ld.line(pts, fill=(20, 120, 112, 230), width=s(7))
        ld.line(pts, fill=(94, 234, 212, 90), width=s(2))

    kelp(inner[0] + s(70), s(250), s(16))
    kelp(inner[0] + s(118), s(190), s(-12))
    kelp(inner[2] - s(120), s(220), s(14))
    kelp(inner[2] - s(70), s(150), s(-10))

    def angelfish(cx, cy, flip=False):
        sign = -1 if flip else 1
        body = (
            cx - sign * s(78),
            cy - s(34),
            cx + sign * s(78),
            cy + s(34),
        )
        box = body if body[0] < body[2] else (body[2], body[1], body[0], body[3])
        ld.ellipse(box, fill=(226, 251, 255, 255))
        # Tall sail, the silhouette people recognize in a planted tank.
        sail = [
            (cx - sign * s(20), cy - s(20)),
            (cx - sign * s(8), cy - s(108)),
            (cx + sign * s(36), cy - s(78)),
            (cx + sign * s(58), cy - s(16)),
        ]
        anal = [
            (cx - sign * s(16), cy + s(18)),
            (cx - sign * s(4), cy + s(96)),
            (cx + sign * s(40), cy + s(62)),
            (cx + sign * s(52), cy + s(14)),
        ]
        ld.polygon(sail, fill=(45, 212, 191, 235))
        ld.polygon(anal, fill=(45, 212, 191, 220))
        tail_x = cx - sign * s(78)
        ld.polygon(
            [
                (tail_x, cy - s(10)),
                (tail_x - sign * s(58), cy - s(46)),
                (tail_x - sign * s(36), cy),
                (tail_x - sign * s(58), cy + s(46)),
                (tail_x, cy + s(10)),
            ],
            fill=(125, 211, 252, 255),
        )
        for stripe in (-s(18), s(8), s(32)):
            ld.line(
                [(cx + sign * stripe, cy - s(28)), (cx + sign * stripe - sign * s(6), cy + s(28))],
                fill=(14, 116, 144, 140),
                width=s(3),
            )
        eye_x = cx + sign * s(40)
        ld.ellipse((eye_x - s(7), cy - s(8), eye_x + s(7), cy + s(6)), fill=(6, 16, 24, 255))
        ld.ellipse((eye_x - s(2), cy - s(6), eye_x + s(3), cy - s(1)), fill=(255, 255, 255, 230))

    def tetra(cx, cy, scale, color, flip=False):
        sign = -1 if flip else 1
        body = [
            (cx + sign * s(46) * scale, cy),
            (cx + sign * s(8) * scale, cy - s(16) * scale),
            (cx - sign * s(34) * scale, cy - s(8) * scale),
            (cx - sign * s(34) * scale, cy + s(8) * scale),
            (cx + sign * s(8) * scale, cy + s(16) * scale),
        ]
        ld.polygon(body, fill=(*color, 255))
        ld.polygon(
            [
                (cx - sign * s(34) * scale, cy),
                (cx - sign * s(62) * scale, cy - s(18) * scale),
                (cx - sign * s(62) * scale, cy + s(18) * scale),
            ],
            fill=(186, 230, 253, 230),
        )
        eye_x = cx + sign * s(24) * scale
        ld.ellipse(
            (eye_x - s(4), cy - s(4), eye_x + s(4), cy + s(4)),
            fill=(6, 16, 24, 255),
        )

    def discus(cx, cy):
        r = s(46)
        ld.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(253, 186, 116, 255))
        ld.ellipse((cx - r + s(8), cy - r + s(6), cx + r - s(8), cy + r - s(6)), fill=(251, 146, 60, 255))
        for i, off in enumerate((-s(18), -s(6), s(6), s(18))):
            ld.arc(
                (cx - r + s(10), cy - r + s(8), cx + r - s(10), cy + r - s(8)),
                start=100 + i * 8,
                end=260 - i * 4,
                fill=(124, 45, 18, 180),
                width=s(2),
            )
            ld.line([(cx + off, cy - s(30)), (cx + off, cy + s(30))], fill=(124, 45, 18, 90), width=s(2))
        ld.polygon(
            [(cx - s(40), cy), (cx - s(62), cy - s(16)), (cx - s(62), cy + s(16))],
            fill=(253, 186, 116, 255),
        )
        ld.ellipse((cx + s(16), cy - s(6), cx + s(26), cy + s(4)), fill=(69, 26, 3, 255))

    angelfish(s(640), s(390))
    tetra(s(430), s(500), 1.15, (125, 211, 252), flip=True)
    discus(s(900), s(300))

    # Bubbles.
    for bx, by, br, a in (
        (1000, 470, 7, 150),
        (1036, 390, 11, 120),
        (980, 320, 5, 160),
        (1070, 280, 8, 100),
        (1010, 230, 4, 140),
        (1100, 360, 6, 110),
    ):
        ld.ellipse(
            (s(bx) - s(br), s(by) - s(br), s(bx) + s(br), s(by) + s(br)),
            outline=(224, 250, 255, a),
            width=s(2),
        )

    clipped = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    clipped.paste(life, mask=mask)
    base = Image.alpha_composite(base, clipped)

    # Glass highlight.
    shine = new_layer()
    sh = ImageDraw.Draw(shine)
    sh.arc(
        (tank[0] + s(18), tank[1] + s(18), tank[0] + s(220), tank[3] - s(18)),
        start=250,
        end=290,
        fill=(255, 255, 255, 80),
        width=s(8),
    )
    sh.rounded_rectangle(tank, radius=s(36), outline=(186, 244, 255, 90), width=s(2))
    base = Image.alpha_composite(base, shine)

    # Corner brackets around the tank.
    hud = new_layer()
    hd = ImageDraw.Draw(hud)
    arm = s(42)
    inset = s(18)
    corners = (
        (tank[0] - inset, tank[1] - inset, 1, 1),
        (tank[2] + inset, tank[1] - inset, -1, 1),
        (tank[0] - inset, tank[3] + inset, 1, -1),
        (tank[2] + inset, tank[3] + inset, -1, -1),
    )
    for x, y, dx, dy in corners:
        hd.line([(x, y), (x + dx * arm, y)], fill=(*CYAN, 200), width=s(3))
        hd.line([(x, y), (x, y + dy * arm)], fill=(*CYAN, 200), width=s(3))
    base = Image.alpha_composite(base, hud)

    # Barbell.
    iron = new_layer()
    idr = ImageDraw.Draw(iron)
    cy = s(400)
    bar_l, bar_r = s(1360), s(2260)
    bar_h = s(22)
    idr.rounded_rectangle(
        (bar_l, cy - bar_h // 2, bar_r, cy + bar_h // 2),
        radius=s(8),
        fill=(214, 222, 230, 255),
    )
    idr.rounded_rectangle(
        (bar_l, cy - bar_h // 2, bar_r, cy - bar_h // 2 + s(5)),
        radius=s(4),
        fill=(255, 255, 255, 90),
    )

    def plate(cx, radius, tone):
        idr.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(16, 18, 22, 255),
            outline=(*tone, 255),
            width=s(10),
        )
        inner = int(radius * 0.62)
        idr.ellipse(
            (cx - inner, cy - inner, cx + inner, cy + inner),
            outline=(*tone, 160),
            width=s(4),
        )
        hub = s(28)
        idr.ellipse((cx - hub, cy - hub, cx + hub, cy + hub), fill=(*tone, 230))
        # tick marks
        for ang in range(0, 360, 30):
            rad = math.radians(ang)
            r1 = radius - s(18)
            r2 = radius - s(8)
            idr.line(
                [
                    (cx + math.cos(rad) * r1, cy + math.sin(rad) * r1),
                    (cx + math.cos(rad) * r2, cy + math.sin(rad) * r2),
                ],
                fill=(*tone, 180),
                width=s(2),
            )

    plate(s(1500), s(168), AMBER)
    plate(s(2140), s(168), (103, 232, 249))
    # collars
    for cx in (s(1660), s(1980)):
        idr.rounded_rectangle((cx - s(16), cy - s(34), cx + s(16), cy + s(34)), radius=s(4), fill=(180, 190, 200, 255))

    base = Image.alpha_composite(base, iron)
    bloom = new_layer()
    bd = ImageDraw.Draw(bloom)
    bd.ellipse((s(1360), s(230), s(1680), s(570)), fill=(245, 180, 70, 50))
    bd.ellipse((s(1980), s(230), s(2300), s(570)), fill=(34, 211, 238, 40))
    base = Image.alpha_composite(base, glow(bloom, 28))

    # Wordmark.
    brand = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", s(34))
    mono = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", s(18))
    text = new_layer()
    td = ImageDraw.Draw(text)

    def spaced(text_value, xy, font, fill, gap):
        x, y = xy
        for ch in text_value:
            td.text((x, y), ch, font=font, fill=fill)
            x += font.getlength(ch) + gap
        return x

    spaced("Z4CAIO", (s(108), s(48)), brand, (*WHITE, 235), s(8))
    spaced("AQUA", (s(1508), s(168)), mono, (*AMBER, 220), s(6))
    spaced("IRON", (s(2068), s(168)), mono, (*CYAN, 220), s(6))
    spaced("24\u00b0C", (s(128), s(700)), mono, (148, 196, 214, 200), s(2))
    spaced("PETR\u00d3POLIS", (s(1888), s(700)), mono, (148, 196, 214, 180), s(3))

    base = Image.alpha_composite(base, text)

    # Vignette.
    vig = Image.new("L", (SW, SH), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse((s(-200), s(-180), s(2600), s(980)), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(s(50)))
    dark = Image.new("RGBA", (SW, SH), (0, 0, 0, 150))
    inv = vig.point(lambda p: 255 - p)
    dark.putalpha(inv)
    base = Image.alpha_composite(base, dark)

    out = base.resize((W, H), Image.Resampling.LANCZOS)
    out.convert("RGB").save("assets/banner.png", "PNG", optimize=True)
    print("wrote assets/banner.png", out.size)


if __name__ == "__main__":
    main()

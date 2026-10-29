"""Erzeugt Aufkleber, Reifenflanken-Prägung und Display-Inhalte als PNG (Pillow).

Schrift: Barlow (SIL OFL) aus public/assets/fonts, für Pillow einmal nach TTF umgewandelt.
Alle Namen und Marken sind erfunden.
"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHRIFTEN = os.path.join(WURZEL, "public", "assets", "fonts")
ZIEL = os.path.join(WURZEL, "var", "szene", "dekor")
_cache = {}


def schrift(gewicht, groesse, sc=True):
    vorhanden = (500, 600, 700) if sc else (400, 500, 600)
    gewicht = min(vorhanden, key=lambda g: abs(g - gewicht))
    datei = f"barlow-{'sc-' if sc else ''}{gewicht}"
    ttf = os.path.join(ZIEL, "..", "schriften", datei + ".ttf")
    if not os.path.exists(ttf):
        from fontTools.ttLib import TTFont
        os.makedirs(os.path.dirname(ttf), exist_ok=True)
        f = TTFont(os.path.join(SCHRIFTEN, datei + ".woff2"))
        f.flavor = None
        f.save(ttf)
    schluessel = (ttf, groesse)
    if schluessel not in _cache:
        _cache[schluessel] = ImageFont.truetype(ttf, groesse)
    return _cache[schluessel]


def schraeg(bild, faktor):
    b, h = bild.size
    rand = int(abs(faktor) * h)
    neu = Image.new("RGBA", (b + rand, h), (0, 0, 0, 0))
    neu.paste(bild, (rand if faktor > 0 else 0, 0))
    return neu.transform(neu.size, Image.AFFINE, (1, faktor, 0, 0, 1, 0), Image.BICUBIC)


def text_bild(text, groesse, farbe, gewicht=700, sc=True, abstand=0, rand=8):
    f = schrift(gewicht, groesse, sc)
    breite = 0
    for z in text:
        breite += f.getlength(z) + abstand
    hoehe = int(groesse * 1.25)
    img = Image.new("RGBA", (int(breite) + rand * 2, hoehe + rand * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = rand
    for z in text:
        d.text((x, rand), z, font=f, fill=farbe)
        x += f.getlength(z) + abstand
    return img.crop(img.getbbox()) if img.getbbox() else img


def rahmen_logo():
    """Großer Schriftzug fürs Unterrohr: sandfarben mit Kupferstrich, leicht kursiv."""
    schrift_b = text_bild("TRAIL", 300, (214, 205, 188, 255), 700, abstand=8)
    e9 = text_bild("E9", 300, (196, 120, 70, 255), 700, abstand=8)
    punkt = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(punkt).ellipse((6, 6, 58, 58), fill=(196, 120, 70, 255))
    breite = schrift_b.width + 60 + punkt.width + 60 + e9.width
    hoehe = max(schrift_b.height, e9.height) + 60
    img = Image.new("RGBA", (breite + 40, hoehe), (0, 0, 0, 0))
    img.paste(schrift_b, (20, 0), schrift_b)
    img.paste(punkt, (20 + schrift_b.width + 60, schrift_b.height // 2 - 32), punkt)
    img.paste(e9, (20 + schrift_b.width + 60 + punkt.width + 60, 0), e9)
    d = ImageDraw.Draw(img)
    d.rectangle((20, hoehe - 26, breite + 20, hoehe - 14), fill=(196, 120, 70, 255))
    img = schraeg(img, -0.18)
    img.save(os.path.join(ZIEL, "rahmen_logo.png"))
    return img.size


def oberrohr():
    t = text_bild("CARBON · 160 / 150 · 29", 90, (214, 205, 188, 230), 600, abstand=6)
    img = Image.new("RGBA", (t.width + 20, t.height + 20), (0, 0, 0, 0))
    img.paste(t, (10, 10), t)
    img.save(os.path.join(ZIEL, "oberrohr.png"))
    return img.size


def gabel():
    a = text_bild("TRAIL 38", 150, (230, 230, 230, 255), 700, abstand=4)
    b = text_bild("AIR · 160 MM · 3-WAY", 70, (200, 200, 200, 255), 500, abstand=3)
    img = Image.new("RGBA", (max(a.width, b.width) + 30, a.height + b.height + 50), (0, 0, 0, 0))
    img.paste(a, (15, 10), a)
    img.paste(b, (15, a.height + 34), b)
    img.save(os.path.join(ZIEL, "gabel.png"))
    return img.size


def felge():
    t = text_bild("TRAILGRIP  ·  AL 30  ·  29\"  ·  TUBELESS", 80, (232, 232, 230, 255), 600, abstand=6)
    img = Image.new("RGBA", (t.width + 20, t.height + 20), (0, 0, 0, 0))
    img.paste(t, (10, 10), t)
    img.save(os.path.join(ZIEL, "felge.png"))
    return img.size


def motor():
    t = text_bild("DRIVE 85", 120, (180, 182, 186, 255), 700, abstand=6)
    img = Image.new("RGBA", (t.width + 20, t.height + 20), (0, 0, 0, 0))
    img.paste(t, (10, 10), t)
    img.save(os.path.join(ZIEL, "motor.png"))
    return img.size


def inspektion():
    """Prüfplakette der Werkstatt (wie auf der alten Seite)."""
    img = Image.new("RGBA", (520, 360), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 519, 359), radius=26, fill=(240, 241, 236, 255))
    d.rounded_rectangle((0, 0, 519, 92), radius=26, fill=(14, 74, 76, 255))
    d.rectangle((0, 60, 519, 92), fill=(14, 74, 76, 255))
    d.text((28, 20), "Radhaus Fuhse", font=schrift(700, 54, False), fill=(240, 241, 236, 255))
    d.text((28, 120), "Inspektion", font=schrift(600, 44, False), fill=(27, 35, 38, 255))
    d.text((28, 176), "10 / 2026", font=schrift(700, 80, False), fill=(27, 35, 38, 255))
    d.text((28, 290), "Nächste: 10 / 2027", font=schrift(500, 34, False), fill=(27, 35, 38, 255))
    d.ellipse((380, 190, 480, 290), outline=(27, 35, 38, 255), width=7)
    d.line((402, 240, 424, 264, 462, 214), fill=(27, 35, 38, 255), width=8)
    img.save(os.path.join(ZIEL, "inspektion.png"))
    return img.size


def reifenflanke():
    """Höhenbild der Flankenschrift; x = Umfang (zweimal herum), y = Radius (innen unten)."""
    b, h = 8192, 256
    img = Image.new("L", (b, h), 0)
    teile = [("TRAILGRIP", 150, 700, 40), ("29 × 2.50", 64, 600, 30), ("63-622", 56, 600, 26), ("E-25 READY", 56, 600, 26),
             ("TUBELESS READY", 52, 600, 24), ("1.4 – 2.4 BAR / 20 – 35 PSI", 46, 500, 20), ("MADE IN EU", 44, 500, 18)]
    for runde in range(2):
        x = runde * b // 2 + 120
        for text, groesse, gewicht, abst in teile:
            t = text_bild(text, groesse, 255, gewicht, abstand=abst // 4).convert("L")
            t = t.transpose(Image.FLIP_TOP_BOTTOM)
            y = (h - t.height) // 2
            img.paste(255, (x, y), t)
            x += t.width + 140
        d = ImageDraw.Draw(img)
        d.rectangle((runde * b // 2 + 60, 18, runde * b // 2 + b // 2 - 60, 22), fill=150)
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    img.save(os.path.join(ZIEL, "reifenflanke.png"))
    return img.size


def displayinhalt(datei, kopf, gross=None, einheit="", zeilen=(), akku=0.86):
    """Inhalt des Farbdisplays (320 × 240), wie ihn die Seite für das Kapitel anzeigt."""
    img = Image.new("RGB", (320, 240), (6, 9, 10))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 320, 38), fill=(14, 74, 76))
    d.text((14, 6), kopf, font=schrift(600, 26), fill=(217, 244, 239))
    d.rounded_rectangle((232, 10, 296, 28), radius=3, outline=(217, 244, 239), width=2)
    d.rectangle((297, 15, 301, 23), fill=(217, 244, 239))
    d.rectangle((235, 13, 235 + int(58 * max(0, min(1, akku))), 25), fill=(79, 217, 138) if akku > 0.2 else (242, 201, 76))
    if gross is not None:
        d.text((14, 44), str(gross), font=schrift(700, 96), fill=(255, 255, 255))
        d.text((200, 104), einheit, font=schrift(500, 28, False), fill=(154, 184, 180))
    y = 172 if gross is not None else 56
    for text, ok in zeilen:
        farbe = (242, 201, 76) if ok is False else (79, 217, 138) if ok else (217, 244, 239)
        d.text((14, y), text, font=schrift(500, 26, False), fill=farbe)
        y += 32
    img.save(datei)


def alle():
    os.makedirs(ZIEL, exist_ok=True)
    masse = {
        "rahmen_logo": rahmen_logo(),
        "oberrohr": oberrohr(),
        "gabel": gabel(),
        "felge": felge(),
        "motor": motor(),
        "inspektion": inspektion(),
        "reifenflanke": reifenflanke(),
    }
    return masse


if __name__ == "__main__":
    print(alle())

#!/usr/bin/env python3
"""Macht aus den gerenderten PNGs die Bildfolge der Startseite.

    python scripts/kodieren.py

Liest var/szene/bilder/bild_XXXX.png und var/szene/lagen.json, schreibt nach public/assets/werkstatt/
(gross: 1280 × 720, klein: 854 × 480, WebP), dazu manifest.json, lagen.json, die Standbilder für
das HTML und das Vorschaubild für soziale Netze. docs/ bekommt dieselben Dateien.

Nachbearbeitung wie bei einem Foto: leichte Vignette, minimaler Farbsaum am Rand, etwas Schärfe.
"""

import json
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUELLE = os.path.join(WURZEL, "var", "szene", "bilder")
LAGEN = os.path.join(WURZEL, "var", "szene", "lagen.json")
LAGEN_WEB = os.path.join(WURZEL, "var", "szene", "lagen-web.json")
ZIEL = os.path.join(WURZEL, "public", "assets", "werkstatt")
BILDER = os.path.join(WURZEL, "public", "assets", "bilder")

SAETZE = {"gross": (1280, 720, 78), "klein": (854, 480, 74)}


def nachbearbeiten(img):
    b, h = img.size
    a = np.asarray(img).astype(np.float32) / 255.0
    yy, xx = np.mgrid[0:h, 0:b]
    rx = (xx - b / 2) / (b / 2)
    ry = (yy - h / 2) / (h / 2)
    r2 = (rx * rx * (b / h) + ry * ry) / (b / h + 1)
    t = np.clip((r2 - 0.25) / 0.75, 0, 1)
    vignette = 1 - 0.16 * t * t * (3 - 2 * t)
    a *= vignette[..., None]
    img = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))
    # Farbsaum: Rot minimal größer, Blau minimal kleiner als Grün
    r, g, bl = img.split()
    e = 0.0009
    rg = r.resize((round(b * (1 + e)), round(h * (1 + e))), Image.LANCZOS)
    dx, dy = (rg.width - b) // 2, (rg.height - h) // 2
    r = rg.crop((dx, dy, dx + b, dy + h))
    bk = bl.resize((round(b * (1 - e)), round(h * (1 - e))), Image.LANCZOS)
    bl2 = bl.copy()
    bl2.paste(bk, ((b - bk.width) // 2, (h - bk.height) // 2))
    img = Image.merge("RGB", (r, g, bl2))
    return img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=35, threshold=2))


def main():
    import bpy  # noqa: F401 – stellt mathutils bereit, das szene.regie braucht
    from szene import regie

    n = regie.KAPITEL * regie.BILDER_JE_KAPITEL + 1
    for name in SAETZE:
        os.makedirs(os.path.join(ZIEL, name), exist_ok=True)
    fertig = 0
    for i in range(n):
        quelle = os.path.join(QUELLE, f"bild_{i:04d}.png")
        if not os.path.exists(quelle):
            continue
        ziele = {name: os.path.join(ZIEL, name, f"bild_{i:04d}.webp") for name in SAETZE}
        if all(os.path.exists(z) and os.path.getmtime(z) > os.path.getmtime(quelle) for z in ziele.values()):
            fertig += 1
            continue
        img = nachbearbeiten(Image.open(quelle).convert("RGB"))
        for name, (b, h, q) in SAETZE.items():
            klein = img if img.size == (b, h) else img.resize((b, h), Image.LANCZOS)
            klein.save(ziele[name], "WEBP", quality=q, method=6)
        fertig += 1
    print(f"{fertig} von {n} Bildern kodiert")

    schluessel = [k * regie.BILDER_JE_KAPITEL + round(0.3 * regie.BILDER_JE_KAPITEL) for k in range(regie.KAPITEL)]
    manifest = {
        "bilder": n,
        "je_kapitel": regie.BILDER_JE_KAPITEL,
        "kapitel": regie.KAPITEL,
        "saetze": {name: {"breite": b, "hoehe": h, "muster": f"{name}/bild_{{i}}.webp"} for name, (b, h, _) in SAETZE.items()},
        "schluessel": schluessel,
        "befunde": [{"titel": d["titel"], "wert": d["wert"], "stand": d["stand"], "x": d["anker"][0]} for d in regie.BEFUNDE],
        "teile": {name: [kennung, bezeichnung] for name, (_, kennung, bezeichnung) in regie.MARKIERUNGEN.items()},
    }
    with open(os.path.join(ZIEL, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))
    # lagen-web.json (aus rendern.py --nur-lagen) ist vollständig; lagen.json schreibt der Renderlauf nebenbei
    datei = LAGEN_WEB if os.path.exists(LAGEN_WEB) else LAGEN
    roh = json.load(open(datei)) if os.path.exists(datei) else {}
    lagen = [roh.get(str(i)) for i in range(n)]
    with open(os.path.join(ZIEL, "lagen.json"), "w") as f:
        json.dump(lagen, f, separators=(",", ":"))

    # Standbild im HTML (sichtbar, bevor die Folge lädt) und Vorschaubild für Links
    erstes = os.path.join(QUELLE, "bild_0000.png")
    if os.path.exists(erstes):
        img = nachbearbeiten(Image.open(erstes).convert("RGB"))
        img.save(os.path.join(BILDER, "werkstatt-1280.webp"), "WEBP", quality=82, method=6)
        img.resize((854, 480), Image.LANCZOS).save(os.path.join(BILDER, "werkstatt-854.webp"), "WEBP", quality=80, method=6)
    halt = os.path.join(QUELLE, f"bild_{schluessel[0]:04d}.png")
    if os.path.exists(halt):
        img = nachbearbeiten(Image.open(halt).convert("RGB"))
        b, h = img.size
        hoehe = round(b * 630 / 1200)
        img.crop((0, (h - hoehe) // 2, b, (h - hoehe) // 2 + hoehe)).resize((1200, 630), Image.LANCZOS).save(
            os.path.join(BILDER, "vorschau-1200.jpg"), "JPEG", quality=84, optimize=True, progressive=True)

    # Vorführfassung auf GitHub Pages bekommt dieselben Dateien
    docs = os.path.join(WURZEL, "docs", "assets")
    if os.path.isdir(docs):
        shutil.copytree(ZIEL, os.path.join(docs, "werkstatt"), dirs_exist_ok=True)
        for datei in ("werkstatt-1280.webp", "werkstatt-854.webp", "vorschau-1200.jpg"):
            if os.path.exists(os.path.join(BILDER, datei)):
                shutil.copy2(os.path.join(BILDER, datei), os.path.join(docs, "bilder", datei))
    groesse = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(ZIEL) for f in fs)
    print(f"Bildfolge: {groesse / 1e6:.1f} MB in {ZIEL}")


if __name__ == "__main__":
    main()

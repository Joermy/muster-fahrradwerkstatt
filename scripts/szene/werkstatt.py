"""Die Werkstatt um das Rad: Raum, Möbel, Werkzeug, Licht. Maße in Millimetern, Boden bei z = BODEN.

Ein heller, aufgeräumter Raum: geschliffener Beton, weiß gestrichener Kalksandstein, Stahlfensterband
mit Tageslicht, Werkbank mit Eichenplatte, Werkzeugwand aus Birke-Multiplex.
"""

import math
import random

import bpy
from mathutils import Matrix, Vector

from .werkzeug import TAU, kasten, kreisprofil, netz, platte, torus, verbinden, zylinder

BODEN = -274.0
DECKE = 3300.0
X0, X1 = -2700.0, 4300.0
Y0, Y1 = -4600.0, 2400.0
BANK_HOEHE = BODEN + 920.0
BANK_X0, BANK_X1 = -1400.0, 2500.0
BANK_TIEFE = 680.0
PLATTE_Z0, PLATTE_Z1 = BANK_HOEHE + 140.0, BANK_HOEHE + 1300.0
FENSTER_Y0, FENSTER_Y1 = -3900.0, 1900.0
BRUESTUNG = BODEN + 950.0
STURZ = BODEN + 3050.0

ZUFALL = random.Random(7)

M = {
    "beton": "Beton", "ziegel": "Ziegel_weiss", "putz": "Putz", "decke": "Decke", "sockel": "Sockel", "birke": "Birke", "eiche": "Eiche",
    "anthrazit": "Anthrazit", "schwarz": "Schwarz_matt", "stahl_verz": "Verzinkt", "alu": "Alu", "chrom": "Chrom", "gummi": "Gummi",
    "gummi_matte": "Gummimatte", "kunststoff_rot": "Griff_rot", "kunststoff_gelb": "Griff_gelb", "kunststoff_schwarz": "Kunststoff",
    "kunststoff_blau": "Griff_blau", "petrol": "Petrol", "karton": "Karton", "papier": "Papier", "tafel": "Tafel", "glas": "Fensterglas",
    "led": "LED_band", "led_warm": "LED_warm", "aussen": "Aussen",
}


def torus_alt(name, mitte, achse, r_gross, r_klein, mat, um=96, quer=16, profil=None):
    if profil is None:
        profil = kreisprofil(r_gross, r_klein, quer)
    return torus(name, mitte, achse, profil, mat, um)


def platte_alt(name, umriss, dicke, mat, fase=0.0, ebene="xz", ort=(0, 0, 0), loecher=()):
    """Umriss in x/z, Dicke nach -y (vor der Rückwand)."""
    m = Matrix.Translation(Vector(ort)) @ Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    return platte(name, umriss, dicke, mat, fase, m, loecher)


def raum(M):
    teile = {}
    teile["boden"] = netz("boden", [(X0, Y0, BODEN), (X1, Y0, BODEN), (X1, Y1, BODEN), (X0, Y1, BODEN)], [(0, 1, 2, 3)], M["beton"])
    teile["decke"] = netz("decke", [(X0, Y0, DECKE), (X0, Y1, DECKE), (X1, Y1, DECKE), (X1, Y0, DECKE)], [(0, 1, 2, 3)], M["decke"])

    # Rückwand: Kalksandstein, unten dunkler Sockel
    hinten = [netz("wand_hinten", [(X0, Y1, BODEN + 120), (X1, Y1, BODEN + 120), (X1, Y1, DECKE), (X0, Y1, DECKE)], [(0, 3, 2, 1)], M["ziegel"])]
    hinten.append(netz("sockel_hinten", [(X0, Y1, BODEN), (X1, Y1, BODEN), (X1, Y1, BODEN + 120), (X0, Y1, BODEN + 120)], [(0, 3, 2, 1)], M["sockel"]))
    teile["wand_hinten"] = verbinden("wand_hinten", hinten)

    # Rechte Wand: Putz, petrolfarbener Sockel
    rechts = [netz("wand_rechts", [(X1, Y0, BODEN + 1200), (X1, Y1, BODEN + 1200), (X1, Y1, DECKE), (X1, Y0, DECKE)], [(0, 3, 2, 1)], M["putz"]),
              netz("sockel_rechts", [(X1, Y0, BODEN), (X1, Y1, BODEN), (X1, Y1, BODEN + 1200), (X1, Y0, BODEN + 1200)], [(0, 3, 2, 1)], M["sockel"])]
    teile["wand_rechts"] = verbinden("wand_rechts", rechts)

    # Vordere Wand mit Sektionaltor
    vorn = []
    tor_x0, tor_x1, tor_h = -1400.0, 1800.0, BODEN + 2800
    for (a, b, c, d) in (((X0, tor_x0), (BODEN, DECKE), None, None), ((tor_x1, X1), (BODEN, DECKE), None, None), ((tor_x0, tor_x1), (tor_h, DECKE), None, None)):
        vorn.append(netz("wand_vorn", [(a[0], Y0, b[0]), (a[1], Y0, b[0]), (a[1], Y0, b[1]), (a[0], Y0, b[1])], [(0, 1, 2, 3)], M["putz"]))
    teile["wand_vorn"] = verbinden("wand_vorn", vorn)
    tor = []
    sektionen = 5
    hs = (tor_h - BODEN) / sektionen
    for i in range(sektionen):
        z0 = BODEN + i * hs
        tor.append(kasten(f"Sektion{i}", ((tor_x0 + tor_x1) / 2, Y0 + 30, z0 + hs / 2), (tor_x1 - tor_x0, 40, hs - 6), M["putz"] if i != 3 else M["anthrazit"], fase=4))
        if i == 3:
            for j in range(6):
                bx = tor_x0 + 200 + j * (tor_x1 - tor_x0 - 400) / 5.0
                tor.append(kasten(f"Torfenster{i}{j}", (bx, Y0 + 52, z0 + hs / 2), (380, 6, hs * 0.55), M["aussen"]))
        else:
            for j in range(3):
                tor.append(kasten(f"Sicke{i}{j}", ((tor_x0 + tor_x1) / 2, Y0 + 51, z0 + hs * (0.25 + 0.25 * j)), (tor_x1 - tor_x0 - 60, 3, 10), M["putz"], fase=1.5))
    for x in (tor_x0 - 60, tor_x1 + 60):
        tor.append(kasten("Torzarge", (x, Y0 + 40, (BODEN + tor_h) / 2), (110, 80, tor_h - BODEN), M["anthrazit"], fase=4))
    teile["tor"] = verbinden("tor", tor)

    # Linke Wand: Stahlfensterband über Brüstung
    links = []
    bruestung = BODEN + 950.0
    sturz = BODEN + 3050.0
    f_y0, f_y1 = -3900.0, 1900.0
    links.append(netz("wand_links_u", [(X0, Y0, BODEN), (X0, Y1, BODEN), (X0, Y1, bruestung), (X0, Y0, bruestung)], [(0, 3, 2, 1)], M["ziegel"]))
    links.append(netz("wand_links_o", [(X0, Y0, sturz), (X0, Y1, sturz), (X0, Y1, DECKE), (X0, Y0, DECKE)], [(0, 3, 2, 1)], M["ziegel"]))
    links.append(netz("wand_links_v", [(X0, Y0, bruestung), (X0, f_y0, bruestung), (X0, f_y0, sturz), (X0, Y0, sturz)], [(0, 3, 2, 1)], M["ziegel"]))
    links.append(netz("wand_links_h", [(X0, f_y1, bruestung), (X0, Y1, bruestung), (X0, Y1, sturz), (X0, f_y1, sturz)], [(0, 3, 2, 1)], M["ziegel"]))
    # Laibung
    for (ya, yb) in ((f_y0, f_y0), (f_y1, f_y1)):
        links.append(netz("laibung", [(X0 - 240, ya, bruestung), (X0, ya, bruestung), (X0, ya, sturz), (X0 - 240, ya, sturz)], [(0, 1, 2, 3)] if ya == f_y1 else [(0, 3, 2, 1)], M["putz"]))
    links.append(netz("laibung_u", [(X0 - 240, f_y0, bruestung), (X0 - 240, f_y1, bruestung), (X0, f_y1, bruestung), (X0, f_y0, bruestung)], [(0, 1, 2, 3)], M["putz"]))
    links.append(netz("laibung_o", [(X0 - 240, f_y0, sturz), (X0, f_y0, sturz), (X0, f_y1, sturz), (X0 - 240, f_y1, sturz)], [(0, 1, 2, 3)], M["putz"]))
    links.append(kasten("Fensterbank", (X0 + 10, (f_y0 + f_y1) / 2, bruestung - 15), (100, f_y1 - f_y0 + 40, 30), M["anthrazit"], fase=3))
    teile["wand_links"] = verbinden("wand_links", links)

    fenster = []
    xf = X0 - 120
    felder_y, felder_z = 12, 4
    for i in range(felder_y + 1):
        y = f_y0 + (f_y1 - f_y0) * i / felder_y
        breit = 60 if i % 3 == 0 else 32
        fenster.append(kasten(f"Sprosse_y{i}", (xf, y, (bruestung + sturz) / 2), (50, breit, sturz - bruestung), M["schwarz"], fase=2))
    for j in range(felder_z + 1):
        z = bruestung + (sturz - bruestung) * j / felder_z
        breit = 60 if j in (0, felder_z) else 32
        fenster.append(kasten(f"Sprosse_z{j}", (xf, (f_y0 + f_y1) / 2, z), (50, f_y1 - f_y0, breit), M["schwarz"], fase=2))
    fenster.append(netz("scheibe", [(xf, f_y0, bruestung), (xf, f_y1, bruestung), (xf, f_y1, sturz), (xf, f_y0, sturz)], [(0, 1, 2, 3)], M["glas"]))
    teile["fenster"] = verbinden("fenster", fenster)
    return teile


def leuchten(M):
    teile = []
    for x in (-900.0, 1200.0, 3200.0):
        y0, y1 = -3600.0, 1600.0
        z = DECKE - 420
        teile.append(kasten("Leuchte", (x, (y0 + y1) / 2, z + 30), (90, y1 - y0, 60), M["anthrazit"], fase=3))
        teile.append(kasten("Diffusor", (x, (y0 + y1) / 2, z - 1), (70, y1 - y0 - 20, 4), M["led"]))
        for y in (y0 + 300, y1 - 300):
            teile.append(zylinder("Seil", (x, y, z + 60), (x, y, DECKE), 1.0, M["chrom"], 6))
    # Pendelleuchte über dem Montageplatz
    p = Vector((560.0, -150.0, DECKE - 900))
    profil = [(4, 0), (34, 0), (40, -30), (60, -70), (140, -150), (215, -230), (240, -248), (236, -252), (210, -236), (134, -156), (55, -76), (35, -36), (4, -36)]
    schirm = torus_alt("Schirm", p, (0, 0, 1), 0, 0, M["anthrazit"], um=64, profil=[(r, z) for (r, z) in profil])
    teile.append(schirm)
    innen = torus_alt("Schirm_innen", p + Vector((0, 0, -2)), (0, 0, 1), 0, 0, M["putz"], um=64, profil=[(r * 0.985, z) for (r, z) in reversed(profil[3:9])])
    teile.append(innen)
    teile.append(zylinder("Fassung", p + Vector((0, 0, -20)), p + Vector((0, 0, -95)), 26, M["anthrazit"], 24))
    teile.append(zylinder("Leuchtmittel", p + Vector((0, 0, -95)), p + Vector((0, 0, -100)), 52, M["led_warm"], 32))
    teile.append(zylinder("Kabel", p, Vector((p.x, p.y, DECKE)), 3.0, M["schwarz"], 8))
    return verbinden("leuchten", teile)


# ---------------------------------------------------------------- Werkbank und Werkzeug


def schrank(x0, x1, M, schubladen):
    teile = []
    tiefe = BANK_TIEFE - 40
    y_vorn = Y1 - 30 - tiefe
    h = BANK_HOEHE - 40 - (BODEN + 100)
    teile.append(kasten("Korpus", ((x0 + x1) / 2, Y1 - 30 - tiefe / 2, BODEN + 100 + h / 2), (x1 - x0, tiefe, h), M["anthrazit"], fase=4))
    teile.append(kasten("Sockel", ((x0 + x1) / 2, Y1 - 30 - tiefe / 2 + 40, BODEN + 50), (x1 - x0 - 40, tiefe - 80, 100), M["schwarz"], fase=2))
    z = BODEN + 100 + h
    for hoehe in schubladen:
        z -= hoehe
        mitte_z = z + hoehe / 2
        teile.append(kasten("Front", ((x0 + x1) / 2, y_vorn - 9, mitte_z), (x1 - x0 - 16, 18, hoehe - 8), M["anthrazit"], fase=3))
        teile.append(kasten("Griffleiste", ((x0 + x1) / 2, y_vorn - 24, mitte_z + hoehe / 2 - 26), (x1 - x0 - 120, 14, 14), M["alu"], fase=3))
    return teile


def werkbank(M):
    teile = []
    x0, x1 = BANK_X0, BANK_X1
    teile += schrank(x0, x0 + 600, M, [140, 140, 180, 240, 0])
    teile += schrank(x1 - 600, x1, M, [120, 120, 120, 160, 260])
    teile += schrank(x0 + 1600, x0 + 2200, M, [240, 260, 260])
    # offene Fächer dazwischen
    for (a, b) in ((x0 + 600, x0 + 1600), (x0 + 2200, x1 - 600)):
        teile.append(kasten("Zwischenboden", ((a + b) / 2, Y1 - 30 - (BANK_TIEFE - 40) / 2, BODEN + 260), (b - a, BANK_TIEFE - 60, 25), M["anthrazit"], fase=2))
        teile.append(kasten("Rueckwand", ((a + b) / 2, Y1 - 40, (BODEN + BANK_HOEHE) / 2), (b - a, 20, BANK_HOEHE - BODEN - 40), M["anthrazit"]))
    # Arbeitsplatte
    teile.append(kasten("Platte", ((x0 + x1) / 2, Y1 - BANK_TIEFE / 2 - 10, BANK_HOEHE - 20), (x1 - x0 + 40, BANK_TIEFE, 40), M["eiche"], fase=3))
    return teile


def maulschluessel(laenge, M):
    hb = laenge * 0.038
    R = laenge * 0.085
    Rj = laenge * 0.1
    o = Rj * 0.52
    umr = []
    aL = math.pi / 2 + math.asin(hb / R)
    aR = math.pi / 2 - math.asin(hb / R) + TAU
    for i in range(17):
        w = aL + (aR - aL) * i / 16
        umr.append((R * math.cos(w), R * math.sin(w)))
    b0 = -math.pi / 2 + math.asin(hb / Rj)
    b1 = math.pi / 2 - math.asin(o / Rj)
    for i in range(9):
        w = b0 + (b1 - b0) * i / 8
        umr.append((Rj * math.cos(w), laenge + Rj * math.sin(w)))
    umr += [(o, laenge - Rj * 0.1), (-o, laenge - Rj * 0.1)]
    c0 = math.pi / 2 + math.asin(o / Rj)
    c1 = 3 * math.pi / 2 - math.asin(hb / Rj)
    for i in range(9):
        w = c0 + (c1 - c0) * i / 8
        umr.append((Rj * math.cos(w), laenge + Rj * math.sin(w)))
    loch = [(R * 0.55 * math.cos(TAU * i / 12), R * 0.55 * math.sin(TAU * i / 12)) for i in range(12)]
    return umr, [loch]


def werkzeugwand(M):
    teile = []
    y = Y1 - 22
    teile.append(kasten("Lochplatte", ((BANK_X0 + BANK_X1) / 2, Y1 - 10, (PLATTE_Z0 + PLATTE_Z1) / 2), (BANK_X1 - BANK_X0 - 100, 20, PLATTE_Z1 - PLATTE_Z0), M["birke"], fase=2))
    # Schienen
    for z in (PLATTE_Z0 + 380, PLATTE_Z0 + 820):
        teile.append(kasten("Schiene", ((BANK_X0 + BANK_X1) / 2, y - 6, z), (BANK_X1 - BANK_X0 - 300, 12, 40), M["alu"], fase=2))
    # Maulschlüsselsatz
    x = BANK_X0 + 250
    for i, l in enumerate([230, 215, 200, 185, 170, 160, 150, 140, 130, 120]):
        umr, loecher = maulschluessel(l, M)
        s = platte_alt(f"Schluessel{i}", umr, 4.5, M["chrom"], fase=0.8, ebene="xz", loecher=loecher)
        s.data.transform(Matrix.Translation(Vector((x + i * 46, y - 14, PLATTE_Z0 + 380 - l - 30))))
        teile.append(s)
        teile.append(zylinder("Haken", (x + i * 46, y - 6, PLATTE_Z0 + 380 - 22), (x + i * 46, y - 40, PLATTE_Z0 + 380 - 18), 2.5, M["chrom"], 8))
    # Schraubendreher
    x = BANK_X0 + 880
    for i in range(7):
        laenge = 90 + (i % 4) * 25
        xx = x + i * 52
        zt = PLATTE_Z0 + 820 - 40
        farbe = M["kunststoff_rot"] if i % 2 == 0 else M["kunststoff_gelb"]
        teile.append(zylinder("Heft", (xx, y - 40, zt), (xx, y - 40, zt - 105), 15, farbe, 16, r2=13))
        teile.append(zylinder("Klinge", (xx, y - 40, zt - 105), (xx, y - 40, zt - 105 - laenge), 3.0 + (i % 3) * 0.6, M["chrom"], 10))
    teile.append(kasten("Halter", (x + 156, y - 28, PLATTE_Z0 + 820 - 30), (420, 50, 18), M["anthrazit"], fase=2))
    # Inbusschlüssel
    x = BANK_X0 + 1330
    for i in range(9):
        s = 2 + i * 0.5
        lang = 80 + i * 14
        xx = x + i * 26
        zt = PLATTE_Z0 + 820 - 30
        teile.append(zylinder("Inbus_lang", (xx, y - 30, zt), (xx, y - 30, zt - lang), s, M["kunststoff_schwarz"], 6))
        teile.append(zylinder("Inbus_kurz", (xx, y - 30, zt), (xx, y - 30 - 30 - s * 4, zt), s, M["kunststoff_schwarz"], 6))
    teile.append(kasten("Inbushalter", (x + 104, y - 24, PLATTE_Z0 + 820 - 22), (270, 34, 16), M["kunststoff_schwarz"], fase=2))
    # Zangen
    x = BANK_X0 + 1720
    for i in range(4):
        l = 180 + i * 20
        xx = x + i * 90
        zt = PLATTE_Z0 + 820 - 50
        for s in (-1, 1):
            griff = [(xx + s * 4, zt), (xx + s * 22, zt - l * 0.45), (xx + s * 14, zt - l)]
            for j in range(2):
                a, b = Vector((griff[j][0], y - 28 - s * 2, griff[j][1])), Vector((griff[j + 1][0], y - 28 - s * 2, griff[j + 1][1]))
                teile.append(zylinder("Zangengriff", a, b, 7.5 if j else 6, M["kunststoff_rot"] if i % 2 else M["kunststoff_blau"], 10))
        teile.append(kasten("Zangenkopf", (xx, y - 28, zt + 30), (22, 12, 70), M["chrom"], fase=4))
        teile.append(zylinder("Zangenhaken", (xx, y - 6, zt + 70), (xx, y - 40, zt + 74), 2.5, M["chrom"], 8))
    # Kettenpeitsche, Pedalschlüssel, Drehmomentschlüssel
    x = BANK_X0 + 2200
    zt = PLATTE_Z0 + 820 - 30
    teile.append(zylinder("Peitschengriff", (x, y - 30, zt), (x, y - 30, zt - 160), 13, M["kunststoff_schwarz"], 12))
    teile.append(kasten("Peitschenstab", (x, y - 30, zt - 260), (26, 6, 200), M["chrom"], fase=2))
    for k in range(18):
        teile.append(kasten("Kettenglied", (x + 18, y - 30, zt - 160 - k * 12.7), (10, 8, 12), M["stahl_verz"], fase=1))
    x += 120
    teile.append(zylinder("Pedalgriff", (x, y - 30, zt), (x, y - 30, zt - 150), 14, M["kunststoff_blau"], 12))
    teile.append(kasten("Pedalstab", (x, y - 30, zt - 260), (34, 6, 220), M["chrom"], fase=3))
    x += 120
    teile.append(zylinder("Momentgriff", (x, y - 34, zt), (x, y - 34, zt - 140), 15, M["kunststoff_schwarz"], 14))
    teile.append(zylinder("Momentrohr", (x, y - 34, zt - 140), (x, y - 34, zt - 420), 11, M["chrom"], 14))
    teile.append(zylinder("Momentkopf", (x, y - 20, zt - 435), (x, y - 50, zt - 435), 19, M["chrom"], 18))
    # Reifenheber und Kassettenwerkzeuge
    x = BANK_X0 + 2600
    for i, f in enumerate((M["kunststoff_blau"], M["kunststoff_gelb"], M["kunststoff_schwarz"])):
        teile.append(kasten("Reifenheber", (x + i * 34, y - 30, zt - 60), (22, 6, 115), f, fase=2.5))
    for i in range(3):
        teile.append(zylinder("Nuss", (x + 130 + i * 52, y - 10, zt - 40), (x + 130 + i * 52, y - 52, zt - 40), 16 + i * 2, M["chrom"], 16))
    teile.append(zylinder("Hammerstiel", (x + 330, y - 30, zt), (x + 330, y - 30, zt - 240), 11, M["eiche"], 12))
    teile.append(zylinder("Hammerkopf", (x + 300, y - 30, zt - 250), (x + 360, y - 30, zt - 250), 28, M["gummi"], 16))
    # Regal über der Wand mit Kisten
    regal_z = PLATTE_Z1 + 240
    teile.append(kasten("Regalbrett", ((BANK_X0 + BANK_X1) / 2, Y1 - 160, regal_z), (BANK_X1 - BANK_X0 - 100, 320, 30), M["birke"], fase=2))
    for x in (BANK_X0 + 300, (BANK_X0 + BANK_X1) / 2, BANK_X1 - 300):
        teile.append(kasten("Konsole", (x, Y1 - 150, regal_z - 120), (30, 280, 220), M["anthrazit"], fase=2))
    x = BANK_X0 + 120
    while x < BANK_X1 - 400:
        b = ZUFALL.choice([300, 360, 420, 260])
        h = ZUFALL.choice([180, 220, 260, 300])
        if ZUFALL.random() < 0.18:
            x += 160
            continue
        teile.append(kasten("Kiste", (x + b / 2, Y1 - 160, regal_z + 15 + h / 2), (b - 14, 290, h), M["karton"], fase=3))
        teile.append(kasten("Etikett", (x + b / 2, Y1 - 160 - 147, regal_z + 15 + h * 0.62), (b * 0.5, 2, h * 0.25), M["papier"]))
        x += b
    return teile


def auf_der_bank(M):
    teile = []
    z = BANK_HOEHE
    # Schraubstock
    sx, sy = BANK_X0 + 260, Y1 - BANK_TIEFE + 110
    teile.append(kasten("Stockfuss", (sx, sy, z + 25), (150, 160, 50), M["anthrazit"], fase=8))
    teile.append(kasten("Backe_fest", (sx, sy - 10, z + 110), (160, 60, 120), M["anthrazit"], fase=8))
    teile.append(kasten("Backe_lose", (sx, sy - 120, z + 110), (160, 60, 120), M["anthrazit"], fase=8))
    teile.append(kasten("Schiene", (sx, sy - 60, z + 70), (80, 220, 40), M["anthrazit"], fase=3))
    teile.append(zylinder("Spindel", (sx, sy - 150, z + 80), (sx, sy - 230, z + 80), 10, M["chrom"], 12))
    teile.append(zylinder("Knebel", (sx - 110, sy - 232, z + 80), (sx + 110, sy - 232, z + 80), 6, M["chrom"], 10))
    for s in (-1, 1):
        teile.append(kasten("Schutzbacke", (sx, sy - 40 - 50 * (s + 1) / 2 * 1.4, z + 150), (164, 14, 44), M["gummi"], fase=3))
    # Zentrierständer
    zx, zy = BANK_X1 - 420, Y1 - 330
    teile.append(kasten("Zentrierfuss", (zx, zy, z + 15), (420, 160, 30), M["anthrazit"], fase=6))
    for s in (-1, 1):
        a = Vector((zx + s * 190, zy, z + 30))
        b = Vector((zx + s * 170, zy, z + 420))
        teile.append(zylinder("Zentrierarm", a, b, 14, M["anthrazit"], 14))
        teile.append(kasten("Zentrierklemme", (b.x, zy, b.z + 20), (40, 60, 50), M["alu"], fase=5))
    teile.append(kasten("Messarm", (zx - 170, zy - 40, z + 380), (40, 20, 70), M["alu"], fase=3))
    # Laufrad im Zentrierständer
    teile += laufrad_einfach(Vector((zx, zy, z + 440)), (0, 1, 0), 300, M, speichen=28)
    # Teileschalen und Tasse
    for i in range(3):
        teile.append(kasten("Schale", (BANK_X0 + 1500 + i * 160, Y1 - 200, z + 22), (140, 200, 44), M["anthrazit"], fase=6))
    teile.append(zylinder("Tasse", (BANK_X0 + 1300, Y1 - 470, z), (BANK_X0 + 1300, Y1 - 470, z + 95), 42, M["papier"], 24))
    teile.append(kasten("Tablet", (BANK_X0 + 2000, Y1 - 420, z + 6), (250, 180, 10), M["kunststoff_schwarz"], fase=4))
    teile.append(kasten("Tuch", (BANK_X0 + 2350, Y1 - 360, z + 8), (220, 160, 16), M["kunststoff_rot"], fase=6))
    return teile


def laufrad_einfach(mitte, achse, r, M, speichen=24):
    teile = []
    achse = Vector(achse).normalized()
    reifen = [(r + 4 + 18 * (1 + math.cos(TAU * i / 14)), 15 * math.sin(TAU * i / 14)) for i in range(14)]
    teile.append(torus_alt("Reifen", mitte, achse, 0, 0, M["gummi"], um=96, profil=reifen))
    felge = [(r - 18, -10), (r + 4, -12), (r + 6, 0), (r + 4, 12), (r - 18, 10)]
    teile.append(torus_alt("Felge", mitte, achse, 0, 0, M["kunststoff_schwarz"], um=96, profil=felge))
    teile.append(zylinder("Nabe", mitte - achse * 50, mitte + achse * 50, 18, M["alu"], 16))
    rot = achse.to_track_quat("Z", "Y").to_matrix()
    for k in range(speichen):
        w = TAU * k / speichen
        seite = 1 if k % 2 else -1
        a = mitte + rot @ Vector((22 * math.cos(w), 22 * math.sin(w), 30 * seite))
        w2 = w + seite * 0.35
        b = mitte + rot @ Vector(((r - 18) * math.cos(w2), (r - 18) * math.sin(w2), 0))
        teile.append(zylinder("Speiche", a, b, 1.1, M["chrom"], 5, kappen=False))
    return teile


def wand_rechts_regal(M):
    teile = []
    x = X1 - 260
    y0, y1 = -1800.0, 600.0
    boeden = [BODEN + 120, BODEN + 700, BODEN + 1250, BODEN + 1800, BODEN + 2300]
    for yy in (y0, y1):
        for xx in (x - 220, x + 220):
            teile.append(kasten("Steher", (xx, yy, (BODEN + boeden[-1] + 40) / 2), (40, 40, boeden[-1] - BODEN + 40), M["stahl_verz"], fase=2))
    for z in boeden:
        teile.append(kasten("Boden", (x, (y0 + y1) / 2, z), (480, y1 - y0 + 40, 24), M["stahl_verz"], fase=2))
    # Reifen gestapelt und Kartons
    for i in range(5):
        teile.append(torus_alt("Stapelreifen", (x, y0 + 330, boeden[0] + 26 + i * 50), (0, 0, 1), 300, 24, M["gummi"], um=64, quer=10))
    for j, z in enumerate(boeden[1:4]):
        yy = y0 + 80
        while yy < y1 - 150:
            b = ZUFALL.choice([260, 340, 400])
            h = ZUFALL.choice([220, 280, 340, 380])
            h = min(h, 420)
            mat_k = M["karton"] if ZUFALL.random() < 0.75 else M["anthrazit"]
            teile.append(kasten("Regalkiste", (x + 10, yy + b / 2, z + 12 + h / 2), (380, b - 16, h), mat_k, fase=3))
            if mat_k is M["karton"]:
                teile.append(kasten("Etikett", (x - 181, yy + b / 2, z + 12 + h * 0.65), (2, b * 0.45, h * 0.22), M["papier"]))
            yy += b + ZUFALL.choice([0, 20, 80])
    for k in range(3):
        teile.append(torus_alt("Schlauchkarton", (x, y1 - 400 + k * 110, boeden[4] + 60), (0, 1, 0), 120, 14, M["gummi"], um=32, quer=8))
    # Laufräder an Haken an der Rückwand rechts
    for i in range(3):
        mitte = Vector((2950 + i * 420, Y1 - 120 - i * 18, BODEN + 2250))
        teile.append(zylinder("Wandhaken", (mitte.x, Y1, mitte.z + 330), (mitte.x, Y1 - 160, mitte.z + 330), 5, M["anthrazit"], 8))
        teile += laufrad_einfach(mitte, (0.15, 1, 0), 300, M, speichen=24)
    # Pinnwand mit Auftragszetteln
    teile.append(kasten("Pinnwand", (X1 - 12, 1450, BODEN + 1650), (20, 1100, 750), M["tafel"], fase=3))
    for i in range(9):
        yy = 1000 + (i % 3) * 320 + ZUFALL.uniform(-20, 20)
        zz = BODEN + 1400 + (i // 3) * 230 + ZUFALL.uniform(-20, 20)
        teile.append(kasten("Zettel", (X1 - 24, yy, zz), (2, 210, 150), M["papier"]))
    return teile


def montageplatz(M):
    teile = []
    teile.append(kasten("Matte", (620, 140, BODEN + 6), (2300, 1360, 12), M["gummi_matte"], fase=5))
    # Standpumpe und Kompressorschlauch
    px, py = BANK_X1 + 260, Y1 - 300
    teile.append(kasten("Pumpenfuss", (px, py, BODEN + 18), (260, 70, 24), M["schwarz"], fase=6))
    teile.append(zylinder("Pumpenrohr", (px, py, BODEN + 30), (px, py, BODEN + 640), 26, M["petrol"], 20))
    teile.append(zylinder("Manometer", (px, py - 30, BODEN + 120), (px, py - 50, BODEN + 120), 38, M["kunststoff_schwarz"], 20))
    teile.append(zylinder("Pumpengriff", (px - 150, py, BODEN + 690), (px + 150, py, BODEN + 690), 16, M["kunststoff_schwarz"], 14))
    teile.append(zylinder("Kolbenstange", (px, py, BODEN + 640), (px, py, BODEN + 690), 6, M["chrom"], 10))
    # Werkzeugwagen rechts vom Rad
    wx, wy = 2350, 900
    teile.append(kasten("Wagen", (wx, wy, BODEN + 480), (740, 460, 760), M["anthrazit"], fase=8))
    for i in range(5):
        teile.append(kasten("Wagenlade", (wx, wy - 236, BODEN + 180 + i * 140), (700, 14, 120), M["anthrazit"], fase=3))
        teile.append(kasten("Ladengriff", (wx, wy - 248, BODEN + 225 + i * 140), (500, 12, 12), M["alu"], fase=3))
    teile.append(kasten("Wagenplatte", (wx, wy, BODEN + 875), (760, 480, 30), M["gummi"], fase=4))
    for (dx, dy) in ((-320, -180), (320, -180), (-320, 180), (320, 180)):
        teile.append(zylinder("Rolle", (wx + dx - 20, wy + dy, BODEN + 50), (wx + dx + 20, wy + dy, BODEN + 50), 50, M["gummi"], 16))
    for i in range(4):
        teile.append(zylinder("Dose", (wx - 250 + i * 70, wy - 80, BODEN + 890), (wx - 250 + i * 70, wy - 80, BODEN + 1090 - i * 25), 28, [M["petrol"], M["kunststoff_rot"], M["kunststoff_blau"], M["kunststoff_gelb"]][i], 18))
    return teile




def ausstattung(M):
    """Was jede echte Werkstatt hat: Heizkörper, Feuerlöscher, Steckdosen, Uhr, Kabeltrommel, Mülleimer."""
    teile = []
    # Heizkörper unter dem Fensterband
    for i, y0 in enumerate((-3300.0, -1300.0, 700.0)):
        for k in range(22):
            y = y0 + k * 42
            teile.append(kasten("Rippe", (X0 + 70, y, BODEN + 520), (60, 30, 560), M["putz"], fase=8, segmente=2))
        teile.append(zylinder("Heizrohr", (X0 + 70, y0 - 40, BODEN + 210), (X0 + 70, y0 + 22 * 42 + 20, BODEN + 210), 11, M["putz"], 12))
        teile.append(zylinder("Ventil", (X0 + 70, y0 - 60, BODEN + 760), (X0 + 70, y0 - 60, BODEN + 840), 18, M["putz"], 16))
    # Feuerlöscher mit Schild neben dem Tor
    fx, fy = X1 - 160, -4000.0
    teile.append(zylinder("Loescher", (fx, fy, BODEN + 520), (fx, fy, BODEN + 1080), 80, M["kunststoff_rot"], 32))
    teile.append(zylinder("Loescherkopf", (fx, fy, BODEN + 1080), (fx, fy, BODEN + 1150), 28, M["chrom"], 16))
    teile.append(kasten("Loeschergriff", (fx - 20, fy, BODEN + 1160), (90, 14, 10), M["schwarz"], fase=3))
    teile.append(zylinder("Schlauch", (fx + 10, fy - 40, BODEN + 1100), (fx + 30, fy - 85, BODEN + 700), 9, M["schwarz"], 10))
    teile.append(kasten("Halter", (X1 - 30, fy, BODEN + 900), (40, 120, 80), M["anthrazit"], fase=3))
    teile.append(kasten("Brandschild", (X1 - 6, fy, BODEN + 1500), (6, 200, 200), M["kunststoff_rot"], fase=2))
    teile.append(kasten("Brandschild_weiss", (X1 - 10, fy, BODEN + 1500), (2, 120, 120), M["papier"]))
    # Steckdosenleiste über der Werkbank, Aufputzdosen an der rechten Wand
    for i in range(6):
        teile.append(kasten("Dose", (BANK_X0 + 300 + i * 90, Y1 - 30, BANK_HOEHE + 70), (72, 40, 72), M["papier"], fase=6))
        teile.append(kasten("Dosenloch", (BANK_X0 + 300 + i * 90, Y1 - 51, BANK_HOEHE + 70), (36, 4, 36), M["kunststoff_schwarz"], fase=3))
    for y in (-2200.0, -900.0):
        teile.append(kasten("CEE", (X1 - 40, y, BODEN + 1350), (80, 110, 150), M["kunststoff_blau"], fase=8))
    teile.append(kasten("Kabelkanal", (X1 - 15, -1000, BODEN + 1250), (30, 4800, 40), M["papier"], fase=2))
    # Wanduhr über dem Fensterband
    teile.append(zylinder("Uhr", (X0 + 2, 300, STURZ + 120), (X0 + 30, 300, STURZ + 120), 160, M["papier"], 48))
    teile.append(zylinder("Uhrrand", (X0 + 2, 300, STURZ + 120), (X0 + 34, 300, STURZ + 120), 168, M["schwarz"], 48, kappen=False))
    for k in range(12):
        w = math.tau * k / 12
        teile.append(kasten("Strich", (X0 + 31, 300 + 140 * math.cos(w), STURZ + 120 + 140 * math.sin(w)), (2, 8 if k % 3 else 14, 22 if k % 3 else 30), M["schwarz"]))
    teile.append(kasten("Zeiger_h", (X0 + 33, 300 + 40, STURZ + 120 + 30), (2, 10, 110), M["schwarz"]))
    teile.append(kasten("Zeiger_m", (X0 + 34, 300 - 50, STURZ + 120 + 10), (2, 140, 8), M["schwarz"]))
    # Kabeltrommel und Mülleimer bei der Werkbank
    teile.append(torus_alt("Kabel", (X0 + 420, Y1 - 300, BODEN + 170), (1, 0, 0), 120, 34, M["kunststoff_schwarz"], 48, 10))
    teile.append(zylinder("Trommelscheibe", (X0 + 380, Y1 - 300, BODEN + 170), (X0 + 384, Y1 - 300, BODEN + 170), 160, M["anthrazit"], 40))
    teile.append(zylinder("Trommelscheibe", (X0 + 456, Y1 - 300, BODEN + 170), (X0 + 460, Y1 - 300, BODEN + 170), 160, M["anthrazit"], 40))
    teile.append(zylinder("Muelleimer", (BANK_X1 + 300, Y1 - 700, BODEN), (BANK_X1 + 300, Y1 - 700, BODEN + 640), 210, M["anthrazit"], 32, r2=200))
    teile.append(zylinder("Deckel", (BANK_X1 + 300, Y1 - 700, BODEN + 640), (BANK_X1 + 300, Y1 - 700, BODEN + 660), 214, M["kunststoff_schwarz"], 32))
    # Papierrolle an der Werkzeugwand
    teile.append(zylinder("Papierrolle", (BANK_X1 - 160, Y1 - 120, PLATTE_Z0 + 120), (BANK_X1 - 160 + 260, Y1 - 120, PLATTE_Z0 + 120), 70, M["papier"], 32))
    teile.append(zylinder("Rollenhalter", (BANK_X1 - 180, Y1 - 120, PLATTE_Z0 + 120), (BANK_X1 + 120, Y1 - 120, PLATTE_Z0 + 120), 8, M["chrom"], 12))
    # Laptop mit Diagnose-Software auf der Werkbank
    lx, ly = BANK_X0 + 1500, Y1 - 360
    teile.append(kasten("Laptop", (lx, ly, BANK_HOEHE + 9), (340, 240, 16), M["anthrazit"], fase=4))
    deckel = kasten("Laptopdeckel", (lx, ly + 110, BANK_HOEHE + 120), (340, 10, 230), M["anthrazit"], fase=4)
    deckel.data.transform(Matrix.Translation((lx, ly + 110, BANK_HOEHE + 10)) @ Matrix.Rotation(math.radians(-14), 4, "X") @ Matrix.Translation((-lx, -(ly + 110), -(BANK_HOEHE + 10))))
    teile.append(deckel)
    schirm = kasten("Laptopschirm", (lx, ly + 104, BANK_HOEHE + 122), (310, 2, 190), "Laptop_schirm")
    schirm.data.transform(Matrix.Translation((lx, ly + 110, BANK_HOEHE + 10)) @ Matrix.Rotation(math.radians(-14), 4, "X") @ Matrix.Translation((-lx, -(ly + 110), -(BANK_HOEHE + 10))))
    teile.append(schirm)
    return teile


def welt(s):
    w = bpy.data.worlds.new("Himmel")
    s.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.75, 0.86, 1.0, 1)
    bg.inputs["Strength"].default_value = 1.6
    sonne = bpy.data.objects.new("Sonne", bpy.data.lights.new("Sonne", "SUN"))
    sonne.data.energy = 3.2
    sonne.data.color = (1.0, 0.93, 0.83)
    sonne.data.angle = math.radians(1.2)
    sonne.rotation_euler = (math.radians(58), 0, math.radians(-112))
    s.collection.objects.link(sonne)
    return sonne


def aussen(M):
    """Was man durchs Fenster sieht: Hof, gegenüberliegende Halle, Bäume. Überbelichtet wie auf einem Foto."""
    teile = []
    teile.append(netz("Hof", [(X0 - 30000, Y0 - 20000, BODEN - 300), (X0 - 300, Y0 - 20000, BODEN - 300), (X0 - 300, Y1 + 20000, BODEN - 300), (X0 - 30000, Y1 + 20000, BODEN - 300)],
                      [(0, 1, 2, 3)], "Asphalt"))
    teile.append(kasten("Halle", (X0 - 16000, -1000, BODEN + 3500), (3000, 30000, 8000), "Fassade"))
    for i in range(14):
        y = -9000 + i * 1400
        teile.append(kasten("Hallenfenster", (X0 - 14480, y, BODEN + 3600), (40, 900, 1800), "Fenster_dunkel"))
    return verbinden("aussen", teile)


def licht(s):
    """Portal im Fenster (bündelt das Himmelslicht) und eine große, unsichtbare Softbox wie beim Produktfoto."""
    portal = bpy.data.lights.new("Portal", "AREA")
    portal.shape = "RECTANGLE"
    portal.size = FENSTER_Y1 - FENSTER_Y0
    portal.size_y = STURZ - BRUESTUNG
    portal.cycles.is_portal = True
    o = bpy.data.objects.new("Portal", portal)
    o.location = (X0 - 150, (FENSTER_Y0 + FENSTER_Y1) / 2, (BRUESTUNG + STURZ) / 2)
    o.rotation_euler = (0, math.radians(90), 0)
    s.collection.objects.link(o)
    box = bpy.data.lights.new("Softbox", "AREA")
    box.shape = "RECTANGLE"
    box.size = 2600
    box.size_y = 1600
    box.energy = 3.2e8
    box.color = (1.0, 0.97, 0.93)
    o2 = bpy.data.objects.new("Softbox", box)
    o2.location = (1500, -2600, 2900)
    o2.rotation_euler = (Vector((640, 0, 450)) - Vector(o2.location)).to_track_quat("-Z", "Y").to_euler()
    o2.visible_camera = False
    o2.visible_glossy = True
    s.collection.objects.link(o2)
    return o, o2


def bauen(s):
    """Baut die Werkstatt in die Szene; gibt die Teile als Wörterbuch zurück."""
    teile = raum(M)
    teile["aussen"] = aussen(M)
    licht(s)
    teile["leuchten"] = leuchten(M)
    teile["moebel"] = verbinden("moebel", werkbank(M) + werkzeugwand(M) + auf_der_bank(M) + wand_rechts_regal(M) + montageplatz(M) + ausstattung(M))
    welt(s)
    return teile

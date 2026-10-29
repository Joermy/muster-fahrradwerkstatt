"""E-MTB von 2026 (Größe L, 160/150 mm, 29"), erfunden, ohne echte Marken.

x vom Hinterrad zum Vorderrad, y quer (Antriebsseite negativ), z nach oben, Millimeter.
Das Rad hängt im Montageständer; der Boden liegt bei z = BODEN.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from .werkzeug import (TAU, auswerten, boolesch, chaikin, drehen, drehpunkt, drehteil, drehteil_achse, fasen, glaetten, kasten, kopieren, kreis, netz,
                       platte, rohr, rundrechteck, torus, umriss, verbinden, verschieben, voxel, zusatz, zylinder)

# ---------------------------------------------------------------- Geometrie

R_FELGE = 311.0
R_RAD = 374.0
BODEN = -274.0
HINTEN = Vector((0.0, 0.0, R_RAD))
VORN = Vector((1270.0, 0.0, R_RAD))
TRETLAGER = Vector((447.0, 0.0, R_RAD - 28.0))

LENKWINKEL = math.radians(64.5)
U = Vector((-math.cos(LENKWINKEL), 0, math.sin(LENKWINKEL)))
N = Vector((math.sin(LENKWINKEL), 0, math.cos(LENKWINKEL)))
GABEL_VERSATZ = 44.0
EINBAUHOEHE = 580.0
ACHSE_AUF_LENKACHSE = VORN - N * GABEL_VERSATZ
KRONE = ACHSE_AUF_LENKACHSE + U * EINBAUHOEHE
STEUERROHR_UNTEN = KRONE + U * 14
STEUERROHR_OBEN = STEUERROHR_UNTEN + U * 115
VORBAU = STEUERROHR_OBEN + U * 40
LENKERMITTE = VORBAU + N * 45 + U * 4

SITZWINKEL = math.radians(75.5)
S = Vector((-math.cos(SITZWINKEL), 0, math.sin(SITZWINKEL)))
SITZROHR_OBEN = TRETLAGER + S * 455
HAUPTLAGER = TRETLAGER + Vector((-40, 0, 88))
HORST = HINTEN + Vector((52, 0, -18))
WIPPE = Vector((390.0, 0.0, 625.0))
STREBE_OBEN = WIPPE + Vector((-62, 0, 38))
DAEMPFER_OBEN = WIPPE + Vector((58, 0, 32))
DAEMPFER_UNTEN = Vector((660.0, 0.0, 606.0))
UNTERROHR_A = STEUERROHR_UNTEN + U * 26 - N * 4
UNTERROHR_B = TRETLAGER + Vector((92, 0, 74))
OBERROHR_A = STEUERROHR_OBEN - U * 22
OBERROHR_B = TRETLAGER + S * 318

TEILUNG = 12.7
KETTENBLATT_Y = -52.0
KETTENBLATT_ZAEHNE = 34
KASSETTE = [10, 12, 14, 16, 18, 21, 24, 28, 32, 38, 44, 52]
KASSETTE_Y_GROSS = -30.5
KASSETTE_ABSTAND = 3.9
SCHALTROLLE_ZAEHNE = 12
KAEFIG = 102.0
KURBEL = 165.0
ROTOR = {"v": 110.0, "h": 101.5}
ROTOR_Y = {"v": 51.0, "h": 56.0}
GABEL_ABSTAND = 63.0


def teilkreis(zaehne):
    return TEILUNG / (2 * math.sin(math.pi / zaehne))


def zahnkranz_umriss(zaehne, versatz=0.0, proben=14, breit_schmal=False):
    rp = teilkreis(zaehne)
    rolle = 4.05
    r_kopf = (TEILUNG * (0.6 + 1 / math.tan(math.pi / zaehne))) / 2 - 0.4
    schritt = TAU / zaehne
    aus = []
    for k in range(zaehne):
        spitze = r_kopf - (0.9 if breit_schmal and k % 2 else 0.0)
        for j in range(proben):
            d = (j / proben - 0.5) * schritt
            bog = rp * abs(d)
            if bog < rolle * 0.98:
                r = rp - math.sqrt(rolle * rolle - bog * bog)
            else:
                f = min(1.0, (abs(d) - rolle / rp) / (schritt / 2 - rolle / rp))
                r = rp + (spitze - rp) * (1 - (1 - f) ** 1.6)
                if f > 0.9:
                    r = spitze - 0.25
            w = versatz + k * schritt + d
            aus.append((r * math.cos(w), r * math.sin(w)))
    return aus


def ebene_seite(punkte_xz, dicke, y, mat, fase=1.0):
    """Platte in der Seitenebene (x/z), Dicke in y ab `y`."""
    m = Matrix(((1, 0, 0, 0), (0, 0, 1, y), (0, 1, 0, 0), (0, 0, 0, 1)))
    return platte("Platte", punkte_xz, dicke, mat, fase, m)


def kapsel_umriss(a, b, ra, rb, n=14):
    """2D-Umriss zweier Kreise mit Tangenten (Langloch/Lasche) in x/z."""
    a, b = Vector((a[0], a[1])), Vector((b[0], b[1]))
    d = b - a
    w = math.atan2(d.y, d.x)
    laenge = d.length
    k = max(-1.0, min(1.0, (ra - rb) / laenge))
    phi = math.acos(k)
    aus = []
    for i in range(n + 1):
        t = w + phi + (TAU - 2 * phi) * i / n
        aus.append((a.x + ra * math.cos(t), a.y + ra * math.sin(t)))
    for i in range(n + 1):
        t = w - phi + 2 * phi * i / n
        aus.append((b.x + rb * math.cos(t), b.y + rb * math.sin(t)))
    return aus


# ---------------------------------------------------------------- Laufräder


def reifenprofil():
    """Querschnitt der Karkasse (r, y) vom Wulst links zum Wulst rechts."""
    rc, a, b = 340.5, 30.5, 31.5
    t0 = math.asin((R_FELGE + 1.5 - rc) / a)
    aus = [(R_FELGE + 0.5, -15.4)]
    for i in range(41):
        t = t0 + (math.pi - 2 * t0) * i / 40
        aus.append((rc + a * math.sin(t), -b * math.cos(t)))
    aus.append((R_FELGE + 0.5, 15.4))
    return aus, (rc, a, b)


def karkasse_punkt(y, w, ell):
    rc, a, b = ell
    t = math.acos(max(-1.0, min(1.0, -y / b)))
    r = rc + a * math.sin(t)
    dr = a * math.cos(t)
    dy = b * math.sin(t)
    radial = Vector((math.cos(w), 0, math.sin(w)))
    seitlich = Vector((0, 1, 0))
    p = radial * r + seitlich * (-b * math.cos(t))
    quer = (radial * dr + seitlich * dy).normalized()
    normal = (radial * dy - seitlich * dr).normalized()
    tangente = Vector((-math.sin(w), 0, math.cos(w)))
    return p, normal, quer, tangente


def stollen(bm, ell, w, y, laenge, breite, hoehe, drehung=0.0, rampe=0.0, verjuengung=0.8):
    """Ein Profilstollen: Quader auf der Karkasse, oben schmaler, optional mit Rampe."""
    p, nrm, quer, tang = karkasse_punkt(y, w, ell)
    c, s = math.cos(drehung), math.sin(drehung)
    t2 = tang * c + quer * s
    q2 = quer * c - tang * s
    ecken = []
    for h, f in ((-1.2, 1.0), (hoehe, verjuengung)):
        for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            hh = h
            if h > 0 and rampe and u < 0:
                hh = h - rampe
            ecken.append(p + t2 * (u * laenge / 2 * f) + q2 * (v * breite / 2 * f) + nrm * hh)
    vs = [bm.verts.new(e) for e in ecken]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])


def reifen(name):
    profil, ell = reifenprofil()
    karkasse = drehteil(name + "_karkasse", profil, "Reifen", 240, geschlossen=False, winkel=70)
    bm = bmesh.new()
    einheiten = 36
    for k in range(einheiten):
        w0 = TAU * k / einheiten
        dw = TAU / einheiten
        # Mitte: abwechselnd Paar mit Rampen und breiter Einzelstollen
        if k % 2 == 0:
            for y in (-6.2, 6.2):
                stollen(bm, ell, w0, y, 12.5, 9.5, 4.0, rampe=1.0)
        else:
            stollen(bm, ell, w0, 0.0, 10.5, 19, 4.0, rampe=0.9)
        stollen(bm, ell, w0 + dw * 0.5, 0.0, 9, 14, 3.8, drehung=0.0)
        # Übergang, schräg gestellt
        for y in (-16.0, 16.0):
            stollen(bm, ell, w0 + dw * (0.25 if y < 0 else 0.75), y, 11, 8.5, 4.1, drehung=0.35 * (1 if y > 0 else -1))
        # Schulter: lang und kurz im Wechsel
        for y in (-25.0, 25.0):
            lang = (k % 2 == 0) == (y > 0)
            stollen(bm, ell, w0 + dw * (0.0 if y < 0 else 0.5), y, 17 if lang else 12, 10, 4.5, verjuengung=0.86)
            stollen(bm, ell, w0 + dw * (0.5 if y < 0 else 0.0), y * 1.03, 9, 9, 4.2, verjuengung=0.86)
    me = bpy.data.meshes.new(name + "_stollen")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name + "_stollen", me)
    bpy.context.scene.collection.objects.link(obj)
    from .werkzeug import material_von
    me.materials.append(material_von("Reifen"))
    obj = fasen(obj, 0.7, 2, 40)
    glaetten(obj, 50)
    return verbinden(name, [karkasse, obj])


def felge(name):
    profil = [(287, -10.5), (289, -15.8), (300, -17.6), (309, -17.9), (313.5, -17.4), (315.2, -16.4), (314.8, -15.2), (312.2, -15.0),
              (311.2, -13.6), (311.0, -8.5), (307.0, -6.0), (307.0, 6.0), (311.0, 8.5), (311.2, 13.6), (312.2, 15.0), (314.8, 15.2),
              (315.2, 16.4), (313.5, 17.4), (309, 17.9), (300, 17.6), (289, 15.8), (287, 10.5)]
    f = drehteil(name, profil, "Felge", 192, winkel=30)
    ventil = zylinder("Ventil", Vector((0, 0, 290)), Vector((0, 0, 318)), 3.2, "Alu_roh", 12)
    kappe = zylinder("Ventilkappe", Vector((0, 0, 287)), Vector((0, 0, 268)), 4.2, "Kunststoff", 16)
    mutter = zylinder("Ventilmutter", Vector((0, 0, 287)), Vector((0, 0, 281)), 6.0, "Alu_roh", 6)
    return verbinden(name, [f, ventil, kappe, mutter])


def nabe(name, vorn):
    if vorn:
        profil = [(8, -60), (19, -60), (19, -50), (24, -46), (30, -40), (30, -36.5), (24, -34), (19, -26), (17, 0), (19, 26), (24, 34),
                  (30, 36.5), (30, 40), (24, 46), (19, 50), (19, 60), (8, 60)]
        flansche = (38.0, -38.0)
    else:
        profil = [(8, -79), (20, -79), (20, -72), (22, -66), (30, -26), (30, -22.5), (24, -20), (19, -12), (18, 0), (19, 22), (24, 32),
                  (30, 35.5), (30, 39), (24, 44), (20, 64), (20, 79), (8, 79)]
        flansche = (-24.0, 37.0)
    teile = [drehteil(name, profil, "Nabe", 72)]
    teile.append(drehteil("Achskappe", [(0, 0), (12, 0), (12, 4), (0, 4)], "Alu_schwarz_glatt", 32, mitte=(0, 61 if vorn else 80, 0)))
    teile.append(drehteil("Achskappe", [(0, 0), (12, 0), (12, -4), (0, -4)], "Alu_schwarz_glatt", 32, mitte=(0, -61 if vorn else -80, 0)))
    return verbinden(name, teile), flansche


def speichen(name, flansche, r_loch=26.0, r_felge=297.0, anzahl=32, kreuzung=3):
    teile = []
    nippel = []
    je = anzahl // 2
    info = []
    for seite_i, y_fl in enumerate(flansche):
        y_rim = 2.4 if y_fl > 0 else -2.4
        for k in range(je):
            a_h = TAU * k / je + (TAU / anzahl if seite_i else 0)
            richtung = 1 if k % 2 == 0 else -1
            a_r = a_h + richtung * kreuzung * TAU / je
            hub = Vector((r_loch * math.cos(a_h), y_fl, r_loch * math.sin(a_h)))
            rim = Vector((r_felge * math.cos(a_r), y_rim, r_felge * math.sin(a_r)))
            d = (rim - hub).normalized()
            teile.append(zylinder("Speiche", hub + d * 3, rim, 1.0, "Speiche", 8, kappen=False))
            kopf_richtung = Vector((0, 1 if y_fl > 0 else -1, 0))
            teile.append(zylinder("Speichenkopf", hub + d * 3, hub + kopf_richtung * 3.5, 1.0, "Speiche", 8))
            teile.append(drehteil_achse("Kopf", [(0, 0), (2.1, 0), (2.1, 1.4), (0, 1.4)], "Speiche", hub + kopf_richtung * 3.5, kopf_richtung, 12))
            nippel.append(zylinder("Nippel", rim - d * 11, rim + d * 3, 2.0, "Nippel", 8))
            info.append([round(a_r, 5), seite_i])
    obj = verbinden(name, teile + nippel)
    return zusatz(obj, r_felge=r_felge, r_loch=r_loch)


def bremsscheibe(name, r_aussen, y):
    r_innen = r_aussen - 18.0
    aussen = []
    # Außenkante mit flachen Wellen wie bei Scheiben neuerer Bauart
    for i in range(240):
        w = TAU * i / 240
        aussen.append(((r_aussen - 0.6 * (1 - math.cos(w * 24))) * math.cos(w), (r_aussen - 0.6 * (1 - math.cos(w * 24))) * math.sin(w)))
    loecher = []
    for k in range(24):
        w = TAU * k / 24
        for j, (rr, rl) in enumerate(((r_innen + 5.5, 2.3), (r_innen + 11.5, 2.3))):
            ww = w + j * TAU / 48
            loecher.append(kreis(rl, 12, mitte=(rr * math.cos(ww), rr * math.sin(ww))))
    fenster = []
    arme = 6
    for k in range(arme):
        w0 = TAU * k / arme
        pk = []
        for j in range(12):
            t = j / 11
            pk.append(((r_innen - 1.5) * math.cos(w0 + 0.13 + t * 0.78), (r_innen - 1.5) * math.sin(w0 + 0.13 + t * 0.78)))
        for j in range(12):
            t = 1 - j / 11
            rr = 36 + 10 * t
            pk.append((rr * math.cos(w0 + 0.48 + t * 0.4), rr * math.sin(w0 + 0.48 + t * 0.4)))
        fenster.append(pk)
    scheibe = umriss(name, [aussen, kreis(29, 48)] + fenster + loecher, 2.0, "Bremsscheibe", fase=0.25, aufloesung=0, y=0)
    verschieben(scheibe, (0, y, 0))
    aufnahme = drehteil("Centerlock", [(19, y - 9), (34, y - 9), (34, y - 1.0), (19, y - 1.0)], "Alu_schwarz_glatt", 48)
    ring = drehteil("Verschlussring", [(16, y + 1), (27, y + 1), (27, y + 5.5), (16, y + 5.5)], "Alu_schwarz_glatt", 48)
    obj = verbinden(name, [scheibe, aufnahme, ring])
    return zusatz(obj, r_aussen=r_aussen, hitze=0.0, anlauf=0.0)


def kassette(name):
    teile = []
    for i, z in enumerate(KASSETTE[::-1]):
        y = KASSETTE_Y_GROSS - i * KASSETTE_ABSTAND
        rp = teilkreis(z)
        loecher = []
        r_innen = 17.5 if z < 16 else 21.0
        if z >= 24:
            n = 5 if z < 38 else 6
            for k in range(n):
                w0 = TAU * k / n
                pk = []
                ra, ri = rp - 10.5, max(r_innen + 8, rp * 0.45)
                for j in range(8):
                    t = j / 7
                    pk.append((ra * math.cos(w0 + 0.16 + t * (TAU / n - 0.32)), ra * math.sin(w0 + 0.16 + t * (TAU / n - 0.32))))
                for j in range(8):
                    t = 1 - j / 7
                    pk.append((ri * math.cos(w0 + 0.3 + t * (TAU / n - 0.6)), ri * math.sin(w0 + 0.3 + t * (TAU / n - 0.6))))
                loecher.append(pk)
        mat = "Kassette_dunkel" if z >= 38 else "Kassette"
        teile.append(umriss(f"Ritzel{z}", [zahnkranz_umriss(z, versatz=0.13 * i, proben=10), kreis(r_innen, 32)] + loecher, 1.7, mat, fase=0.25, aufloesung=0, y=y))
    y_klein = KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND
    teile.append(drehteil("Kassettenkoerper", [(16, KASSETTE_Y_GROSS + 2), (22, KASSETTE_Y_GROSS + 2), (22, y_klein - 2), (16, y_klein - 2)], "Stahl_dunkel", 48))
    teile.append(drehteil("Verschlussring", [(10, y_klein - 1), (17, y_klein - 1), (17, y_klein - 6), (10, y_klein - 6)], "Alu_schwarz_glatt", 48))
    return verbinden(name, teile)


def laufrad(vorn):
    seite = "v" if vorn else "h"
    mitte = VORN if vorn else HINTEN
    teile = {}
    teile["reifen"] = reifen(f"reifen_{seite}")
    teile["felge"] = felge(f"felge_{seite}")
    n, flansche = nabe(f"nabe_{seite}", vorn)
    teile["nabe"] = n
    teile["speichen"] = speichen(f"speichen_{seite}", flansche)
    teile["bremsscheibe"] = bremsscheibe(f"bremsscheibe_{seite}", ROTOR[seite], ROTOR_Y[seite])
    if not vorn:
        teile["kassette"] = kassette("kassette")
    aus = {}
    for name, obj in teile.items():
        verschieben(obj, mitte)
        drehpunkt(obj, mitte)
        aus[obj.name] = obj
    return aus


# ---------------------------------------------------------------- Rahmen


def rahmen_vorn():
    """Hauptrahmen als ein verschmolzener Carbon-Körper mit Akkuschacht."""
    teile = []
    # Steuerrohr, unten aufgeweitet für den 1,5"-Steuersatz
    teile.append(rohr("Steuerrohr", [STEUERROHR_UNTEN - U * 6, STEUERROHR_OBEN + U * 2],
                      lambda t: (31 - 4.5 * t + 3.5 * (1 - t) ** 6, 31 - 4.5 * t + 3.5 * (1 - t) ** 6, 2.0), "Lack", um=48))
    mitte_u = UNTERROHR_A.lerp(UNTERROHR_B, 0.5) + Vector((0, 0, -8))
    teile.append(rohr("Unterrohr", [UNTERROHR_A, UNTERROHR_A.lerp(mitte_u, 0.5) + Vector((0, 0, -3)), mitte_u, UNTERROHR_B],
                      lambda t: (45 - 4 * t, 39 - 3 * t + 3 * math.sin(math.pi * t), 2.7), "Lack", um=56, seite=Vector((0, 1, 0))))
    mitte_o = OBERROHR_A.lerp(OBERROHR_B, 0.5) + Vector((0, 0, 6))
    teile.append(rohr("Oberrohr", [OBERROHR_A, mitte_o, OBERROHR_B],
                      lambda t: (21 - 3 * t + 5 * (1 - t) ** 4, 25 - 6 * t, 2.5), "Lack", um=44))
    teile.append(rohr("Sitzrohr", [TRETLAGER + S * 40, TRETLAGER + S * 250, SITZROHR_OBEN],
                      lambda t: (23 + 5 * (1 - t) ** 3, 21.5 + 6 * (1 - t) ** 3, 2.2), "Lack", um=44))
    # Motoraufnahme: Wangen, die aus dem Unterrohr wachsen und den Motor oben umschließen
    wange = [(-70, 52), (-52, 92), (-14, 114), (44, 120), (104, 112), (152, 92), (174, 62), (160, 40), (110, 44), (40, 50), (-20, 46)]
    for y in (-54.0, 46.0):
        teile.append(ebene_seite(chaikin([(TRETLAGER.x + x, TRETLAGER.z + z) for x, z in wange], 3), 8.0, y, "Lack", 2.5))
    teile.append(rohr("Motordach", [TRETLAGER + Vector((-40, 0, 104)), TRETLAGER + Vector((60, 0, 118)), UNTERROHR_B + (UNTERROHR_A - UNTERROHR_B).normalized() * 40],
                      lambda t: (12, 48, 2.6), "Lack", um=40))
    # Hauptlager-, Wippen- und Dämpferaufnahmen
    teile.append(zylinder("Hauptlagerauge", HAUPTLAGER + Vector((0, -50, 0)), HAUPTLAGER + Vector((0, 50, 0)), 17, "Lack", 32))
    teile.append(rohr("Wippenauge", [WIPPE + Vector((0, -24, 0)), WIPPE + Vector((0, 24, 0))], lambda t: (15, 15, 2), "Lack", um=28, seite=Vector((1, 0, 0))))
    for y in (-15.5, 15.5):
        ohr = kapsel_umriss((DAEMPFER_UNTEN.x, DAEMPFER_UNTEN.z), (DAEMPFER_UNTEN.x + 34, DAEMPFER_UNTEN.z - 26), 14, 18)
        teile.append(ebene_seite(ohr, 7.0, y - 3.5, "Lack", 1.2))
    # Kabeleinlass hinten am Unterrohr
    roh = verbinden("rahmen_roh", teile)
    rahmen = voxel(roh, 1.6, glaettung=6, faktor=0.6)
    # Steuerrohr innen frei, Sitzrohr für die Stütze
    rahmen = boolesch(rahmen, zylinder("Bohrung", STEUERROHR_UNTEN - U * 20, STEUERROHR_OBEN + U * 20, 20.5, "Lack", 32))
    rahmen = boolesch(rahmen, zylinder("Sitzbohrung", SITZROHR_OBEN - S * 120, SITZROHR_OBEN + S * 20, 15.9, "Lack", 32))
    rahmen = boolesch(rahmen, zylinder("Tretlager", TRETLAGER + Vector((0, -70, 0)), TRETLAGER + Vector((0, 70, 0)), 20, "Lack", 32))
    luecke = kasten("Daempferspalt", DAEMPFER_UNTEN + Vector((10, 0, -6)), (70, 23, 60), "Lack")
    rahmen = boolesch(rahmen, luecke)
    rahmen.name = "rahmen"
    rahmen.data.materials.clear()
    from .werkzeug import material_von
    rahmen.data.materials.append(material_von("Lack"))
    return rahmen


def akkuschacht():
    """Volumen des Akkus unter dem Unterrohr (für Ausschnitt und Akku selbst)."""
    a = UNTERROHR_A.lerp(UNTERROHR_B, 0.13)
    b = UNTERROHR_A.lerp(UNTERROHR_B, 0.86)
    d = (b - a).normalized()
    quer = Vector((0, 1, 0)).cross(d).normalized()
    if quer.z > 0:
        quer = -quer
    return a, b, d, quer


def akku_und_schacht(rahmen):
    """Schneidet die untere Hälfte des Unterrohrs als Akkudeckel heraus und lässt einen Schacht zurück."""
    a, b, d, quer = akkuschacht()
    aussen = rohr("Schacht", [a + quer * 50, b + quer * 50], lambda t: (46, 46, 4.0), "Lack", um=40, seite=Vector((0, 1, 0)))
    innen = rohr("Schacht_innen", [a + quer * 2 + d * 6, b + quer * 2 - d * 6], lambda t: (26, 30, 3.0), "Lack", um=40, seite=Vector((0, 1, 0)))
    deckel = kopieren(rahmen, "akku")
    deckel = boolesch(deckel, kopieren(aussen, "Schnitt"), "INTERSECT")
    luft = kopieren(aussen, "Fuge")
    mod = luft.modifiers.new("Fuge", "DISPLACE")
    mod.strength = 0.5
    luft = auswerten(luft)
    rahmen = boolesch(rahmen, luft)
    rahmen = boolesch(rahmen, kopieren(innen, "Hohlraum"))
    paket = rohr("Zellen", [a + quer * 4 + d * 10, b + quer * 4 - d * 10], lambda t: (24, 28, 3.0), "Akku_innen", um=32, seite=Vector((0, 1, 0)))
    stecker = kasten("Akkustecker", a + quer * 2 + d * 8, (16, 34, 26), "Kunststoff", fase=3)
    schloss = zylinder("Schloss", b + quer * 30 - d * 30 + Vector((0, 36, 0)), b + quer * 30 - d * 30 + Vector((0, 41.5, 0)), 6.5, "Alu_roh", 24)
    leds = []
    for i in range(5):
        p = b - d * 14 + quer * (16 + i * 7)
        leds.append(zylinder("LED", p - d * 0.5, p + d * 1.5, 1.8, "LED", 12))
    akku = verbinden("akku", [deckel, paket, stecker, schloss] + leds)
    for o in (aussen, innen):
        bpy.data.objects.remove(o, do_unlink=True)
    zusatz(akku, richtung=list(d), quer=list(quer), led=0.0)
    drehpunkt(akku, (a + b) / 2)
    return rahmen, akku


def hinterbau():
    teile = []
    for s in (1, -1):
        y_vorn = 34.0 * s
        y_hinten = 70.0 * s
        hl = HAUPTLAGER + Vector((0, y_vorn, 0))
        hp = HORST + Vector((0, y_hinten, 0))
        mitte = hl.lerp(hp, 0.5) + Vector((0, 12.0 * s, -18 if s < 0 else -8))
        teile.append(rohr(f"Kettenstrebe{s}", [hl, hl.lerp(mitte, 0.45) + Vector((0, 4 * s, -6)), mitte, hp],
                          lambda t: (18 - 6 * t, 10 - 2 * t, 2.5), "Lack", um=32))
        teile.append(zylinder("Hauptlagernabe", hl + Vector((0, -9 * s, 0)), hl + Vector((0, 9 * s, 0)), 16, "Lack", 28))
        ausfall = kapsel_umriss((HINTEN.x - 4, HINTEN.z), (HORST.x, HORST.z), 21, 15)
        teile.append(ebene_seite(ausfall, 10.0, y_hinten - 5.0, "Lack", 1.5))
        so = STREBE_OBEN + Vector((0, 27.0 * s, 0))
        unten = HINTEN + Vector((10, 71.0 * s, 26))
        teile.append(rohr(f"Sitzstrebe{s}", [unten, unten.lerp(so, 0.5) + Vector((10, 4 * s, 0)), so],
                          lambda t: (13 - 2 * t, 9.5 - 1.5 * t, 2.4), "Lack", um=28))
    # Strebenbrücke und Dämpferbock der Sitzstreben
    br_a = HINTEN.lerp(STREBE_OBEN, 0.68) + Vector((12, -30, 0))
    br_b = HINTEN.lerp(STREBE_OBEN, 0.68) + Vector((12, 30, 0))
    teile.append(rohr("Bruecke", [br_a, (br_a + br_b) / 2 + Vector((6, 0, 5)), br_b], lambda t: (11, 9, 2.4), "Lack", um=24, seite=Vector((1, 0, 0))))
    jk_a = HAUPTLAGER.lerp(HORST, 0.32) + Vector((0, -36, -2))
    jk_b = HAUPTLAGER.lerp(HORST, 0.32) + Vector((0, 36, 4))
    teile.append(rohr("Joch", [jk_a, jk_b], lambda t: (14, 9, 2.4), "Lack", um=24, seite=Vector((1, 0, 0))))
    # Bremsaufnahme (Post Mount) an der rechten Sitzstrebe
    pm = HINTEN + Vector((70, 72, 52))
    teile.append(kasten("PostMount", pm, (58, 12, 22), "Lack", fase=4))
    drehen(teile[-1], math.radians(-24), "Y", pm)
    roh = verbinden("hinterbau_roh", teile)
    hb = voxel(roh, 1.4, glaettung=5, faktor=0.55)
    for p_ in (HINTEN,):
        hb = boolesch(hb, zylinder("Achsloch", p_ + Vector((0, -90, 0)), p_ + Vector((0, 90, 0)), 6.5, "Lack", 24))
    hb.name = "hinterbau"
    hb.data.materials.clear()
    from .werkzeug import material_von
    hb.data.materials.append(material_von("Lack"))
    return hb


def wippe():
    teile = []
    for y in (-30.0, 22.0):
        umr = kapsel_umriss((STREBE_OBEN.x, STREBE_OBEN.z), (DAEMPFER_OBEN.x, DAEMPFER_OBEN.z), 15, 15)
        p = ebene_seite(umr, 8.0, y, "Alu_schwarz", 1.6)
        unten = ebene_seite(kapsel_umriss((WIPPE.x - 30, WIPPE.z + 18), (WIPPE.x + 30, WIPPE.z + 16), 14, 14), 8.0, y, "Alu_schwarz", 1.6)
        mitte = ebene_seite(kapsel_umriss((WIPPE.x, WIPPE.z), (WIPPE.x, WIPPE.z + 20), 19, 16), 8.0, y, "Alu_schwarz", 1.6)
        teile += [p, unten, mitte]
    teile.append(kasten("Wippensteg", WIPPE + Vector((-10, -4, 40)), (70, 52, 10), "Alu_schwarz", fase=3))
    for punkt, r in ((STREBE_OBEN, 7), (WIPPE, 8), (DAEMPFER_OBEN, 7)):
        for y in (-34.0, 34.0):
            teile.append(drehteil_achse("Bolzenkopf", [(0, 0), (r + 2.5, 0), (r + 2.5, 3.5), (r - 1, 4.5), (0, 4.5)], "Alu_roh",
                                        punkt + Vector((0, y if y > 0 else y, 0)), Vector((0, 1 if y > 0 else -1, 0)), 24))
    w = verbinden("wippe", teile)
    return drehpunkt(w, WIPPE)


def daempfer():
    a, b = DAEMPFER_UNTEN, DAEMPFER_OBEN
    d = (b - a).normalized()
    teile = []
    for punkt in (a, b):
        teile.append(zylinder("Auge", punkt + Vector((0, -11, 0)), punkt + Vector((0, 11, 0)), 11, "Daempfer", 24))
        teile.append(zylinder("Buchse", punkt + Vector((0, -15.5, 0)), punkt + Vector((0, 15.5, 0)), 6.5, "Alu_roh", 16))
    laenge = (b - a).length
    teile.append(rohr("Luftkammer", [a + d * 18, a + d * 120], lambda t: (24.5, 24.5, 2), "Daempfer", um=40, seite=Vector((0, 1, 0))))
    teile.append(rohr("Dichtkopf", [a + d * 116, a + d * 128], lambda t: (22, 22, 2), "Kunststoff", um=32))
    teile.append(zylinder("Kolbenstange", a + d * 126, a + d * 142, 15.5, "Kolbenstange", 32))
    teile.append(rohr("Daempferkoerper", [a + d * 136, b - d * 14], lambda t: (17.5, 17.5, 2), "Daempfer", um=32))
    seite_z = d.cross(Vector((0, 1, 0))).normalized()
    if seite_z.z < 0:
        seite_z = -seite_z
    ausgleich = b - d * 30 + seite_z * 26
    teile.append(rohr("Ausgleich", [ausgleich - d * 70, ausgleich], lambda t: (13.5, 13.5, 2), "Daempfer", um=28))
    teile.append(rohr("Steg", [b - d * 20, ausgleich - d * 5], lambda t: (8, 10, 2.5), "Daempfer", um=16))
    teile.append(zylinder("Hebel", b - d * 36 + Vector((0, -18, 0)), b - d * 36 + Vector((0, -30, 0)), 8, "Alu_roh", 16))
    teile.append(drehteil_achse("Drehknopf", [(0, 0), (10, 0), (10, 6), (0, 6)], "Kunststoff", ausgleich - d * 72, -d, 24))
    obj = verbinden("daempfer", teile)
    return zusatz(obj, laenge=laenge)


def motor():
    teile = []
    profil = rundrechteck(176, 140, 32, 8)
    gehaeuse = ebene_seite([(TRETLAGER.x + 38 + x, TRETLAGER.z + 6 + z) for x, z in profil], 82.0, -41.0, "Motor", 8.0)
    teile.append(gehaeuse)
    for s in (1, -1):
        deckel = drehteil("Motordeckel", [(0, 0), (40, 0), (44, 1.6 * s), (40, 3.4 * s), (0, 3.4 * s)], "Alu_schwarz_glatt", 64,
                          mitte=(TRETLAGER.x, 41 * s, TRETLAGER.z))
        teile.append(deckel)
    schutz = ebene_seite(chaikin([(TRETLAGER.x + x, TRETLAGER.z + z) for x, z in [(-52, -58), (60, -60), (132, -52), (158, -26), (150, -50), (124, -80), (-30, -82), (-64, -68)]], 3),
                         74.0, -37.0, "Kunststoff", 3.0)
    teiles = [schutz]
    for i in range(6):
        teiles.append(kasten("Rippe", TRETLAGER + Vector((-20 + i * 26, 0, -79)), (6, 70, 6), "Kunststoff", fase=1.5))
    obj = verbinden("motor", teile + teiles)
    return drehpunkt(obj, TRETLAGER)


# ---------------------------------------------------------------- Front


def gabel():
    teile = []
    y = GABEL_ABSTAND
    standrohr_oben = EINBAUHOEHE - 30
    standrohr_unten = 330.0
    for s in (1, -1):
        q = Vector((0, y * s, 0))
        teile.append(zylinder(f"Standrohr{s}", VORN + q + U * standrohr_unten, VORN + q + U * (standrohr_oben + 10), 19.0, "Standrohr", 48))
        teile.append(drehteil_achse("Kappe", [(0, 0), (16, 0), (16, 6), (12, 9), (0, 9)], "Alu_schwarz_glatt", VORN + q + U * (EINBAUHOEHE + 8), U, 32))
    # Krone: zwei Klemmaugen, Schaftauge und eine durchgehende Brücke, zu einem Gussteil verschmolzen
    kr = []
    for s_ in (1, -1):
        q = Vector((0, y * s_, 0))
        kr.append(rohr("Kronenauge", [VORN + q + U * (standrohr_oben - 16), VORN + q + U * (standrohr_oben + 22)], lambda t: (25.5, 25.5, 2), "Alu_schwarz", um=40))
    kr.append(rohr("Schaftauge", [KRONE - U * 14, KRONE + U * 22], lambda t: (26, 26, 2.2), "Alu_schwarz", um=40))
    for s_ in (1, -1):
        bein = VORN + Vector((0, y * s_, 0)) + U * (standrohr_oben + 2)
        kr.append(rohr("Kronenarm", [bein, bein.lerp(KRONE + U * 4, 0.5) + U * 6, KRONE + U * 4], lambda t: (15, 17, 2.6), "Alu_schwarz", um=32, seite=U))
    kr.append(rohr("Kronenbruecke", [VORN + Vector((0, -y, 0)) + U * (standrohr_oben + 4), VORN + U * (standrohr_oben + 16) - N * 8, VORN + Vector((0, y, 0)) + U * (standrohr_oben + 4)],
                   lambda t: (13, 16, 2.6), "Alu_schwarz", um=32, seite=U))
    krone = voxel(verbinden("krone_roh", kr), 1.0, glaettung=5, faktor=0.5)
    krone = boolesch(krone, zylinder("Standrohrbohrung1", VORN + Vector((0, y, 0)) + U * (standrohr_oben - 40), VORN + Vector((0, y, 0)) + U * (standrohr_oben + 40), 19.05, "Alu_schwarz", 40), "DIFFERENCE")
    krone = boolesch(krone, zylinder("Standrohrbohrung2", VORN + Vector((0, -y, 0)) + U * (standrohr_oben - 40), VORN + Vector((0, -y, 0)) + U * (standrohr_oben + 40), 19.05, "Alu_schwarz", 40), "DIFFERENCE")
    teile.append(krone)
    teile.append(zylinder("Schaft", KRONE, STEUERROHR_OBEN + U * 60, 14.3, "Alu_schwarz", 32))
    obj = verbinden("gabel", teile)
    drehpunkt(obj, KRONE)

    unten = []
    for s in (1, -1):
        q = Vector((0, y * s, 0))
        start = VORN + q
        unten.append(rohr(f"Tauchrohr{s}", [start - U * 14, start + U * 70, start + U * 220, start + U * (standrohr_unten + 34)],
                          lambda t: (22 + 3.5 * (1 - t) ** 3, 22 + 2 * (1 - t) ** 3, 2.1), "Tauchrohr", um=44))
        unten.append(drehteil_achse("Abstreifer", [(19.2, 0), (24.5, 0), (24.5, 6), (21, 11), (19.2, 11)], "Gummi", start + U * (standrohr_unten + 34), U, 48))
        ende = ebene_seite(kreis(21, 32, mitte=(VORN.x, VORN.z)), 20.0, y * s - 10, "Tauchrohr", 3)
        unten.append(ende)
    # Brücke vorn, über dem Reifen nach oben gewölbt
    unten.append(rohr("Gabelbruecke", [VORN + Vector((0, -y, 0)) + U * 318 + N * 14, VORN + Vector((0, -y * 0.7, 0)) + U * 366 + N * 30,
                                       VORN + U * 392 + N * 36, VORN + Vector((0, y * 0.7, 0)) + U * 366 + N * 30, VORN + Vector((0, y, 0)) + U * 318 + N * 14],
                      lambda t: (12, 20, 2.6), "Tauchrohr", um=28, seite=N))
    unten.append(zylinder("Steckachse", VORN + Vector((0, -78, 0)), VORN + Vector((0, 78, 0)), 7.5, "Alu_schwarz_glatt", 24))
    unten.append(rohr("Achshebel", [VORN + Vector((0, 80, 0)), VORN + Vector((-14, 84, 22)), VORN + Vector((-22, 85, 52))], lambda t: (5.5 - 1.5 * t, 3.5, 2.5), "Alu_schwarz_glatt", um=16))
    pm = VORN + Vector((0, y + 8, 0)) + U * 78 - N * 26
    pmo = kasten("PostMount", pm, (32, 14, 76), "Tauchrohr", fase=4)
    drehen(pmo, -(math.pi / 2 - LENKWINKEL), "Y", pm)
    unten.append(pmo)
    for s in (1, -1):
        unten.append(drehteil_achse("Entlueftung", [(0, 0), (5, 0), (5, 3), (0, 3)], "Alu_roh", VORN + Vector((0, y * s, 0)) + U * (standrohr_unten + 10) + N * 23, N, 16))
    t = verbinden("gabel_unten", unten)
    drehpunkt(t, VORN)
    return obj, zusatz(t, achse=list(U), federweg=160)


def steuersatz():
    teile = []
    teile.append(drehteil_achse("Lagerschale_unten", [(20, 0), (35, 0), (35, 8), (31, 12), (20, 12)], "Alu_schwarz_glatt", STEUERROHR_UNTEN - U * 18, U, 64))
    deckel = drehteil_achse("Steuersatzdeckel", [(15, 0), (29, 0), (29.5, 7), (27, 13), (15, 13)], "Alu_schwarz_glatt", STEUERROHR_OBEN, U, 64)
    teile.append(deckel)
    for i in range(2):
        teile.append(drehteil_achse("Spacer", [(15, 0), (19, 0), (19, 5), (15, 5)], "Alu_schwarz_glatt", STEUERROHR_OBEN + U * (13 + i * 5), U, 48))
    return verbinden("steuersatz", teile)


def cockpit():
    teile = {}
    # Vorbau: Klemmung am Schaft, Körper, Lenkerklemme mit Frontplatte
    vb = []
    vb.append(rohr("Schaftklemme", [VORBAU - U * 20, VORBAU + U * 20], lambda t: (21, 21, 2.2), "Alu_schwarz", um=40, seite=N))
    vb.append(rohr("Vorbaukoerper", [VORBAU + N * 8, LENKERMITTE - N * 10], lambda t: (17 - 2 * t, 21, 2.8), "Alu_schwarz", um=32))
    vb.append(rohr("Lenkerklemme", [LENKERMITTE + Vector((0, -27, 0)), LENKERMITTE + Vector((0, 27, 0))], lambda t: (21.5, 21.5, 2.2), "Alu_schwarz", um=40, seite=N))
    vb.append(kasten("Frontplatte", LENKERMITTE + N * 19, (10, 56, 40), "Alu_schwarz", fase=3))
    drehen(vb[-1], -(math.pi / 2 - LENKWINKEL), "Y", LENKERMITTE + N * 19)
    for s in (1, -1):
        for zz in (-12, 12):
            p = LENKERMITTE + N * 25 + Vector((0, 18 * s, 0)) + U * zz
            vb.append(drehteil_achse("Schraube", [(0, 0), (4.5, 0), (4.5, 3), (0, 3)], "Alu_roh", p, N, 16))
        p = VORBAU - N * 22 + Vector((0, 0, 0)) + U * (8 * s)
        vb.append(drehteil_achse("Klemmschraube", [(0, 0), (4.5, 0), (4.5, 3), (0, 3)], "Alu_roh", p + Vector((0, -21, 0)), Vector((0, -1, 0)), 16))
    vb.append(drehteil_achse("Ahead", [(0, 0), (16, 0), (16, 4), (0, 6)], "Alu_schwarz_glatt", VORBAU + U * 20, U, 32))
    teile["vorbau"] = verbinden("vorbau", vb)

    # Lenker 780 mm, 25 mm Rise, 8° nach hinten, 5° nach oben
    punkte = []
    for y in (-390, -360, -300, -230, -170, -120, -80, -40, 0, 40, 80, 120, 170, 230, 300, 360, 390):
        a = abs(y)
        rise = 0 if a < 60 else 25 * (1 - math.cos(min(1.0, (a - 60) / 120) * math.pi)) / 2
        rueck = 0 if a < 150 else (a - 150) * math.tan(math.radians(8))
        hoch = 0 if a < 150 else (a - 150) * math.tan(math.radians(5)) * 0.4
        punkte.append(LENKERMITTE + Vector((-rueck, y, rise + hoch)))
    teile["lenker"] = rohr("lenker", punkte, lambda t: (11.1 + 6.4 * max(0, 1 - abs(t - 0.5) * 7.5), 11.1 + 6.4 * max(0, 1 - abs(t - 0.5) * 7.5), 2), "Alu_schwarz",
                           um=36, seite=Vector((0, 0, 1)))
    griffe = []
    enden = {}
    for s in (1, -1):
        ende = punkte[-1] if s > 0 else punkte[0]
        innen = punkte[-3] if s > 0 else punkte[1]
        d = (ende - innen).normalized()
        enden[s] = (ende, d)
        start = ende - d * 136
        griffe.append(rohr(f"Griff{s}", [start, ende + d * 1.5], lambda t: (16 + 1.2 * math.sin(math.pi * t) + (3.5 if t > 0.94 else 0), 16 + 1.2 * math.sin(math.pi * t) + (3.5 if t > 0.94 else 0), 2.1),
                           "Griff", um=36, seite=Vector((0, 0, 1))))
        griffe.append(rohr(f"Klemmring{s}", [start - d * 11, start], lambda t: (17.5, 17.5, 2), "Alu_schwarz", um=28, seite=Vector((0, 0, 1))))
        griffe.append(zylinder("Endkappe", ende + d * 1.5, ende + d * 3.5, 14, "Kunststoff", 24))
    teile["griffe"] = verbinden("griffe", griffe)

    # Bremshebel (4-Kolben-System): Geber am Lenker, Ausgleichsbehälter, Einfingerhebel
    hebel = {}
    for s in (1, -1):
        ende, d = enden[s]
        p = ende - d * 168
        teile_h = []
        teile_h.append(rohr("Schelle", [p - d * 8, p + d * 8], lambda t: (14.5, 14.5, 2.2), "Bremssattel", um=28, seite=Vector((0, 0, 1))))
        koerper = p + Vector((10, 0, 14)) - d * 6
        teile_h.append(rohr("Geber", [koerper - d * 26, koerper + d * 8], lambda t: (12.5, 13.5, 2.3), "Bremssattel", um=28, seite=Vector((0, 0, 1))))
        teile_h.append(kasten("Behaelter", koerper + Vector((-4, 0, 14)) - d * 10, (34, 36, 14), "Bremssattel", fase=4))
        blatt = [koerper + Vector((16, 0, -2)) + d * 4, koerper + Vector((34, 0, -12)) + d * 22, koerper + Vector((42, 0, -22)) + d * 48, koerper + Vector((40, 0, -28)) + d * 70]
        teile_h.append(rohr("Hebelblatt", blatt, lambda t: (6.5 - 1.5 * t + (2.5 if t > 0.88 else 0), 3.6, 2.6), "Alu_schwarz", um=18, seite=Vector((0, 0, 1))))
        teile_h.append(zylinder("Hebelachse", koerper + Vector((16, 0, -2)) + d * 4 + Vector((0, 0, 7)), koerper + Vector((16, 0, -2)) + d * 4 + Vector((0, 0, -7)), 3.2, "Alu_roh", 12))
        hebel[s] = verbinden("bremshebel_l" if s > 0 else "bremshebel_r", teile_h)
        drehpunkt(hebel[s], koerper + Vector((16, 0, -2)) + d * 4)
        zusatz(hebel[s], schlauch=list(koerper + Vector((-8, 0, 2)) - d * 24))
    teile["bremshebel_l"] = hebel[1]
    teile["bremshebel_r"] = hebel[-1]

    # Funk-Schalthebel rechts unter dem Lenker, Vario-Hebel und Motorfernbedienung links
    ende, d = enden[-1]
    p = ende - d * 190 + Vector((6, 0, -18))
    sh = [kasten("Schaltgehaeuse", p, (30, 28, 22), "Kunststoff", fase=6),
          rohr("Schaltpaddel", [p + Vector((8, 0, -6)), p + Vector((28, 6, -14)), p + Vector((40, 16, -16))], lambda t: (7, 3, 2.6), "Alu_schwarz_glatt", um=14, seite=Vector((0, 0, 1)))]
    teile["schalthebel"] = verbinden("schalthebel", sh)
    ende, d = enden[1]
    p = ende - d * 188 + Vector((6, 0, -18))
    teile["vario"] = verbinden("vario", [kasten("Variogehaeuse", p, (26, 24, 18), "Kunststoff", fase=5),
                                          rohr("Variopaddel", [p + Vector((8, 0, -4)), p + Vector((24, -6, -10)), p + Vector((34, -16, -10))], lambda t: (6.5, 3, 2.6), "Alu_schwarz_glatt", um=14, seite=Vector((0, 0, 1)))])
    p = ende - d * 156 + Vector((-14, 0, 10))
    fb = [kasten("Fernbedienung", p, (40, 26, 16), "Kunststoff_glanz", fase=6)]
    for i, dx in enumerate((-10, 0, 10)):
        fb.append(kasten("Taste", p + Vector((dx, 0, 8.5)), (7, 14, 2), "Kunststoff", fase=1.0, segmente=1))
    teile["fernbedienung"] = verbinden("fernbedienung", fb)

    # Farbdisplay auf der Vorbaukappe
    dm = VORBAU + U * 30 + N * 14
    halter = rohr("Displayhalter", [VORBAU + U * 22, dm - U * 6], lambda t: (8, 12, 2.4), "Alu_schwarz", um=16)
    gehaeuse = kasten("Displaygehaeuse", dm, (64, 74, 16), "Kunststoff_glanz", fase=6)
    neig = math.radians(-52)
    drehen(gehaeuse, neig, "Y", dm)
    teile["display"] = verbinden("display", [halter, gehaeuse])
    w, h = 31.0, 25.0
    rot = Matrix.Rotation(neig, 3, "Y")
    ecken = [dm + rot @ Vector((x, yy, 8.2)) for (x, yy) in ((-h, -w), (h, -w), (h, w), (-h, w))]
    schirm = netz("bildschirm", ecken, [(0, 1, 2, 3)], "Bildschirm", [[(0, 1), (0, 0), (1, 0), (1, 1)]], glatt=False)
    teile["bildschirm"] = schirm

    # Scheinwerfer unter dem Lenker
    lp = LENKERMITTE + Vector((22, 0, -44))
    lampe = [rohr("Lampe", [lp - Vector((30, 0, 0)), lp + Vector((14, 0, 0))], lambda t: (15 + 3 * t, 26 + 2 * t, 3.4), "Alu_schwarz", um=40, kappen=(True, False)),
             rohr("Lampenhalter", [lp + Vector((-14, 0, 14)), LENKERMITTE + Vector((-4, 0, -12))], lambda t: (5, 9, 2.4), "Alu_schwarz", um=14)]
    teile["licht_gehaeuse"] = verbinden("licht_gehaeuse", lampe)
    linse = drehteil("licht_vorne", [(0, 0), (16.5, 0), (17.5, -1.5), (0, -2.8)], "Licht", 48, achse="X")
    drehen(linse, math.pi, "Z")
    verschieben(linse, lp + Vector((14.5, 0, 0)))
    zusatz(linse, licht=0.0)
    teile["licht_vorne"] = linse
    return teile


def leitungen(cockpit_teile):
    """Bremsleitungen und Vario-Zug: vom Lenker in den Steuersatzdeckel, vorn zur Gabel."""
    teile = []
    eingang = STEUERROHR_OBEN + U * 8 + N * 30
    links = Vector(cockpit_teile["bremshebel_l"]["schlauch"])
    rechts = Vector(cockpit_teile["bremshebel_r"]["schlauch"])
    vorn_mitte = LENKERMITTE + N * 34 - U * 40
    teile.append(rohr("Leitung_hinten", [rechts, rechts + Vector((36, 26, -26)), vorn_mitte + Vector((0, -46, 6)), vorn_mitte + Vector((0, -16, -40)), eingang + N * 14 + Vector((0, -6, 8)), eingang + Vector((0, -5, 0))],
                      lambda t: (2.6, 2.6, 2), "Leitung", um=12))
    teile.append(rohr("Variozug", [LENKERMITTE + Vector((-22, 198, -24)), LENKERMITTE + Vector((24, 150, -40)), vorn_mitte + Vector((0, 40, 0)), vorn_mitte + Vector((0, 12, -44)),
                                   eingang + N * 14 + Vector((0, 6, 8)), eingang + Vector((0, 5, 0))],
                      lambda t: (2.3, 2.3, 2), "Leitung", um=12))
    pm = VORN + Vector((0, GABEL_ABSTAND + 8, 0)) + U * 104 - N * 24
    teile.append(rohr("Leitung_vorn", [links, links + Vector((40, -22, -30)), vorn_mitte + Vector((10, 60, -10)), KRONE + N * 46 + Vector((0, 74, 10)),
                                       VORN + Vector((0, GABEL_ABSTAND + 26, 0)) + U * 300 - N * 4, VORN + Vector((0, GABEL_ABSTAND + 22, 0)) + U * 180 - N * 16, pm],
                      lambda t: (2.6, 2.6, 2), "Leitung", um=12))
    for p in (VORN + Vector((0, GABEL_ABSTAND + 23, 0)) + U * 240 - N * 12,):
        teile.append(kasten("Leitungsclip", p, (10, 8, 14), "Kunststoff", fase=2))
    return verbinden("leitungen", teile)


def sattel():
    teile = []
    oben = SITZROHR_OBEN + S * 250
    teile.append(zylinder("Stuetze_unten", SITZROHR_OBEN - S * 110, SITZROHR_OBEN + S * 26, 15.8, "Alu_schwarz", 40))
    teile.append(drehteil_achse("Dichtring", [(15.8, 0), (19.5, 0), (19.5, 10), (17, 14), (15.8, 14)], "Kunststoff", SITZROHR_OBEN + S * 26, S, 40))
    teile.append(zylinder("Stuetze_oben", SITZROHR_OBEN + S * 38, oben, 13.0, "Alu_schwarz_glatt", 40))
    teile.append(drehteil_achse("Kragen", [(15.8, 0), (21.5, 0), (21.5, 14), (15.8, 14)], "Alu_schwarz", SITZROHR_OBEN - S * 2, S, 40))
    kopf = oben + S * 10
    teile.append(kasten("Stuetzenkopf", kopf, (62, 26, 18), "Alu_schwarz", fase=5))
    stuetze = verbinden("sattelstuetze", teile)
    drehpunkt(stuetze, SITZROHR_OBEN)

    mitte = kopf + Vector((-4, 0, 34))
    laenge = 262.0

    def profil(t):
        if t > 0.58:
            breite = 17 + (70 - 17) * ((1 - t) / 0.42) ** 0.75
        else:
            breite = 70 - 6 * ((0.58 - t) / 0.58) ** 2.4
        hoehe = 12 if t > 0.12 else 8 + 4 * (t / 0.12)
        return (hoehe, breite, 2.6)

    punkte = [mitte + Vector((-laenge * 0.47, 0, 10)), mitte + Vector((-laenge * 0.18, 0, 0)), mitte + Vector((laenge * 0.22, 0, -1)), mitte + Vector((laenge * 0.53, 0, 3))]
    polster = rohr("Polster", punkte, profil, "Sattel", um=48)
    schale = rohr("Schale", [p + Vector((0, 0, -9)) for p in punkte], lambda t: (5, profil(t)[1] - 3, 2.4), "Kunststoff", um=40)
    streben = []
    for s in (1, -1):
        streben.append(rohr(f"Strebe{s}", [mitte + Vector((-104, 34 * s, -14)), mitte + Vector((-64, 22 * s, -30)), mitte + Vector((40, 14 * s, -32)), mitte + Vector((108, 6 * s, -16))],
                            lambda t: (3.5, 3.5, 2), "Stahl_dunkel", um=12))
    sa = verbinden("sattel", [polster, schale] + streben)
    drehpunkt(sa, SITZROHR_OBEN)
    return stuetze, sa


# ---------------------------------------------------------------- Antrieb


def kurbelsatz():
    teile = {}
    rp = teilkreis(KETTENBLATT_ZAEHNE)
    fenster = []
    for k in range(4):
        w0 = TAU * k / 4 + math.pi / 4
        pk = []
        ra, ri = rp - 12, 33
        for j in range(10):
            t = j / 9
            pk.append((ra * math.cos(w0 + 0.22 + t * 1.13), ra * math.sin(w0 + 0.22 + t * 1.13)))
        for j in range(10):
            t = 1 - j / 9
            pk.append((ri * math.cos(w0 + 0.48 + t * 0.6), ri * math.sin(w0 + 0.48 + t * 0.6)))
        fenster.append(pk)
    blatt = umriss("Blatt", [zahnkranz_umriss(KETTENBLATT_ZAEHNE, breit_schmal=True), kreis(15, 32)] + fenster, 2.4, "Kettenblatt", fase=0.5, y=KETTENBLATT_Y)
    kern = drehteil("Direktmontage", [(14, KETTENBLATT_Y + 1.2), (31, KETTENBLATT_Y + 1.2), (31, KETTENBLATT_Y + 6), (14, KETTENBLATT_Y + 6)], "Alu_schwarz", 48)
    teile["kettenblatt"] = verbinden("kettenblatt", [blatt, kern])
    w0 = math.radians(-35)
    for seite, y, w in ((-1, -70.0, w0), (1, 70.0, w0 + math.pi)):
        d = Vector((math.cos(w), 0, math.sin(w)))
        ende = d * KURBEL + Vector((0, y + 8 * seite, 0))
        arm = rohr("Arm", [Vector((0, y, 0)), d * 70 + Vector((0, y + 4 * seite, 0)), ende],
                   lambda t: (17 - 6 * t, 10.5 + 1.5 * t, 3.4), "Alu_schwarz", um=32, seite=Vector((0, 1, 0)))
        schutz = rohr("Kurbelschutz", [d * 70 + Vector((0, y + 4 * seite + 9 * seite, 0)), d * 140 + Vector((0, y + 7 * seite + 9 * seite, 0))],
                      lambda t: (11 - 2 * t, 2.2, 2.4), "Kunststoff", um=20, seite=Vector((0, 1, 0)))
        nabe_ = drehteil("Kurbelauge", [(0, y - 11), (19, y - 11), (21, y), (19, y + 11), (0, y + 11)], "Alu_schwarz", 40)
        auge = drehteil("Pedalauge", [(0, ende.y - 8), (12, ende.y - 8), (12, ende.y + 8), (0, ende.y + 8)], "Alu_schwarz", 32)
        verschieben(auge, (ende.x, 0, ende.z))
        name = "kurbel_" + ("l" if seite > 0 else "r")
        teile[name] = verbinden(name, [arm, schutz, nabe_, auge])
        # Flachpedal mit Pins
        p = []
        y0 = ende.y + 12 * seite
        p.append(zylinder("Pedalachse", Vector((0, ende.y, 0)), Vector((0, y0 + 102 * seite, 0)), 6.5, "Stahl", 16))
        umr = rundrechteck(104, 100, 14, 5)
        koerper = platte("Pedalkoerper", umr, 15.0, "Alu_schwarz", 1.5, Matrix.Translation((0, y0 + 52 * seite, -7.5)), loecher=[rundrechteck(70, 66, 10, 4)])
        p.append(koerper)
        for ix in (-1, 1):
            for iy in (-1, -0.33, 0.33, 1):
                for iz in (-1, 1):
                    q = Vector((ix * 44, y0 + 52 * seite + iy * 42, iz * 7.5))
                    p.append(zylinder("Pin", q, q + Vector((0, 0, 4 * iz)), 1.6, "Stahl", 8))
        ped = verbinden("pedal_" + ("l" if seite > 0 else "r"), p)
        verschieben(ped, (ende.x, 0, ende.z))
        teile["pedal_" + ("l" if seite > 0 else "r")] = ped
    for name, obj in teile.items():
        verschieben(obj, TRETLAGER)
        if name.startswith("pedal"):
            w = w0 if name.endswith("_r") else w0 + math.pi
            drehpunkt(obj, TRETLAGER + Vector((math.cos(w) * KURBEL, 0, math.sin(w) * KURBEL)))
        else:
            drehpunkt(obj, TRETLAGER)
    zusatz(teile["kettenblatt"], zaehne=KETTENBLATT_ZAEHNE, y=KETTENBLATT_Y)
    zusatz(teile["kurbel_r"], laenge=KURBEL, startwinkel=w0)
    return teile


def schaltwerk():
    """Schaltwerk ohne Schaltauge, direkt an der Achse (Lage des Käfigs setzt die Kette)."""
    teile = {}
    rj = teilkreis(SCHALTROLLE_ZAEHNE)
    halter_p = HINTEN + Vector((0, -88, 0))
    halter = [drehteil_achse("Achsaufnahme", [(0, 0), (19, 0), (19, 12), (15, 15), (0, 15)], "Alu_schwarz", halter_p, Vector((0, -1, 0)), 40),
              rohr("Halterarm", [halter_p + Vector((0, -6, 0)), halter_p + Vector((-28, -10, -34)), halter_p + Vector((-34, -14, -62))],
                   lambda t: (13, 9, 2.6), "Alu_schwarz", um=24)]
    teile["schaltwerk_halter"] = drehpunkt(verbinden("schaltwerk_halter", halter), halter_p)
    para = [kasten("Parallelogramm", (34, -6, 0), (66, 20, 32), "Alu_schwarz", fase=5),
            kasten("Batterie", (30, -18, 10), (40, 12, 26), "Kunststoff_glanz", fase=4),
            kasten("Kopf", (70, 0, -4), (26, 26, 34), "Alu_schwarz", fase=6)]
    teile["schaltwerk_arm"] = verbinden("schaltwerk_arm", para)
    platten = []
    for seite in (1, -1):
        r_o, r_u = rj + 4.5, rj + 6.0
        kontur = []
        for i in range(13):
            w = math.radians(-20) + math.radians(220) * i / 12
            kontur.append((r_o * math.cos(w), r_o * math.sin(w)))
        kontur.append((-14, -KAEFIG * 0.5))
        for i in range(13):
            w = math.radians(150) + math.radians(230) * i / 12
            kontur.append((r_u * math.cos(w) + 4, r_u * math.sin(w) - KAEFIG))
        kontur.append((16, -KAEFIG * 0.55))
        pl = umriss(f"Kaefigplatte{seite}", [chaikin(kontur, 2)], 2.6, "Alu_schwarz" if seite < 0 else "Alu_roh", fase=0.6, y=8.0 * seite)
        platten.append(pl)
    platten.append(zylinder("Achse_oben", Vector((0, -10, 0)), Vector((0, 10, 0)), 4, "Alu_roh", 16))
    platten.append(zylinder("Achse_unten", Vector((0, -10, -KAEFIG)), Vector((0, 10, -KAEFIG)), 4, "Alu_roh", 16))
    teile["schaltwerk_kaefig"] = verbinden("schaltwerk_kaefig", platten)
    for name in ("oben", "unten"):
        r = umriss(f"rolle_{name}", [zahnkranz_umriss(SCHALTROLLE_ZAEHNE), kreis(6, 16)], 3.0, "Kunststoff", fase=0.4, y=0)
        nb = drehteil("Rollennabe", [(5.5, -4.5), (10, -4.5), (10, 4.5), (5.5, 4.5)], "Alu_roh", 24)
        teile[f"rolle_{name}"] = verbinden(f"rolle_{name}", [r, nb])
    verschieben(teile["rolle_unten"], (0, 0, -KAEFIG))
    drehpunkt(teile["rolle_unten"], (0, 0, -KAEFIG))
    zusatz(teile["schaltwerk_halter"], ort=list(halter_p))
    return teile


def kettenglieder():
    def lasche(name, y, dicke, mat):
        pk = []
        for i in range(13):
            w = math.pi / 2 + math.pi * i / 12
            pk.append((4.7 * math.cos(w), 4.7 * math.sin(w)))
        for i in range(5):
            t = i / 4
            pk.append((t * TEILUNG, -4.7 + 1.1 * math.sin(math.pi * t)))
        for i in range(13):
            w = -math.pi / 2 + math.pi * i / 12
            pk.append((TEILUNG + 4.7 * math.cos(w), 4.7 * math.sin(w)))
        for i in range(5):
            t = i / 4
            pk.append((TEILUNG - t * TEILUNG, 4.7 - 1.1 * math.sin(math.pi * t)))
        return umriss(name, [pk, kreis(1.9, 12), kreis(1.9, 12, mitte=(TEILUNG, 0))], dicke, mat, fase=0.25, y=y)

    aussen = [lasche("A1", 4.9, 1.0, "Kette"), lasche("A2", -4.9, 1.0, "Kette"),
              zylinder("Bolzen1", Vector((0, -5.7, 0)), Vector((0, 5.7, 0)), 1.85, "Stahl", 10),
              zylinder("Bolzen2", Vector((TEILUNG, -5.7, 0)), Vector((TEILUNG, 5.7, 0)), 1.85, "Stahl", 10)]
    innen = [lasche("I1", 3.3, 0.9, "Stahl_dunkel"), lasche("I2", -3.3, 0.9, "Stahl_dunkel"),
             zylinder("Rolle1", Vector((0, -2.85, 0)), Vector((0, 2.85, 0)), 3.85, "Stahl_dunkel", 16),
             zylinder("Rolle2", Vector((TEILUNG, -2.85, 0)), Vector((TEILUNG, 2.85, 0)), 3.85, "Stahl_dunkel", 16)]
    return verbinden("glied_aussen", aussen), verbinden("glied_innen", innen)


def bremssattel(vorn):
    seite = "v" if vorn else "h"
    mitte = VORN if vorn else HINTEN
    r_aussen = ROTOR[seite]
    y_scheibe = ROTOR_Y[seite]
    winkel = math.radians(150) if vorn else math.radians(26)
    r_mitte = r_aussen - 9
    ort = mitte + Vector((r_mitte * math.cos(winkel), y_scheibe, r_mitte * math.sin(winkel)))
    tangente = Vector((-math.sin(winkel), 0, math.cos(winkel)))
    radial = Vector((math.cos(winkel), 0, math.sin(winkel)))
    teile = []
    for s in (1, -1):
        haelfte = kasten(f"Sattelhaelfte{s}", (0, 11.5 * s, 2), (84, 17, 34), "Bremssattel", fase=6, segmente=4)
        teile.append(haelfte)
        for i in (-1, 1):
            k = drehteil(f"Kolbendeckel{s}{i}", [(0, 0), (9.5, 0), (9.5, 2.0 * s), (0, 2.0 * s)], "Alu_roh", 24)
            verschieben(k, (i * 21, 20 * s, 0))
            teile.append(k)
    teile.append(kasten("Satteldach", (0, 0, 17), (76, 40, 10), "Bremssattel", fase=4))
    teile.append(zylinder("Entlueftung", Vector((30, 10, 18)), Vector((32, 10, 28)), 3.4, "Alu_roh", 12))
    teile.append(zylinder("Banjo", Vector((-36, 12, 14)), Vector((-36, 26, 14)), 6.5, "Alu_roh", 16))
    for i in (-1, 1):
        teile.append(zylinder(f"Bolzen{i}", Vector((i * 28, 25, -6)), Vector((i * 28, -25, -6)), 4.0, "Stahl_dunkel", 16))
    sattel_obj = verbinden(f"bremssattel_{seite}", teile)
    belaege = []
    for s in (1, -1):
        b = kasten(f"belag{s}", (0, 3.0 * s, 0), (62, 3.4, 17), "Belag", fase=1.4, segmente=2)
        rueck = kasten(f"traeger{s}", (0, 5.4 * s, 0), (64, 1.6, 19), "Stahl_dunkel", fase=0.5, segmente=1)
        belaege.append(verbinden(f"belag_{seite}_{'l' if s > 0 else 'r'}", [b, rueck]))
    m = Matrix.Translation(ort) @ Matrix(((tangente.x, 0, radial.x, 0), (0, 1, 0, 0), (tangente.z, 0, radial.z, 0), (0, 0, 0, 1)))
    for o in [sattel_obj] + belaege:
        o.data.transform(m)
        drehpunkt(o, ort)
    return sattel_obj, belaege


def ruecklicht():
    br = HINTEN.lerp(STREBE_OBEN, 0.68) + Vector((12, 0, 0))
    gehaeuse = kasten("Ruecklichtgehaeuse", br + Vector((-14, 0, -2)), (12, 44, 18), "Kunststoff_glanz", fase=4)
    linse = kasten("licht_hinten", br + Vector((-20.5, 0, -2)), (2.0, 38, 12), "Ruecklicht", fase=1.0, segmente=2)
    zusatz(linse, licht=0.0)
    return gehaeuse, linse


def staender():
    """Montageständer: Stahlteller, Teleskopsäule, Drehkopf, Klemme an der Sattelstütze."""
    teile = []
    klemme = SITZROHR_OBEN + S * 120
    sx, sy = klemme.x - 40, 470.0
    kopf_z = klemme.z + 60
    teile.append(drehteil("Teller", [(0, BODEN + 6), (300, BODEN + 6), (304, BODEN + 9), (304, BODEN + 16), (298, BODEN + 20), (0, BODEN + 20)], "Staender", 96,
                          mitte=(sx, sy, 0), achse="Z"))
    teile.append(drehteil("Tellerring", [(0, BODEN), (292, BODEN), (296, BODEN + 2), (296, BODEN + 6), (0, BODEN + 6)], "Gummi", 72, mitte=(sx, sy, 0), achse="Z"))
    teile.append(drehteil("Fussnabe", [(0, BODEN + 20), (62, BODEN + 20), (58, BODEN + 34), (34, BODEN + 52), (0, BODEN + 52)], "Staender", 48, mitte=(sx, sy, 0), achse="Z"))
    unten_oben = BODEN + 900
    teile.append(zylinder("Saeule", Vector((sx, sy, BODEN + 40)), Vector((sx, sy, unten_oben)), 24.0, "Staender", 40))
    teile.append(drehteil("Manschette", [(0, unten_oben - 34), (31, unten_oben - 34), (33, unten_oben - 30), (33, unten_oben + 8), (29, unten_oben + 12), (0, unten_oben + 12)], "Staender", 40,
                          mitte=(sx, sy, 0), achse="Z"))
    hebel_a = Vector((sx + 30, sy - 8, unten_oben - 12))
    teile.append(rohr("Schnellspanner", [hebel_a, hebel_a + Vector((40, -30, 6)), hebel_a + Vector((92, -42, 18))], lambda t: (6.5 - 2 * t, 4.5, 2.5), "Staender_Stahl", um=14))
    teile.append(zylinder("Innenrohr", Vector((sx, sy, unten_oben - 60)), Vector((sx, sy, kopf_z - 30)), 19.0, "Staender_Stahl", 36))
    kopf = Vector((sx, sy, kopf_z))
    teile.append(rohr("Kopfgehaeuse", [kopf + Vector((0, 0, -46)), kopf + Vector((0, 0, 10))], lambda t: (27, 27, 3), "Staender", um=36))
    teile.append(zylinder("Drehnabe", kopf + Vector((0, 40, 0)), kopf + Vector((0, -52, 0)), 36.0, "Staender", 48))
    teile.append(drehteil("Raendelrad", [(0, 40), (44, 40), (46, 43), (46, 62), (42, 66), (0, 66)], "Kunststoff", 48, mitte=(sx, sy, kopf_z)))
    for k in range(24):
        w = TAU * k / 24
        q = kopf + Vector((46 * math.cos(w), 52, 46 * math.sin(w)))
        teile.append(kasten(f"Rippe{k}", q, (4, 22, 4), "Kunststoff", fase=1.0, segmente=1))
    teile.append(drehteil("Drehscheibe", [(0, -52), (40, -52), (42, -55), (42, -60), (0, -60)], "Staender_Stahl", 48, mitte=(sx, sy, kopf_z)))
    arm_a = kopf + Vector((0, -58, 0))
    arm_b = Vector((klemme.x - 6, 62, klemme.z + 6))
    teile.append(rohr("Ausleger", [arm_a, arm_a.lerp(arm_b, 0.5) + Vector((0, 0, 4)), arm_b], lambda t: (17, 15, 4), "Staender", um=28))
    klemmteile = [kasten("Klemmkoerper", (0, 52, 0), (64, 40, 78), "Staender", fase=8, segmente=3)]
    for s in (1, -1):
        klemmteile.append(rohr(f"Backe{s}", [Vector((30 * s, 40, -34)), Vector((30 * s, 40, 34))], lambda t: (12, 22, 4), "Staender", um=20))
        bogen = []
        for i in range(9):
            w = math.radians(-70 + 140 * i / 8) if s > 0 else math.radians(110 + 140 * i / 8)
            bogen.append(Vector((19 * math.cos(w), 19 * math.sin(w) * 0.98 + 2, 0)))
        for i in range(len(bogen) - 1):
            a, b = bogen[i], bogen[i + 1]
            mitte = (a + b) / 2
            stueck = kasten(f"Polster{s}{i}", mitte, (max((b - a).length, 1) + 1.0, 6, 62), "Gummi", fase=1.5, segmente=1)
            d = (b - a).normalized()
            drehen(stueck, math.atan2(d.y, d.x), "Z", mitte)
            klemmteile.append(stueck)
        klemmteile.append(rohr(f"Kiefer{s}", [Vector((30 * s, 38, 0)), Vector((27 * s, 16, 0)), Vector((22 * s, 6, 0))], lambda t: (26, 9, 3), "Staender", um=20, seite=Vector((0, 0, 1))))
    klemmteile.append(zylinder("Spindel", Vector((0, 72, 18)), Vector((0, 126, 18)), 7.0, "Staender_Stahl", 16))
    klemmteile.append(rohr("Knebel", [Vector((-58, 128, 18)), Vector((58, 128, 18))], lambda t: (6, 6, 2), "Staender_Stahl", um=14, seite=Vector((0, 0, 1))))
    for x in (-62, 62):
        klemmteile.append(zylinder("Knebelkappe", Vector((x * 0.94, 128, 18)), Vector((x * 1.12, 128, 18)), 9.5, "Kunststoff", 16))
    ausrichtung = Matrix.Translation(klemme) @ Matrix.Rotation(-(math.pi / 2 - SITZWINKEL), 4, "Y")
    for t in klemmteile:
        t.data.transform(ausrichtung)
    teile += klemmteile
    obj = verbinden("staender", teile)
    return drehpunkt(obj, klemme)


# ---------------------------------------------------------------- Aufkleber


def aufkleber(name, bild, mitte, u, normale, breite, hoehe, ziel, teile_u=48, teile_v=10, abstand=0.12):
    """Legt ein Bild als dünne Haut auf `ziel`: Gitter vor die Fläche setzen, entlang der Normalen aufprojizieren."""
    from . import materialien
    n = Vector(normale).normalized()
    u = Vector(u)
    u = (u - n * u.dot(n)).normalized()
    v = n.cross(u)
    if v.z < -1e-6:
        u = -u
        v = n.cross(u)
    mitte = Vector(mitte)
    punkte, flaechen, uvs = [], [], []
    for j in range(teile_v + 1):
        for i in range(teile_u + 1):
            s, t = i / teile_u, j / teile_v
            punkte.append(mitte + u * ((s - 0.5) * breite) + v * ((t - 0.5) * hoehe) + n * 30)
    for j in range(teile_v):
        for i in range(teile_u):
            a = j * (teile_u + 1) + i
            flaechen.append((a, a + 1, a + teile_u + 2, a + teile_u + 1))
            uvs.append([(i / teile_u, j / teile_v), ((i + 1) / teile_u, j / teile_v), ((i + 1) / teile_u, (j + 1) / teile_v), (i / teile_u, (j + 1) / teile_v)])
    mat_name = "Dekor_" + bild.split(".")[0]
    if mat_name not in materialien.MATS:
        materialien.MATS[mat_name] = materialien.dekor(mat_name, bild)
    obj = netz(name, punkte, flaechen, materialien.MATS[mat_name], uvs, glatt=True)
    mod = obj.modifiers.new("Auflegen", "SHRINKWRAP")
    mod.wrap_method = "PROJECT"
    mod.use_negative_direction = True
    mod.use_positive_direction = False
    mod.target = ziel
    mod.offset = abstand
    mod.project_limit = 80
    obj = auswerten(obj)
    obj.name = name
    obj.visible_shadow = False
    # Gitterpunkte, die keine Fläche getroffen haben, schweben – samt ihren Flächen entfernen
    dg = bpy.context.evaluated_depsgraph_get()
    ziel_ev = ziel.evaluated_get(dg)
    inv = ziel.matrix_world.inverted()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    weg = []
    for v in bm.verts:
        ok, punkt, _, _ = ziel_ev.closest_point_on_mesh(inv @ (obj.matrix_world @ v.co))
        if not ok or (ziel.matrix_world @ punkt - obj.matrix_world @ v.co).length > 1.5:
            weg.append(v)
    bmesh.ops.delete(bm, geom=weg, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def rahmen_aufkleber(rahmen, gabel_unten, felgen, motor_):
    teile = {}
    a, b, d, quer = akkuschacht()
    for s, nm in ((-1, "logo_r"), (1, "logo_l")):
        mitte = UNTERROHR_A.lerp(UNTERROHR_B, 0.47) - quer * 19 + Vector((0, 42 * s, 0))
        teile[nm] = aufkleber(nm, "rahmen_logo.png", mitte, -d, Vector((0, s, 0)), 196, 42, rahmen, 64, 12)
    ot = OBERROHR_A.lerp(OBERROHR_B, 0.42) + Vector((0, -26, 0))
    teile["oberrohr_text"] = aufkleber("oberrohr_text", "oberrohr.png", ot, (OBERROHR_A - OBERROHR_B), Vector((0, -1, 0)), 120, 11, rahmen, 32, 4)
    pl = TRETLAGER + S * 395 + Vector((0, -24, 0))
    teile["inspektion"] = aufkleber("inspektion", "inspektion.png", pl, S, Vector((0, -1, 0)), 24, 35, rahmen, 12, 16)
    teile["motor_text"] = aufkleber("motor_text", "motor.png", TRETLAGER + Vector((70, -42, 18)), Vector((1, 0, 0)), Vector((0, -1, 0)), 56, 12, motor_, 16, 4)
    for s in (-1, 1):
        q = VORN + Vector((0, (GABEL_ABSTAND + 24) * s, 0)) + U * 150
        teile[f"gabel_text{s}"] = aufkleber(f"gabel_text{s}", "gabel.png", q, U, Vector((0, s, 0)), 92, 31, gabel_unten, 24, 8)
    for felge_obj in felgen:
        mitte_r = felge_obj.matrix_world.translation
        for s in (-1, 1):
            for w0 in (0.6, 0.6 + math.pi):
                teile[f"{felge_obj.name}_text{s}{w0:.1f}"] = felgen_aufkleber(felge_obj, mitte_r, s, w0)
    return teile


def felgen_aufkleber(felge_obj, mitte, s, w0):
    from . import materialien
    mat_name = "Dekor_felge"
    if mat_name not in materialien.MATS:
        materialien.MATS[mat_name] = materialien.dekor(mat_name, "felge.png", glanz=False)
    spanne = 0.62
    ri, ra = 299.5, 307.5
    punkte, flaechen, uvs = [], [], []
    n = 40
    for j in range(2):
        for i in range(n + 1):
            w = w0 + spanne * (i / n - 0.5) * (-s)
            r = ri + (ra - ri) * j
            y = (17.75 + 0.15) * s
            punkte.append(mitte + Vector((r * math.cos(w), y, r * math.sin(w))))
    for i in range(n):
        flaechen.append((i, i + 1, i + n + 2, i + n + 1))
        uvs.append([(i / n, 0), ((i + 1) / n, 0), ((i + 1) / n, 1), (i / n, 1)])
    obj = netz(f"felgentext", punkte, flaechen, materialien.MATS[mat_name], uvs, glatt=True)
    obj.visible_shadow = False
    return obj


# ---------------------------------------------------------------- Zusammenbau

GRUPPEN = {
    "vorderbau": ("KRONE", None, ["gabel", "steuersatz", "leitungen"]),
    "federung": ("VORN", "vorderbau", ["gabel_unten", "gabel_text-1", "gabel_text1"]),
    "laufradV": ("VORN", "federung", ["felge_v", "reifen_v", "speichen_v", "nabe_v", "bremsscheibe_v"]),
    "bremseV": ("SATTEL_V", "federung", ["bremssattel_v", "belag_v_l", "belag_v_r"]),
    "cockpit": ("LENKERMITTE", "vorderbau", ["vorbau", "lenker", "griffe", "bremshebel_l", "bremshebel_r", "schalthebel", "vario", "fernbedienung",
                                             "display", "bildschirm", "licht_gehaeuse", "licht_vorne"]),
    "laufradH": ("HINTEN", None, ["felge_h", "reifen_h", "speichen_h", "nabe_h", "bremsscheibe_h"]),
    "ritzel": ("HINTEN", "laufradH", ["kassette"]),
    "kurbel": ("TRETLAGER", None, ["kettenblatt", "kurbel_r", "kurbel_l", "pedal_r", "pedal_l"]),
    "sattel": ("SITZROHR_OBEN", None, ["sattel", "sattelstuetze"]),
    "akku": ("AKKU", None, ["akku"]),
    "motor": ("TRETLAGER", None, ["motor", "motor_text"]),
    "bremseH": ("SATTEL_H", None, ["bremssattel_h", "belag_h_l", "belag_h_r"]),
    "schaltwerk": ("HINTEN", None, ["schaltwerk_halter", "schaltwerk_arm", "schaltwerk_kaefig", "rolle_oben", "rolle_unten"]),
}


def leer(name, ort, eltern=None):
    """Leer-Objekt als Drehpunkt einer Gruppe; 'welt' merkt sich die Lage in Weltkoordinaten."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 40
    bpy.context.scene.collection.objects.link(e)
    ort = Vector(ort)
    if eltern is not None:
        e.parent = eltern
        e.location = ort - Vector(eltern["welt"])
    else:
        e.location = ort
    e["welt"] = list(ort)
    return e


def anhaengen(obj, eltern):
    """Hängt ein Teil an eine Gruppe; alle Teile sind beim Bau unverdreht, also reicht die Verschiebung."""
    welt = obj.location.copy()
    obj.parent = eltern
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.location = welt - Vector(eltern["welt"])


def bauen(mit_staender=True):
    """Baut das ganze Rad und hängt die Teile an Gruppen (Leer-Objekte) für die Zeitleiste."""
    t = {}
    rahmen = rahmen_vorn()
    rahmen, akku_obj = akku_und_schacht(rahmen)
    t["rahmen"] = rahmen
    t["akku"] = akku_obj
    t["hinterbau"] = hinterbau()
    t["wippe"] = wippe()
    t["daempfer"] = daempfer()
    t["motor"] = motor()
    g, gu = gabel()
    t["gabel"], t["gabel_unten"] = g, gu
    t["steuersatz"] = steuersatz()
    t.update(cockpit())
    t["leitungen"] = leitungen(t)
    st, sa = sattel()
    t["sattelstuetze"], t["sattel"] = st, sa
    for vorn in (True, False):
        t.update(laufrad(vorn))
        sat, bel = bremssattel(vorn)
        t[sat.name] = sat
        for b_ in bel:
            t[b_.name] = b_
    t.update(kurbelsatz())
    t.update(schaltwerk())
    a, i = kettenglieder()
    for o in (a, i):
        o.hide_render = True
        o.hide_viewport = True
    t["glied_aussen"], t["glied_innen"] = a, i
    rl, linse = ruecklicht()
    t["ruecklicht"], t["licht_hinten"] = rl, linse
    t.update(rahmen_aufkleber(rahmen, gu, [t["felge_v"], t["felge_h"]], t["motor"]))
    if mit_staender:
        t["staender"] = staender()

    for name, o in t.items():
        o.name = name
        if o.data:
            o.data.name = name
    orte = {
        "KRONE": KRONE, "VORN": VORN, "HINTEN": HINTEN, "LENKERMITTE": LENKERMITTE, "TRETLAGER": TRETLAGER, "SITZROHR_OBEN": SITZROHR_OBEN,
        "AKKU": t["akku"].matrix_world.translation.copy(), "SATTEL_V": t["bremssattel_v"].matrix_world.translation.copy(),
        "SATTEL_H": t["bremssattel_h"].matrix_world.translation.copy(),
    }
    wurzel = leer("rad", Vector((0, 0, 0)))
    gruppen = {}
    for name, (ort, eltern, _) in GRUPPEN.items():
        gruppen[name] = leer(name, orte[ort], gruppen[eltern] if eltern else wurzel)
    for name, (_, _, mitglieder) in GRUPPEN.items():
        for m in mitglieder:
            if m in t:
                anhaengen(t[m], gruppen[name])
    for name, o in t.items():
        if o.parent is None:
            anhaengen(o, wurzel)
    for felge_text in [n for n in t if n.startswith("felge_") and "_text" in n]:
        anhaengen(t[felge_text], gruppen["laufradV" if felge_text.startswith("felge_v") else "laufradH"])
    for e in list(gruppen.values()) + [wurzel]:
        e["basis"] = list(e.location)
    for o in t.values():
        o["basis"] = list(o.location)
    return t, gruppen, wurzel

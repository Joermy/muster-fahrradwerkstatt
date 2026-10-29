"""Zeitleiste der Startseite: p = 0 … 8 (ein Kapitel je Bildschirmhöhe Scrollweg).

Alles hier ist eine reine Funktion von p, damit jedes Bild für sich gerendert werden kann und die
Seite dieselben Werte (Gang, Temperatur …) ohne Blender ausrechnet. Die Formeln stammen aus der
Echtzeitfassung (public/assets/js/rad/effekte.js, regie.js, zerlegen.js) und sind in
public/assets/js/werkstatt/zeitleiste.js gespiegelt.
"""

import math

from mathutils import Matrix, Vector

from . import rad

KAPITEL = 8
BILDER_JE_KAPITEL = 24

# Kameraeinstellungen in Weltkoordinaten (x, y, z wie das Rad), Brennweite über das Blickfeld (vertikal, Grad)
EINSTELLUNGEN = [
    {"name": "ankunft", "auge": (2650, -3150, 700), "ziel": (640, 0, 470), "fov": 28, "drift": (-260, -120, 40), "blende": 5.6, "versatz": 0.16},
    {"name": "diagnose", "auge": (640, -3900, 560), "ziel": (640, 0, 480), "fov": 27, "drift": (0, 120, 0), "blende": 8.0, "versatz": 0.14},
    {"name": "zerlegen", "auge": (2500, -3600, 1750), "ziel": (600, 0, 380), "fov": 31, "drift": (-220, -120, -60), "blende": 8.0, "versatz": -0.14},
    {"name": "antrieb", "auge": (300, -1000, 450), "ziel": (190, -40, 335), "fov": 30, "drift": (60, 40, -20), "blende": 2.8, "versatz": 0.14},
    {"name": "bremse", "auge": (1420, 560, 540), "ziel": (1190, 52, 420), "fov": 29, "drift": (-50, 30, 20), "blende": 2.8, "versatz": -0.14},
    {"name": "laufrad", "auge": (-1500, -1250, 760), "ziel": (40, -10, 370), "fov": 27, "drift": (80, 60, -30), "blende": 4.0, "versatz": 0.14},
    {"name": "akku", "auge": (980, -1500, 300), "ziel": (720, -30, 540), "fov": 32, "drift": (-80, 40, 30), "blende": 4.0, "versatz": -0.14},
    {"name": "uebergabe", "auge": (3150, -1900, 330), "ziel": (600, 0, 470), "fov": 30, "drift": (-220, -120, 40), "blende": 5.6, "versatz": 0.14},
]

SENSOR = 36.0


def klemm(x, a, b):
    return max(a, min(b, x))


def glatt(a, b, x):
    t = klemm((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def sanft(x):
    return x * x * x * (x * (x * 6 - 15) + 10)


def fenster(a, b, c, d, x):
    return glatt(a, b, x) * (1 - glatt(c, d, x))


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- Kamera


def einstellung(i, f):
    e = EINSTELLUNGEN[max(0, min(KAPITEL - 1, i))]
    d = f - 0.3
    auge = Vector(e["auge"]) + Vector(e["drift"]) * d
    return e, auge, Vector(e["ziel"])


def kamera_bei(p):
    """Kameralage für p. Jedes Kapitel ist eine ruhige Einstellung mit leichter Fahrt; zwischen den
    Kapiteln blendet der Spieler über. Kameraflüge bräuchten ein Vielfaches an Bildern, um flüssig zu sein."""
    k = min(int(math.floor(p)), KAPITEL - 1)
    e, auge, ziel = einstellung(k, p - k)
    return {"auge": auge, "ziel": ziel, "fov": e["fov"], "blende": e["blende"], "versatz": e["versatz"], "kapitel": k, "name": e["name"]}


def kamera_setzen(cam, lage, breite, hoehe):
    auge, ziel = lage["auge"], lage["ziel"]
    cam.location = auge
    cam.rotation_euler = (ziel - auge).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_width = SENSOR
    cam.data.sensor_height = SENSOR * hoehe / breite
    cam.data.angle = math.radians(lage["fov"])
    # Bild nach links/rechts verschieben, damit Platz für den Text bleibt (wie setViewOffset)
    cam.data.shift_x = -lage["versatz"] * 0.5 * min(1.0, (breite / hoehe - 1) * 1.6)
    cam.data.clip_start = 20
    cam.data.clip_end = 40000
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (ziel - auge).length
    cam.data.dof.aperture_fstop = lage["blende"]
    cam.data.dof.aperture_blades = 7
    cam.data.dof.aperture_rotation = math.radians(12)


# ---------------------------------------------------------------- Zustand des Rads

T_KETTE = 640.0      # Kettenweg in mm je Einheit p bei Grundtempo 1
T_RAD = 6.0          # Sekunden je Einheit p für das Vorderrad


def kettentempo(p):
    im_antrieb = fenster(2.7, 3.0, 3.75, 3.95, p)
    im_rad = fenster(4.75, 5.0, 5.8, 5.95, p)
    return 0.1 + 0.9 * im_antrieb + 0.4 * im_rad


def gang_bei(p):
    k = int(math.floor(p))
    f = p - k
    if p < 3.0:
        return 0.0
    if k == 3:
        g = klemm((f - 0.05) / 0.55, 0.0, 1.0) * 11
        stufe = math.floor(g)
        return min(11.0, stufe + glatt(0.65, 1.0, g - stufe))
    return lerp(11.0, 6.0, glatt(3.97, 4.12, p))


def omega_vorn_ziel(p):
    k = int(math.floor(p))
    f = p - k
    if k == 4:
        return lerp(26.0, 0.0, glatt(0.18, 0.5, f))
    if k > 4:
        return 0.0
    return 1.2


class Integrale:
    """Kettenweg, Kurbel-, Hinterrad- und Vorderradwinkel als Integral über p (fein abgetastet)."""

    def __init__(self, antrieb, schritte=8192):
        self.n = schritte
        self.dp = KAPITEL / schritte
        self.s = [0.0]
        self.wk = [0.0]
        self.wh = [0.0]
        self.wv = [0.0]
        self.om = [1.2]
        om = 1.2
        for i in range(schritte):
            p = i * self.dp
            ds = kettentempo(p) * T_KETTE * self.dp
            g = gang_bei(p)
            self.s.append(self.s[-1] + ds)
            self.wk.append(self.wk[-1] - ds / antrieb.r_kb)
            self.wh.append(self.wh[-1] - ds / antrieb.r_ritzel(g))
            ziel = omega_vorn_ziel(p)
            k = int(math.floor(p))
            f = p - k
            rate = 2.5 if (k == 4 and f < 0.18) else 4.0
            om += (ziel - om) * min(1.0, rate * T_RAD * self.dp)
            self.om.append(om)
            self.wv.append(self.wv[-1] - om * T_RAD * self.dp)

    def bei(self, p):
        x = klemm(p / self.dp, 0, self.n)
        i = int(x)
        j = min(self.n, i + 1)
        t = x - i
        return {
            "s": lerp(self.s[i], self.s[j], t), "w_kurbel": lerp(self.wk[i], self.wk[j], t), "w_hinten": lerp(self.wh[i], self.wh[j], t),
            "w_vorn": lerp(self.wv[i], self.wv[j], t), "omega_vorn": lerp(self.om[i], self.om[j], t),
        }


def hitze_bei(p):
    k = int(math.floor(p))
    f = p - k
    return glatt(0.2, 0.52, f) * (1 - 0.75 * glatt(0.6, 1.0, f)) if k == 4 else 0.0


def anlauf_bei(p):
    if p < 3.9:
        return 0.0
    hoechst = 0.0
    q = 3.9
    while q <= min(p, 5.0):
        hoechst = max(hoechst, hitze_bei(q))
        q += 0.005
    return hoechst * 0.9


def werte_bei(p, integ):
    """Alles, was Bild und Anzeige brauchen."""
    k = min(int(math.floor(p)), KAPITEL - 1)
    f = p - k
    w = {"kapitel": k}
    w["scan"] = fenster(0.92, 1.05, 1.82, 1.97, p)
    w["scan_x"] = lerp(-520.0, 1820.0, glatt(1.05, 1.78, p))
    w["zerlegt"] = glatt(2.02, 2.55, p) * (1 - glatt(2.66, 2.98, p))
    w["gang"] = gang_bei(p)
    i = integ.bei(p)
    w.update(i)
    w["druck"] = fenster(0.16, 0.22, 0.58, 0.66, f) if k == 4 else 0.0
    w["hitze"] = hitze_bei(p)
    w["anlauf"] = anlauf_bei(p)
    w["temperatur"] = round(24 + w["hitze"] * 410)
    w["drehzahl"] = round(i["omega_vorn"] * 60 / (2 * math.pi))
    schlag = (1 - glatt(0.12, 0.66, f)) if k == 5 else (1.0 if k < 5 else 0.0)
    w["schlag_mm"] = 10 * schlag * glatt(4.6, 4.95, p)
    w["spannung"] = schlag
    w["spannung_zeigen"] = fenster(4.85, 5.05, 5.75, 5.92, p)
    w["schlag_anzeige"] = f"{3.2 * schlag + 0.15 * (1 - schlag):.1f}".replace(".", ",")
    w["spannung_anzeige"] = round(18 * schlag + 2 * (1 - schlag))
    w["akku_raus"] = glatt(0.04, 0.38, f) * (1 - glatt(0.6, 0.86, f)) if k == 6 else 0.0
    w["ende"] = glatt(6.85, 7.3, p)
    return w


# ---------------------------------------------------------------- Zerlegen

# Wege der Baugruppen beim Zerlegen (aus zerlegen.js, in Rad-Koordinaten umgerechnet: x, -z, y)
WEGE = [
    ("G:laufradV", (560, 40, -110), 0.12, 0.55),
    ("G:laufradH", (-600, -80, -110), 0.12, 0.55),
    ("T:reifen_v", (0, 110, 0), 0.5, 0.45),
    ("T:reifen_h", (0, 110, 0), 0.5, 0.45),
    ("T:bremsscheibe_v", (0, 170, 0), 0.45, 0.45),
    ("T:bremsscheibe_h", (0, 170, 0), 0.45, 0.45),
    ("G:ritzel", (0, -150, 0), 0.42, 0.45),
    ("G:vorderbau", (210, 0, 110), 0.0, 0.5),
    ("G:federung", (50, 0, -170), 0.22, 0.5),
    ("G:cockpit", (30, 0, 190), 0.3, 0.5),
    ("G:sattel", (-60, 0, 200), 0.18, 0.5),
    ("G:akku", (60, 190, -230), 0.32, 0.5),
    ("G:motor", (40, -30, -290), 0.42, 0.5),
    ("G:kurbel", (0, -230, -40), 0.28, 0.5),
    ("G:schaltwerk", (-140, -230, -110), 0.36, 0.5),
    ("G:bremseV", (0, 200, 40), 0.38, 0.45),
    ("G:bremseH", (30, 220, 60), 0.38, 0.45),
    ("T:daempfer", (0, -120, 160), 0.3, 0.5),
]


class Zustand:
    """Setzt das Rad in Blender auf den Stand von p."""

    def __init__(self, teile, gruppen, antrieb):
        self.t = teile
        self.g = gruppen
        self.antrieb = antrieb
        self.integ = Integrale(antrieb)
        self.basis_g = {n: o.location.copy() for n, o in gruppen.items()}
        self.basis_t = {n: o.location.copy() for n, o in teile.items()}
        a = teile["akku"]
        self.akku_richtung = Vector(a["richtung"])
        self.akku_quer = Vector(a["quer"])
        self.wackel = {}

    def ziel(self, schluessel):
        art, name = schluessel.split(":")
        if art == "G":
            return self.g[name], self.basis_g[name]
        return self.t[name], self.basis_t[name]

    def kette_zerlegt(self, i):
        return Vector((-250 + i * rad.TEILUNG * 0.98, -140.0, rad.TRETLAGER.z - 520))

    def setzen(self, p, licht_spot=None):
        w = werte_bei(p, self.integ)
        T, G = self.t, self.g
        # Zerlegen
        for schluessel, weg, ein, dauer in WEGE:
            obj, basis = self.ziel(schluessel)
            f = sanft(klemm((w["zerlegt"] - ein) / dauer, 0.0, 1.0))
            obj.location = basis + Vector(weg) * f
        T["leitungen"].hide_render = w["zerlegt"] > 0.04
        # Akku fällt nach unten aus dem Unterrohr und kommt zur Kamera
        if w["zerlegt"] < 0.001:
            r = w["akku_raus"]
            G["akku"].location = self.basis_g["akku"] + self.akku_quer * (110 * r) + self.akku_richtung * (30 * r) + Vector((0, -150 * r, 0))
        T["akku"]["led"] = 2.5 if w["akku_raus"] > 0.05 else 0.0
        # Antrieb und Laufräder
        self.antrieb.setzen(w["gang"], w["s"], w["w_kurbel"], w["w_hinten"], w["zerlegt"], self.kette_zerlegt)
        lv = G["laufradV"]
        lv.animation_data_clear()
        lv.rotation_euler = (0, -w["w_vorn"], 0)
        if w["omega_vorn"] > 2.0:
            # Bewegungsunschärfe wie bei 1/60 s Belichtung: Schlüssel ein Bild davor und danach
            d = w["omega_vorn"] / 60.0
            szene = lv.users_scene[0]
            f = szene.frame_current
            for df, zus in ((-1, d), (1, -d)):
                lv.rotation_euler = (0, -w["w_vorn"] + zus, 0)
                lv.keyframe_insert("rotation_euler", frame=f + df)
            for fc in lv.animation_data.action.fcurves if hasattr(lv.animation_data.action, "fcurves") else []:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
            lv.rotation_euler = (0, -w["w_vorn"], 0)
        w["bewegung"] = w["omega_vorn"] > 2.0
        # Bremse
        for name, s in (("belag_v_l", 1), ("belag_v_r", -1)):
            T[name].location = self.basis_t[name] + Vector((0, -s * 0.9 * w["druck"], 0))
        T["bremsscheibe_v"]["hitze"] = w["hitze"]
        T["bremsscheibe_v"]["anlauf"] = w["anlauf"]
        T["bremsscheibe_h"]["hitze"] = 0.0
        T["bremsscheibe_h"]["anlauf"] = 0.0
        # Laufrad hinten: Seitenschlag als Formschlüssel, Spannung als Farbe
        for name in ("felge_h", "reifen_h", "speichen_h", "felge_h_text-10.6", "felge_h_text-13.7", "felge_h_text10.6", "felge_h_text13.7"):
            o = T.get(name)
            if o is not None and o.data.shape_keys:
                o.data.shape_keys.key_blocks["Schlag"].value = w["schlag_mm"] / 10.0
        T["speichen_h"]["spannung"] = w["spannung"]
        T["speichen_h"]["spannung_zeigen"] = w["spannung_zeigen"]
        T["speichen_v"]["spannung"] = 0.0
        T["speichen_v"]["spannung_zeigen"] = 0.0
        # Licht
        T["licht_vorne"]["licht"] = 3.0 + 22.0 * w["ende"]
        T["licht_hinten"]["licht"] = 2.0 + 6.0 * w["ende"]
        if licht_spot is not None:
            licht_spot.data.energy = 4.0e6 * w["ende"]
        return w


def schlag_formschluessel(obj, mitte=(0, 0, 0)):
    """Seitenschlag der Felge: verschiebt Punkte entlang der Achse je nach Winkel (wie RADVERFORMUNG).

    mitte: Lage der Radachse in den Netzkoordinaten des Objekts."""
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis")
    sk = obj.shape_key_add(name="Schlag")
    m = Vector(mitte)
    for v, k in zip(obj.data.vertices, sk.data):
        p = v.co - m
        r = math.hypot(p.x, p.z)
        wnk = math.atan2(p.z, p.x)
        anteil = glatt(30.0, 300.0, r)
        d1 = ((wnk - 0.6 + math.pi) % (2 * math.pi)) - math.pi
        d2 = ((wnk + 2.2 + math.pi) % (2 * math.pi)) - math.pi
        beule = math.exp(-d1 * d1 * 3.2) - 0.55 * math.exp(-d2 * d2 * 5.0)
        k.co = v.co + Vector((0, 10.0 * beule * anteil, 0))
    sk.value = 0.0
    return sk


# ---------------------------------------------------------------- Befunde und Markierungen

BEFUNDE = [
    {"anker": (40, -95, 300), "titel": "Schaltwerk", "wert": "Käfig 0,8 mm verbogen", "stand": "achtung"},
    {"anker": (0, 0, 748), "titel": "Reifendruck hinten", "wert": "1,1 bar (Soll 1,6)", "stand": "fehler"},
    {"anker": (-140, -30, 250), "titel": "Speichenspannung", "wert": "± 18 % ungleich", "stand": "achtung"},
    {"anker": (235, -52, 400), "titel": "Kette", "wert": "0,6 % gelängt", "stand": "achtung"},
    {"anker": (480, -45, 300), "titel": "Motor", "wert": "keine Fehler", "stand": "ok"},
    {"anker": (720, -40, 570), "titel": "Akku", "wert": "86 % · 412 Ladezyklen", "stand": "ok"},
    {"anker": (1120, -60, 820), "titel": "Federgabel", "wert": "Service fällig (50 h)", "stand": "achtung"},
    {"anker": (1185, 52, 425), "titel": "Bremsbelag vorn", "wert": "1,2 mm Rest", "stand": "fehler"},
    {"anker": (985, 0, 1110), "titel": "Software", "wert": "4.2.1 → 4.3.0 verfügbar", "stand": "achtung"},
]

# Teile zum Antippen: Name der Markierung → Ankerpunkt am zusammengebauten Rad und Leistung aus leistungen.json
MARKIERUNGEN = {
    "bremsscheibe_v": ((1185, 52, 425), "bremsscheibe", "Bremse vorn"),
    "kette": ((240, -52, 396), "kette", "Kette"),
    "schaltwerk_kaefig": ((12, -92, 300), "schaltwerk", "Schaltwerk"),
    "akku": ((760, -40, 560), "akku", "Akku"),
    "speichen_h": ((-170, -24, 230), "speichen", "Laufrad hinten"),
    "reifen_v": ((1540, -30, 640), "reifen", "Reifen vorn"),
    "gabel": ((1150, -64, 800), "federgabel", "Federgabel"),
}

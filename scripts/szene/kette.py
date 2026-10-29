"""Kette und Schaltwerk: Kettenweg über Kettenblatt, Röllchen und Ritzel, Käfig hält die Länge.

Rechnet in der Seitenebene (x, z); quer liegt jede Kreisscheibe auf ihrer eigenen y-Lage.
Übertragung von public/assets/js/rad/kette.js der Echtzeitfassung.
"""

import math

import bpy
from mathutils import Matrix, Vector

from . import rad

TAU = math.pi * 2
SPALT = 7.0
RICHTUNG = math.radians(-100)


def teilkreis(zaehne):
    return rad.TEILUNG / (2 * math.sin(math.pi / zaehne))


def tangente(a, b):
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    k = (a["s"] * a["r"] - b["s"] * b["r"]) / d
    c = max(-1.0, min(1.0, k))
    s = math.sqrt(1 - c * c)
    mx, my = c * ux - s * uy, c * uy + s * ux
    return ((a["x"] + a["s"] * a["r"] * mx, a["y"] + a["s"] * a["r"] * my), (b["x"] + b["s"] * b["r"] * mx, b["y"] + b["s"] * b["r"] * my))


def weg(kreise):
    n = len(kreise)
    t = [tangente(kreise[i], kreise[(i + 1) % n]) for i in range(n)]
    stuecke = []
    laenge = 0.0
    for i in range(n):
        k = kreise[i]
        ein = t[(i - 1) % n][1]
        aus = t[i][0]
        w0 = math.atan2(ein[1] - k["y"], ein[0] - k["x"])
        w1 = math.atan2(aus[1] - k["y"], aus[0] - k["x"])
        dw = (w0 - w1) if k["s"] > 0 else (w1 - w0)
        dw %= TAU
        lb = dw * k["r"]
        stuecke.append(("bogen", k, w0, dw, lb, k["z"], k["z"]))
        laenge += lb
        von, nach = t[i]
        lg = math.hypot(nach[0] - von[0], nach[1] - von[1])
        stuecke.append(("gerade", von, nach, None, lg, k["z"], kreise[(i + 1) % n]["z"]))
        laenge += lg
    return stuecke, laenge


def punkt_auf(w, s):
    stuecke, laenge = w
    rest = s % laenge
    for i, st in enumerate(stuecke):
        art, a, b, c, l, z0, z1 = st
        if rest <= l or i == len(stuecke) - 1:
            f = min(1.0, rest / l) if l > 0 else 0.0
            if art == "bogen":
                k, w0, dw = a, b, c
                ang = w0 - k["s"] * dw * f
                return Vector((k["x"] + k["r"] * math.cos(ang), z0, k["y"] + k["r"] * math.sin(ang)))
            return Vector((a[0] + (b[0] - a[0]) * f, z0 + (z1 - z0) * f, a[1] + (b[1] - a[1]) * f))
        rest -= l
    return Vector((0, 0, 0))


class Antrieb:
    def __init__(self, teile, gruppen):
        self.teile = teile
        self.gruppen = gruppen
        self.zaehne = rad.KASSETTE
        self.r_kb = teilkreis(rad.KETTENBLATT_ZAEHNE)
        self.r_rolle = teilkreis(rad.SCHALTROLLE_ZAEHNE)
        self.y_kb = rad.KETTENBLATT_Y
        lmax = weg(self.kreise(len(self.zaehne) - 1, math.radians(12)))[1]
        self.glieder_n = math.ceil(lmax / rad.TEILUNG / 2) * 2
        self.laenge = self.glieder_n * rad.TEILUNG
        self.glieder = []
        sammlung = teile["rahmen"].users_collection[0]
        vorlagen = (teile["glied_aussen"], teile["glied_innen"])
        for i in range(self.glieder_n):
            v = vorlagen[i % 2]
            o = bpy.data.objects.new(f"glied{i:03d}", v.data)
            sammlung.objects.link(o)
            self.glieder.append(o)
        self.ruhe = {}

    def y_ritzel(self, g):
        return rad.KASSETTE_Y_GROSS - (len(self.zaehne) - 1 - g) * rad.KASSETTE_ABSTAND

    def r_ritzel(self, g):
        i = max(0, min(len(self.zaehne) - 1, g))
        a = int(math.floor(i))
        b = min(len(self.zaehne) - 1, a + 1)
        f = i - a
        return teilkreis(self.zaehne[a]) * (1 - f) + teilkreis(self.zaehne[b]) * f

    def rolle_oben(self, g):
        r = self.r_ritzel(g) + self.r_rolle + SPALT
        return rad.HINTEN.x + r * math.cos(RICHTUNG), rad.HINTEN.z + r * math.sin(RICHTUNG)

    def kreise(self, g, phi):
        j1 = self.rolle_oben(g)
        y = self.y_ritzel(g)
        return [
            {"x": rad.TRETLAGER.x, "y": rad.TRETLAGER.z, "r": self.r_kb, "s": 1, "z": self.y_kb},
            {"x": j1[0] + rad.KAEFIG * math.sin(phi), "y": j1[1] - rad.KAEFIG * math.cos(phi), "r": self.r_rolle, "s": 1, "z": y},
            {"x": j1[0], "y": j1[1], "r": self.r_rolle, "s": -1, "z": y},
            {"x": rad.HINTEN.x, "y": rad.HINTEN.z, "r": self.r_ritzel(g), "s": 1, "z": y},
        ]

    def kaefig_winkel(self, g):
        a, b = math.radians(-40), math.radians(120)
        for _ in range(40):
            m = (a + b) / 2
            if weg(self.kreise(g, m))[1] > self.laenge:
                a = m
            else:
                b = m
        return (a + b) / 2

    def setzen(self, gang, s, w_kurbel, w_rad, zerlegt=0.0, versatz_zerlegt=None):
        """gang: 0 … 11 (auch Zwischenwerte), s: Kettenweg in mm, Winkel in Bogenmaß."""
        G = self.gruppen
        T = self.teile
        phi = self.kaefig_winkel(gang)
        kreise = self.kreise(gang, phi)
        w = weg(kreise)
        # Kurbel und Laufrad drehen sich um die y-Achse; positiver Winkel dreht x nach z
        G["kurbel"].rotation_euler = (0, -w_kurbel, 0)
        for p in ("pedal_r", "pedal_l"):
            T[p].rotation_euler = (0, w_kurbel, 0)
        G["laufradH"].rotation_euler = (0, -w_rad, 0)
        T["rolle_oben"].rotation_euler = (0, -s / self.r_rolle, 0)
        T["rolle_unten"].rotation_euler = (0, s / self.r_rolle, 0)
        # Ritzelpaket so verdrehen, dass ein Bolzen in einer Zahnlücke liegt
        ri = int(round(gang))
        zr = self.zaehne[ri]
        s_start = sum(st[4] for st in w[0][:6])
        k_ziel = math.ceil((s_start - s) / rad.TEILUNG)
        p0 = punkt_auf(w, s + k_ziel * rad.TEILUNG)
        w_bolzen = math.atan2(p0.z - rad.HINTEN.z, p0.x - rad.HINTEN.x)
        versatz = 0.13 * (len(self.zaehne) - 1 - ri)
        luecke = w_bolzen - w_rad - versatz
        schritte = TAU / zr
        korr = luecke - round(luecke / schritte) * schritte
        G["ritzel"].rotation_euler = (0, -korr, 0)
        # Käfig: obere Rolle sitzt bei j1, Käfig um phi gedreht
        j1 = Vector((kreise[2]["x"], kreise[2]["z"], kreise[2]["y"]))
        basis = Vector(G["schaltwerk"]["welt"])
        for name in ("schaltwerk_kaefig", "rolle_oben", "rolle_unten"):
            T[name].parent = G["schaltwerk"]
        kaefig = T["schaltwerk_kaefig"]
        drehung = Matrix.Rotation(-phi, 4, "Y")
        lokal = j1 - basis
        kaefig.matrix_parent_inverse = Matrix.Identity(4)
        kaefig.matrix_basis = Matrix.Translation(lokal) @ drehung
        T["rolle_oben"].matrix_basis = Matrix.Translation(lokal) @ drehung @ Matrix.Rotation(-s / self.r_rolle, 4, "Y")
        T["rolle_unten"].matrix_basis = Matrix.Translation(lokal) @ drehung @ Matrix.Translation((0, 0, -rad.KAEFIG)) @ Matrix.Rotation(s / self.r_rolle, 4, "Y")
        # Parallelogramm: vom Halter zum Käfigkopf strecken
        halter = Vector(T["schaltwerk_halter"]["ort"])
        kopf = j1 + Vector((12, -6, 18))
        d = kopf - halter
        arm = T["schaltwerk_arm"]
        arm.parent = G["schaltwerk"]
        arm.matrix_parent_inverse = Matrix.Identity(4)
        richtung = d.normalized()
        rot = Vector((1, 0, 0)).rotation_difference(richtung).to_matrix().to_4x4()
        arm.matrix_basis = Matrix.Translation(halter - basis) @ rot @ Matrix.Diagonal((max(0.6, d.length / 80), 1, 1, 1))
        # Glieder
        for i, o in enumerate(self.glieder):
            s0 = s + i * rad.TEILUNG
            a = punkt_auf(w, s0)
            b = punkt_auf(w, s0 + rad.TEILUNG)
            if zerlegt > 0 and versatz_zerlegt is not None:
                f = max(0.0, min(1.0, zerlegt * 1.6 - (i / self.glieder_n) * 0.6))
                f = f * f * (3 - 2 * f)
                ziel = versatz_zerlegt(i)
                a = a.lerp(ziel, f)
                b = b.lerp(ziel + Vector((rad.TEILUNG, 0, 0)), f)
            d = b - a
            winkel = math.atan2(d.z, d.x)
            o.matrix_world = Matrix.Translation(a) @ Matrix.Rotation(-winkel, 4, "Y")
        return {"gang": gang, "phi": phi, "ritzel": self.zaehne[ri], "glieder": self.glieder_n}

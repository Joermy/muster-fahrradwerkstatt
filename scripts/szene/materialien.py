"""Prozedurale Cycles-Materialien für Rad und Werkstatt.

Jedes Material entsteht beim ersten Aufruf von holen(name). Farben sind linear (nicht sRGB).
Werte, die die Zeitleiste ändert (Hitze der Bremsscheibe, Speichenspannung, Scan-Linie …),
liest das Material über Attribut-Knoten aus Eigenschaften des Objekts oder der Szene.
"""

import os

import bpy

MATS = {}
DEKOR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "var", "szene", "dekor")


class Knoten:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.bsdf = self.nt.nodes.get("Principled BSDF")
        self._koord = {}

    def __call__(self, typ, **werte):
        n = self.nt.nodes.new(typ)
        for k, w in werte.items():
            if k.startswith("_"):
                setattr(n, k[1:], w)
            elif isinstance(w, bpy.types.NodeSocket):
                self.nt.links.new(w, n.inputs[k])
            else:
                n.inputs[k].default_value = w
        return n

    def link(self, a, b):
        if isinstance(a, bpy.types.NodeSocket):
            self.nt.links.new(a, b)
        elif isinstance(a, (tuple, list)):
            b.default_value = tuple(a) + ((1.0,) if len(a) == 3 and len(b.default_value) == 4 else ())
        else:
            b.default_value = a

    def setze(self, eingang, wert):
        sock = self.bsdf.inputs[eingang]
        if isinstance(wert, bpy.types.NodeSocket):
            self.link(wert, sock)
        else:
            sock.default_value = tuple(wert) + (1.0,) if isinstance(wert, (tuple, list)) and len(wert) == 3 else wert

    def koord(self, art="Object"):
        if art not in self._koord:
            self._koord[art] = self("ShaderNodeTexCoord").outputs[art]
        return self._koord[art]

    def geo(self):
        if "geo" not in self._koord:
            self._koord["geo"] = self("ShaderNodeNewGeometry")
        return self._koord["geo"]

    def attribut(self, name, art="OBJECT"):
        n = self("ShaderNodeAttribute", _attribute_type=art, _attribute_name=name)
        return n.outputs["Fac"]

    def mathe(self, op, a, b=None, c=None, klemmen=False):
        n = self("ShaderNodeMath", _operation=op, _use_clamp=klemmen)
        for i, w in enumerate((a, b, c)):
            if w is None:
                continue
            if isinstance(w, bpy.types.NodeSocket):
                self.link(w, n.inputs[i])
            else:
                n.inputs[i].default_value = w
        return n.outputs[0]

    def vek(self, op, a, b=None, skalar=None):
        n = self("ShaderNodeVectorMath", _operation=op)
        for i, w in enumerate((a, b)):
            if w is None:
                continue
            if isinstance(w, bpy.types.NodeSocket):
                self.link(w, n.inputs[i])
            else:
                n.inputs[i].default_value = w
        if skalar is not None:
            if isinstance(skalar, bpy.types.NodeSocket):
                self.link(skalar, n.inputs["Scale"])
            else:
                n.inputs["Scale"].default_value = skalar
        return n.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs["Vector"]

    def mischen(self, a, b, fak, typ="MIX", klemmen=True):
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "RGBA"
        n.blend_type = typ
        n.clamp_result = False
        n.clamp_factor = klemmen
        for i, w in ((0, fak), (6, a), (7, b)):
            sock = n.inputs[i]
            if isinstance(w, bpy.types.NodeSocket):
                self.link(w, sock)
            elif isinstance(w, (tuple, list)):
                sock.default_value = tuple(w) + ((1.0,) if len(w) == 3 else ())
            else:
                sock.default_value = w if i == 0 else (w, w, w, 1.0)
        return n.outputs[2]

    def wert_mischen(self, a, b, fak):
        n = self.nt.nodes.new("ShaderNodeMix")
        n.data_type = "FLOAT"
        n.clamp_factor = True
        for sock, w in ((n.inputs[0], fak), (n.inputs[2], a), (n.inputs[3], b)):
            if isinstance(w, bpy.types.NodeSocket):
                self.link(w, sock)
            else:
                sock.default_value = w
        return n.outputs[0]

    def rampe(self, eingang, stopps, interp="LINEAR"):
        n = self.nt.nodes.new("ShaderNodeValToRGB")
        n.color_ramp.interpolation = interp
        self.link(eingang, n.inputs[0])
        el = n.color_ramp.elements
        while len(el) > len(stopps):
            el.remove(el[-1])
        while len(el) < len(stopps):
            el.new(0.5)
        for e, (pos, farbe) in zip(el, stopps):
            e.position = pos
            e.color = tuple(farbe) + ((1.0,) if len(farbe) == 3 else ())
        return n.outputs[0]

    def bereich(self, wert, a, b, c=0.0, d=1.0, art="LINEAR"):
        n = self("ShaderNodeMapRange", _interpolation_type=art, **{"From Min": a, "From Max": b, "To Min": c, "To Max": d})
        self.link(wert, n.inputs["Value"])
        return n.outputs["Result"]

    def rauschen(self, vektor, groesse, detail=4.0, rauheit=0.55, verzerrung=0.0, dim="3D", lakun=2.0):
        n = self("ShaderNodeTexNoise", Scale=1.0 / groesse, Detail=detail, Roughness=rauheit, Distortion=verzerrung, Lacunarity=lakun, _noise_dimensions=dim)
        self.link(vektor, n.inputs["Vector"])
        return n.outputs["Fac"]

    def voronoi(self, vektor, groesse, merkmal="F1", ausgabe="Distance"):
        n = self("ShaderNodeTexVoronoi", Scale=1.0 / groesse, _feature=merkmal)
        self.link(vektor, n.inputs["Vector"])
        return n.outputs[ausgabe]

    def beule(self, hoehe, staerke, abstand=1.0, normale=None):
        n = self("ShaderNodeBump", Strength=staerke, Distance=abstand)
        self.link(hoehe, n.inputs["Height"])
        if normale is not None:
            self.link(normale, n.inputs["Normal"])
        return n.outputs["Normal"]

    def bild(self, pfad, vektor=None, farbraum="sRGB", wiederholen=False, interp="Linear"):
        img = bpy.data.images.load(pfad, check_existing=True)
        img.colorspace_settings.name = farbraum
        n = self("ShaderNodeTexImage", _interpolation=interp, _extension="REPEAT" if wiederholen else "CLIP")
        n.image = img
        if vektor is not None:
            self.link(vektor, n.inputs["Vector"])
        return n

    def ao(self, abstand, nur_lokal=True):
        n = self("ShaderNodeAmbientOcclusion", Distance=abstand, _only_local=nur_lokal, _samples=8)
        return n.outputs["AO"]

    def kante(self, radius):
        """1 an Kanten, 0 auf Flächen (aus der Krümmung des Netzes, ohne zusätzliche Strahlen)."""
        return self.bereich(self.geo().outputs["Pointiness"], 0.52, 0.6, 0.0, 1.0)


def _neu(name, farbe=(0.5, 0.5, 0.5), rauheit=0.5, metall=0.0, glanz=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = tuple(farbe) + (1,)
    b.inputs["Roughness"].default_value = rauheit
    b.inputs["Metallic"].default_value = metall
    b.inputs["Specular IOR Level"].default_value = glanz
    MATS[name] = m
    return m, Knoten(m)


def staub(k, farbe, rauheit, staerke=1.0, hoehe=(0.0, 520.0), farbe_staub=(0.24, 0.22, 0.19)):
    """Feiner Staub: unten am Rad, in Ecken und auf Flächen, die nach oben zeigen – nie fleckig."""
    welt = k.koord("Object")
    pos = k.geo().outputs["Position"]
    z = k("ShaderNodeSeparateXYZ", Vector=pos).outputs["Z"]
    unten = k.bereich(z, hoehe[1], hoehe[0], 0.0, 1.0)
    normale = k("ShaderNodeSeparateXYZ", Vector=k.geo().outputs["Normal"]).outputs["Z"]
    oben = k.bereich(normale, 0.2, 0.95, 0.0, 1.0)
    ecke = k.bereich(k.geo().outputs["Pointiness"], 0.5, 0.42, 0.0, 1.0)
    wolke = k.bereich(k.rauschen(welt, 40, 3, 0.5), 0.3, 0.7, 0.55, 1.0)
    korn = k.bereich(k.rauschen(welt, 0.8, 2, 0.5), 0.35, 0.65, 0.8, 1.0)
    maske = k.mathe("ADD", k.mathe("MULTIPLY", unten, 0.3), k.mathe("ADD", k.mathe("MULTIPLY", oben, 0.22), k.mathe("MULTIPLY", ecke, 0.45)))
    maske = k.mathe("MULTIPLY", k.mathe("MULTIPLY", maske, wolke), korn)
    maske = k.mathe("MULTIPLY", maske, 0.45 * staerke, klemmen=True)
    return k.mischen(farbe, farbe_staub, maske), k.wert_mischen(rauheit, 0.9, maske), maske


def scan(k, ausgang=None):
    """Grüne Laserlinie der Diagnose: wandert in x über das Rad (Szenen-Eigenschaft scan_x)."""
    x = k("ShaderNodeSeparateXYZ", Vector=k.geo().outputs["Position"]).outputs["X"]
    pos = k.attribut("scan_x", "VIEW_LAYER")
    an = k.attribut("scan_an", "VIEW_LAYER")
    d = k.mathe("ABSOLUTE", k.mathe("SUBTRACT", x, pos))
    linie = k.mathe("EXPONENT", k.mathe("MULTIPLY", k.mathe("MULTIPLY", d, d), -0.35))
    saum = k.mathe("EXPONENT", k.mathe("MULTIPLY", d, -0.045))
    staerke = k.mathe("MULTIPLY", k.mathe("ADD", k.mathe("MULTIPLY", linie, 140.0), k.mathe("MULTIPLY", saum, 1.2)), an)
    k.setze("Emission Color", (0.25, 1.0, 0.62))
    k.link(staerke, k.bsdf.inputs["Emission Strength"])


# ---------------------------------------------------------------- Rad


def lack():
    m, k = _neu("Lack", (0.006, 0.05, 0.052), 0.38, 0.35)
    welt = k.koord("Object")
    fein = k.rauschen(welt, 0.06, 2, 0.5)
    k.link(k.beule(fein, 0.05, 0.2), k.bsdf.inputs["Normal"])
    farbe, rau, _ = staub(k, (0.006, 0.05, 0.052), k.bereich(k.rauschen(welt, 90, 3), 0.3, 0.7, 0.33, 0.43), 0.35)
    k.link(farbe, k.bsdf.inputs["Base Color"])
    k.link(rau, k.bsdf.inputs["Roughness"])
    k.setze("Coat Weight", 0.35)
    k.setze("Coat Roughness", 0.32)
    k.setze("Specular IOR Level", 0.55)
    scan(k)
    return m


def alu_schwarz(name="Alu_schwarz", farbe=(0.018, 0.018, 0.02), rauheit=0.36, kante_hell=False, staub_staerke=0.6):
    m, k = _neu(name, farbe, rauheit, 1.0)
    welt = k.koord("Object")
    rau = k.bereich(k.rauschen(welt, 25, 3), 0.3, 0.7, rauheit - 0.06, rauheit + 0.08)
    f = farbe
    if kante_hell:
        kante = k.kante(0.6)
        f = k.mischen(farbe, (0.55, 0.56, 0.58), k.mathe("MULTIPLY", kante, k.bereich(k.rauschen(welt, 3, 3), 0.45, 0.6, 0.0, 0.9)))
    f, rau, _ = staub(k, f, rau, staub_staerke)
    k.link(f, k.bsdf.inputs["Base Color"])
    k.link(rau, k.bsdf.inputs["Roughness"])
    k.setze("Anisotropic", 0.25)
    scan(k)
    return m


def metall(name, farbe, rauheit, aniso=0.0, staub_staerke=0.0):
    m, k = _neu(name, farbe, rauheit, 1.0)
    welt = k.koord("Object")
    rau = k.bereich(k.rauschen(welt, 8, 4, 0.6), 0.3, 0.7, rauheit * 0.8, rauheit * 1.25)
    f = farbe
    if staub_staerke:
        f, rau, _ = staub(k, f, rau, staub_staerke)
    k.link(f, k.bsdf.inputs["Base Color"])
    k.link(rau, k.bsdf.inputs["Roughness"])
    if aniso:
        k.setze("Anisotropic", aniso)
    scan(k)
    return m


def kunststoff(name, farbe, rauheit=0.45, staub_staerke=0.5):
    m, k = _neu(name, farbe, rauheit, 0.0, 0.5)
    welt = k.koord("Object")
    rau = k.bereich(k.rauschen(welt, 4, 3), 0.3, 0.7, rauheit - 0.06, rauheit + 0.08)
    k.link(k.beule(k.rauschen(welt, 0.15, 2), 0.04, 0.2), k.bsdf.inputs["Normal"])
    f, rau, _ = staub(k, farbe, rau, staub_staerke)
    k.link(f, k.bsdf.inputs["Base Color"])
    k.link(rau, k.bsdf.inputs["Roughness"])
    scan(k)
    return m


def gummi(name="Gummi", farbe=(0.016, 0.016, 0.017), rauheit=0.72, staub_staerke=0.7):
    m, k = _neu(name, farbe, rauheit, 0.0, 0.35)
    welt = k.koord("Object")
    k.link(k.beule(k.rauschen(welt, 0.25, 3, 0.6), 0.08, 0.3), k.bsdf.inputs["Normal"])
    f, rau, _ = staub(k, farbe, rauheit, staub_staerke)
    k.link(f, k.bsdf.inputs["Base Color"])
    k.link(rau, k.bsdf.inputs["Roughness"])
    k.setze("Sheen Weight", 0.15)
    k.setze("Sheen Tint", (0.6, 0.6, 0.6))
    scan(k)
    return m


def reifen():
    """Reifengummi mit geprägter Flankenschrift über Polarkoordinaten im Radobjekt."""
    m, k = _neu("Reifen", (0.012, 0.012, 0.013), 0.74, 0.0, 0.28)
    lok = k.koord("Object")
    xyz = k("ShaderNodeSeparateXYZ", Vector=lok)
    r = k.vek("LENGTH", k("ShaderNodeCombineXYZ", X=xyz.outputs["X"], Y=0.0, Z=xyz.outputs["Z"]).outputs[0])
    w = k.mathe("ARCTAN2", xyz.outputs["Z"], xyz.outputs["X"])
    u = k.mathe("FRACT", k.mathe("MULTIPLY", k.mathe("ADD", w, 3.14159265), 2.0 / 6.2831853))
    v = k.bereich(r, 322.0, 352.0, 0.0, 1.0)
    uv = k("ShaderNodeCombineXYZ", X=u, Y=v, Z=0.0)
    schrift = k.bild(os.path.join(DEKOR, "reifenflanke.png"), uv.outputs[0], "Non-Color", wiederholen=False)
    seite = k.mathe("GREATER_THAN", k.mathe("ABSOLUTE", k("ShaderNodeSeparateXYZ", Vector=k.geo().outputs["Normal"]).outputs["Y"]), 0.35)
    praegung = k.mathe("MULTIPLY", schrift.outputs["Color"], seite)
    rauschen = k.rauschen(lok, 0.2, 3, 0.6)
    hoehe = k.mathe("ADD", k.mathe("MULTIPLY", praegung, 0.6), k.mathe("MULTIPLY", rauschen, 0.15))
    k.link(k.beule(hoehe, 0.5, 0.6), k.bsdf.inputs["Normal"])
    rau = k.wert_mischen(0.78, 0.55, praegung)
    farbe = k.mischen((0.014, 0.014, 0.015), (0.03, 0.03, 0.032), praegung)
    f, rau, _ = staub(k, farbe, rau, 0.8, hoehe=(0.0, 260.0))
    k.link(f, k.bsdf.inputs["Base Color"])
    k.link(rau, k.bsdf.inputs["Roughness"])
    scan(k)
    return m


def bremsscheibe():
    """Stahl mit konzentrischen Schleifspuren; Glut und Anlauffarben aus 'hitze' und 'anlauf'."""
    m, k = _neu("Bremsscheibe", (0.62, 0.62, 0.63), 0.22, 1.0)
    lok = k.koord("Object")
    xyz = k("ShaderNodeSeparateXYZ", Vector=lok)
    r = k.vek("LENGTH", k("ShaderNodeCombineXYZ", X=xyz.outputs["X"], Y=0.0, Z=xyz.outputs["Z"]).outputs[0])
    rmax = k.attribut("r_aussen")
    rel = k.mathe("DIVIDE", r, rmax)
    bahn = k.mathe("MULTIPLY", k.bereich(rel, 0.80, 0.84), k.bereich(rel, 0.995, 0.97))
    rillen = k("ShaderNodeTexWave", Scale=1.0, Distortion=2.0, Detail=2.0, **{"Detail Scale": 1.0}, _wave_type="RINGS", _rings_direction="Y")
    k.link(k.vek("SCALE", lok, None, 0.9), rillen.inputs["Vector"])
    rau = k.wert_mischen(0.28, k.bereich(rillen.outputs["Fac"], 0.0, 1.0, 0.12, 0.3), bahn)
    anlauf = k.attribut("anlauf")
    farbe_anlauf = k.rampe(rel, [(0.82, (0.62, 0.62, 0.63)), (0.88, (0.55, 0.42, 0.25)), (0.94, (0.28, 0.25, 0.45)), (0.99, (0.45, 0.5, 0.6))])
    farbe = k.mischen((0.62, 0.62, 0.63), farbe_anlauf, k.mathe("MULTIPLY", anlauf, bahn))
    farbe = k.mischen(farbe, (0.3, 0.3, 0.3), k.mathe("MULTIPLY", bahn, 0.25))
    k.setze("Anisotropic", 0.6)
    tangente = k("ShaderNodeTangent", _direction_type="RADIAL", _axis="Y")
    k.link(tangente.outputs["Tangent"], k.bsdf.inputs["Tangent"])
    hitze = k.attribut("hitze")
    w = k.mathe("ARCTAN2", xyz.outputs["Z"], xyz.outputs["X"])
    flecken = k.bereich(k.mathe("MULTIPLY", k.mathe("SINE", k.mathe("MULTIPLY", w, 9.0)), k.mathe("SINE", k.mathe("MULTIPLY", w, 4.0))), -1.0, 1.0, 0.75, 1.0)
    h = k.mathe("MULTIPLY", k.mathe("MULTIPLY", hitze, flecken), bahn, klemmen=True)
    # Kirschrot bis Orange wie Stahl bei 550–750 °C; hell genug zum Leuchten, nicht so hell, dass AgX es ausbleicht
    glut = k.rampe(h, [(0.0, (0.0, 0.0, 0.0)), (0.35, (0.4, 0.012, 0.0)), (0.75, (0.85, 0.05, 0.002)), (1.0, (1.0, 0.13, 0.008))])
    k.link(glut, k.bsdf.inputs["Emission Color"])
    k.link(k.mathe("MULTIPLY", k.mathe("POWER", h, 1.6), 1.7), k.bsdf.inputs["Emission Strength"])
    # Heißer Stahl verliert den Glanz; dunkle, matte Oberfläche lässt die Glut satt rot statt rosa erscheinen
    farbe = k.mischen(farbe, (0.03, 0.028, 0.028), k.mathe("MULTIPLY", h, 1.3, klemmen=True))
    rau = k.wert_mischen(rau, 0.55, h)
    # Innen (Arme bis zur Centerlock-Aufnahme) schwarz eloxiertes Aluminium wie bei zweiteiligen Scheiben
    innen = k.bereich(rel, 0.795, 0.775)
    farbe = k.mischen(farbe, (0.022, 0.022, 0.024), innen)
    k.link(k.wert_mischen(rau, 0.3, innen), k.bsdf.inputs["Roughness"])
    k.link(farbe, k.bsdf.inputs["Base Color"])
    return m


def speiche():
    """Schwarze Edelstahlspeiche; zeigt im Laufradkapitel die Spannung als Farbe."""
    m, k = _neu("Speiche", (0.03, 0.03, 0.032), 0.32, 1.0)
    lok = k.koord("Object")
    xyz = k("ShaderNodeSeparateXYZ", Vector=lok)
    w = k.mathe("ARCTAN2", xyz.outputs["Z"], xyz.outputs["X"])
    s = k.mathe("ADD", k.mathe("MULTIPLY", k.mathe("SINE", k.mathe("ADD", k.mathe("MULTIPLY", w, 3.0), 0.7)), 0.6), k.mathe("MULTIPLY", k.mathe("SINE", k.mathe("SUBTRACT", k.mathe("MULTIPLY", w, 7.0), 1.3)), 0.4))
    s = k.mathe("MULTIPLY", s, k.attribut("spannung"))
    farbe = k.rampe(k.bereich(s, -0.7, 0.7, 0.0, 1.0), [(0.0, (0.02, 0.22, 1.0)), (0.5, (0.05, 0.85, 0.35)), (1.0, (1.0, 0.12, 0.02))])
    zeigen = k.attribut("spannung_zeigen")
    k.link(farbe, k.bsdf.inputs["Emission Color"])
    k.link(k.mathe("MULTIPLY", zeigen, 1.4), k.bsdf.inputs["Emission Strength"])
    k.link(k.mischen((0.03, 0.03, 0.032), (0.0, 0.0, 0.0), zeigen), k.bsdf.inputs["Base Color"])
    return m


def standrohr():
    m, k = _neu("Standrohr", (0.62, 0.42, 0.17), 0.1, 1.0)
    welt = k.koord("Object")
    k.link(k.bereich(k.rauschen(welt, 20, 3), 0.3, 0.7, 0.07, 0.14), k.bsdf.inputs["Roughness"])
    k.setze("Coat Weight", 0.6)
    k.setze("Coat Roughness", 0.04)
    scan(k)
    return m


def sattel():
    m, k = _neu("Sattel", (0.018, 0.018, 0.019), 0.62, 0.0, 0.4)
    welt = k.koord("Object")
    k.link(k.beule(k.voronoi(welt, 0.6), 0.12, 0.2), k.bsdf.inputs["Normal"])
    k.setze("Sheen Weight", 0.2)
    k.setze("Sheen Roughness", 0.5)
    k.setze("Sheen Tint", (0.4, 0.4, 0.42))
    scan(k)
    return m


def griff():
    m, k = _neu("Griff", (0.02, 0.02, 0.021), 0.82, 0.0, 0.3)
    lok = k.koord("Object")
    rauten = k("ShaderNodeTexWave", Scale=1 / 3.2, Distortion=0.0, _wave_type="BANDS", _bands_direction="DIAGONAL")
    k.link(lok, rauten.inputs["Vector"])
    rauten2 = k("ShaderNodeTexWave", Scale=1 / 3.2, Distortion=0.0, _wave_type="BANDS", _bands_direction="DIAGONAL")
    k.link(k.vek("MULTIPLY", lok, (-1.0, 1.0, 1.0)), rauten2.inputs["Vector"])
    muster = k.mathe("MAXIMUM", k.bereich(rauten.outputs["Fac"], 0.75, 0.9), k.bereich(rauten2.outputs["Fac"], 0.75, 0.9))
    k.link(k.beule(muster, 0.5, 0.6), k.bsdf.inputs["Normal"])
    return m


def leuchtend(name, farbe, staerke_attr, grund=0.0, glas=True):
    """Leuchtfläche, deren Stärke eine Objekt-Eigenschaft steuert."""
    m, k = _neu(name, (0.02, 0.02, 0.02), 0.08, 0.0, 0.8)
    k.setze("Emission Color", farbe)
    staerke = k.mathe("ADD", k.attribut(staerke_attr), grund)
    k.link(staerke, k.bsdf.inputs["Emission Strength"])
    if glas:
        k.setze("Coat Weight", 1.0)
        k.setze("Coat Roughness", 0.02)
    return m


def display():
    m, k = _neu("Bildschirm", (0.0, 0.0, 0.0), 0.05, 0.0, 0.8)
    n = k("ShaderNodeTexImage", _interpolation="Cubic")
    n.name = "Inhalt"
    k.link(k.koord("UV"), n.inputs["Vector"])
    k.link(n.outputs["Color"], k.bsdf.inputs["Emission Color"])
    k.setze("Emission Strength", 1.6)
    k.setze("Coat Weight", 1.0)
    k.setze("Coat Roughness", 0.01)
    return m


def dekor(name, bild, glanz=True):
    """Aufkleber/Druck mit Transparenz aus dem PNG; liegt als dünne Haut auf dem Teil."""
    m, k = _neu(name, (1, 1, 1), 0.3 if glanz else 0.6, 0.0, 0.5)
    b = k.bild(os.path.join(DEKOR, bild), k.koord("UV"))
    k.link(b.outputs["Color"], k.bsdf.inputs["Base Color"])
    k.link(b.outputs["Alpha"], k.bsdf.inputs["Alpha"])
    if glanz:
        k.setze("Coat Weight", 0.6)
        k.setze("Coat Roughness", 0.08)
    return m


# ---------------------------------------------------------------- Werkstatt


def beton():
    m, k = _neu("Beton", (0.25, 0.25, 0.25), 0.45, 0.0, 0.5)
    p = k.koord("Object")
    gross = k.rauschen(p, 1800, 3, 0.5)
    mittel = k.rauschen(p, 260, 6, 0.6, verzerrung=0.6)
    kelle = k.rauschen(p, 700, 2, 0.4, verzerrung=4.0)
    fein = k.rauschen(p, 3.0, 2, 0.7)
    loch = k.mathe("LESS_THAN", k.voronoi(p, 9.0), 0.07)
    basis = k.rampe(gross, [(0.25, (0.20, 0.205, 0.205)), (0.75, (0.30, 0.30, 0.295))])
    farbe = k.mischen(basis, k.rampe(mittel, [(0.3, (0.17, 0.17, 0.17)), (0.7, (0.33, 0.33, 0.32))]), 0.35)
    farbe = k.mischen(farbe, k.rampe(kelle, [(0.4, (0.22, 0.22, 0.22)), (0.6, (0.31, 0.31, 0.30))]), 0.25)
    farbe = k.mischen(farbe, k.rampe(fein, [(0.35, (0.8, 0.8, 0.8)), (0.65, (1.15, 1.15, 1.15))]), 1.0, "MULTIPLY")
    farbe = k.mischen(farbe, (0.09, 0.09, 0.09), k.mathe("MULTIPLY", loch, 0.6))
    xyz = k("ShaderNodeSeparateXYZ", Vector=p)
    fugen = None
    for achse, versatz in (("X", 2700.0), ("Y", 4600.0)):
        v = k.mathe("ADD", xyz.outputs[achse], versatz)
        rest = k.mathe("FLOORED_MODULO", v, 3000.0)
        abst = k.mathe("MINIMUM", rest, k.mathe("SUBTRACT", 3000.0, rest))
        f = k.mathe("LESS_THAN", abst, 2.5)
        fugen = f if fugen is None else k.mathe("MAXIMUM", fugen, f)
    farbe = k.mischen(farbe, (0.06, 0.06, 0.06), k.mathe("MULTIPLY", fugen, 0.85))
    oel = k.bereich(k.rauschen(p, 420, 3, 0.5, verzerrung=1.5), 0.62, 0.72)
    vorn = k.bereich(xyz.outputs["Y"], 600.0, 1700.0)
    farbe = k.mischen(farbe, k.mischen(farbe, (0.5, 0.48, 0.45), 1.0, "MULTIPLY"), k.mathe("MULTIPLY", oel, vorn))
    spur = k.mathe("MULTIPLY", k.bereich(k.rauschen(k.vek("MULTIPLY", p, (1.0, 0.04, 1.0)), 30, 2), 0.55, 0.7), k.bereich(k.rauschen(p, 600, 2), 0.5, 0.6))
    farbe = k.mischen(farbe, k.mischen(farbe, (0.6, 0.6, 0.6), 1.0, "MULTIPLY"), k.mathe("MULTIPLY", spur, 0.6))
    k.link(farbe, k.bsdf.inputs["Base Color"])
    rau = k.bereich(mittel, 0.3, 0.7, 0.28, 0.55)
    rau = k.wert_mischen(rau, 0.18, k.mathe("MULTIPLY", oel, vorn))
    k.link(rau, k.bsdf.inputs["Roughness"])
    hoehe = k.mathe("ADD", k.mathe("MULTIPLY", fein, 0.4), k.mathe("MULTIPLY", loch, -0.6))
    k.link(k.beule(k.mathe("SUBTRACT", hoehe, k.mathe("MULTIPLY", fugen, 3.0)), 0.25, 1.0), k.bsdf.inputs["Normal"])
    return m


def ziegel():
    m, k = _neu("Ziegel_weiss", (0.74, 0.735, 0.71), 0.85, 0.0, 0.3)
    p = k.koord("Object")
    xyz = k("ShaderNodeSeparateXYZ", Vector=p)
    u = k.mathe("ADD", xyz.outputs["X"], xyz.outputs["Y"])
    uv = k("ShaderNodeCombineXYZ", X=u, Y=xyz.outputs["Z"], Z=0.0)
    b = k("ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 9.0, "Mortar Smooth": 0.4, "Brick Width": 250.0, "Row Height": 124.0, "Bias": 0.0}, _offset=0.5, _squash=1.0)
    k.link(uv.outputs[0], b.inputs["Vector"])
    b.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1)
    b.inputs["Color2"].default_value = (0.94, 0.94, 0.93, 1)
    b.inputs["Mortar"].default_value = (0.86, 0.86, 0.85, 1)
    flecken = k.rauschen(p, 900, 3, 0.5)
    struktur = k.rauschen(p, 6, 3, 0.7)
    basis = k.mischen((0.74, 0.735, 0.71), k.rampe(flecken, [(0.3, (0.92, 0.92, 0.91)), (0.7, (1.04, 1.04, 1.03))]), 1.0, "MULTIPLY")
    basis = k.mischen(basis, b.outputs["Color"], 1.0, "MULTIPLY")
    basis = k.mischen(basis, k.rampe(struktur, [(0.3, (0.93, 0.93, 0.93)), (0.7, (1.03, 1.03, 1.03))]), 1.0, "MULTIPLY")
    schmutz = k.mathe("MULTIPLY", k.bereich(xyz.outputs["Z"], 300.0, -274.0, 0.0, 0.35), k.rauschen(p, 120, 4))
    basis = k.mischen(basis, (0.35, 0.33, 0.3), schmutz)
    k.link(basis, k.bsdf.inputs["Base Color"])
    hoehe = k.mathe("ADD", k.mathe("MULTIPLY", b.outputs["Fac"], -2.5), k.mathe("MULTIPLY", struktur, 0.6))
    k.link(k.beule(hoehe, 0.6, 1.0), k.bsdf.inputs["Normal"])
    return m


def putz(name, farbe, rauheit=0.85):
    m, k = _neu(name, farbe, rauheit, 0.0, 0.3)
    p = k.koord("Object")
    flecken = k.rauschen(p, 700, 3, 0.5)
    struktur = k.rauschen(p, 2.5, 4, 0.7)
    k.link(k.mischen(tuple(farbe), k.rampe(flecken, [(0.3, (0.94, 0.94, 0.94)), (0.7, (1.03, 1.03, 1.03))]), 1.0, "MULTIPLY"), k.bsdf.inputs["Base Color"])
    k.link(k.beule(struktur, 0.15, 1.0), k.bsdf.inputs["Normal"])
    return m


def birke():
    m, k = _neu("Birke", (0.56, 0.43, 0.29), 0.6, 0.0, 0.4)
    p = k.koord("Object")
    xyz = k("ShaderNodeSeparateXYZ", Vector=p)
    gestreckt = k("ShaderNodeCombineXYZ", X=k.mathe("MULTIPLY", xyz.outputs["X"], 0.08), Y=k.mathe("MULTIPLY", xyz.outputs["Y"], 0.08), Z=xyz.outputs["Z"]).outputs[0]
    maser = k.rauschen(gestreckt, 14, 5, 0.6, verzerrung=1.2)
    wellen = k("ShaderNodeTexWave", Scale=1 / 30.0, Distortion=6.0, Detail=3.0, **{"Detail Scale": 1.5}, _wave_type="BANDS", _bands_direction="Z")
    k.link(gestreckt, wellen.inputs["Vector"])
    flecken = k.rauschen(p, 500, 3, 0.5)
    basis = k.rampe(maser, [(0.3, (0.50, 0.38, 0.25)), (0.7, (0.64, 0.50, 0.34))])
    basis = k.mischen(basis, k.rampe(wellen.outputs["Fac"], [(0.2, (0.86, 0.84, 0.82)), (0.8, (1.04, 1.04, 1.04))]), 1.0, "MULTIPLY")
    basis = k.mischen(basis, k.rampe(flecken, [(0.3, (0.9, 0.9, 0.9)), (0.7, (1.05, 1.05, 1.05))]), 1.0, "MULTIPLY")
    k.link(basis, k.bsdf.inputs["Base Color"])
    return m


def eiche():
    m, k = _neu("Eiche", (0.36, 0.24, 0.14), 0.45, 0.0, 0.45)
    p = k.koord("Object")
    xyz = k("ShaderNodeSeparateXYZ", Vector=p)
    lamelle = k.mathe("FLOOR", k.mathe("DIVIDE", xyz.outputs["Y"], 42.0))
    zufall = k("ShaderNodeTexWhiteNoise", _noise_dimensions="1D", W=lamelle)
    gestreckt = k("ShaderNodeCombineXYZ", X=k.mathe("MULTIPLY", xyz.outputs["X"], 0.06), Y=xyz.outputs["Y"], Z=k.mathe("ADD", xyz.outputs["Z"], k.mathe("MULTIPLY", lamelle, 37.0))).outputs[0]
    maser = k.rauschen(gestreckt, 5, 6, 0.65, verzerrung=1.5)
    basis = k.rampe(maser, [(0.25, (0.24, 0.15, 0.08)), (0.75, (0.44, 0.30, 0.17))])
    basis = k.mischen(basis, k.rampe(zufall.outputs["Value"], [(0.0, (0.82, 0.8, 0.78)), (1.0, (1.1, 1.08, 1.04))]), 1.0, "MULTIPLY")
    fuge = k.mathe("LESS_THAN", k.mathe("FLOORED_MODULO", xyz.outputs["Y"], 42.0), 0.7)
    basis = k.mischen(basis, (0.1, 0.07, 0.04), k.mathe("MULTIPLY", fuge, 0.5))
    gebrauch = k.bereich(k.rauschen(p, 200, 4, 0.6), 0.55, 0.75, 0.0, 0.5)
    basis = k.mischen(basis, (0.12, 0.09, 0.06), gebrauch)
    k.link(basis, k.bsdf.inputs["Base Color"])
    k.link(k.bereich(k.rauschen(p, 60, 3), 0.3, 0.7, 0.32, 0.6), k.bsdf.inputs["Roughness"])
    return m


def pulver(name, farbe, rauheit=0.55):
    m, k = _neu(name, farbe, rauheit, 0.0, 0.5)
    p = k.koord("Object")
    k.link(k.beule(k.rauschen(p, 1.2, 2, 0.5), 0.08, 1.0), k.bsdf.inputs["Normal"])
    k.link(k.bereich(k.rauschen(p, 300, 3, 0.5), 0.3, 0.7, rauheit - 0.12, rauheit + 0.12), k.bsdf.inputs["Roughness"])
    k.link(tuple(farbe), k.bsdf.inputs["Base Color"])
    return m


def karton():
    m, k = _neu("Karton", (0.40, 0.27, 0.15), 0.85, 0.0, 0.2)
    p = k.koord("Object")
    k.link(k.mischen((0.40, 0.27, 0.15), k.rampe(k.rauschen(p, 60, 4, 0.6), [(0.3, (0.85, 0.85, 0.85)), (0.7, (1.08, 1.08, 1.08))]), 1.0, "MULTIPLY"), k.bsdf.inputs["Base Color"])
    return m


def leuchte(name, farbe, staerke):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = tuple(farbe) + (1,)
    e.inputs["Strength"].default_value = staerke
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    MATS[name] = m
    return m


def fensterglas():
    m = bpy.data.materials.new("Fensterglas")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    t = nt.nodes.new("ShaderNodeBsdfTransparent")
    t.inputs["Color"].default_value = (0.93, 0.96, 0.96, 1)
    g = nt.nodes.new("ShaderNodeBsdfGlossy")
    g.inputs["Roughness"].default_value = 0.02
    f = nt.nodes.new("ShaderNodeFresnel")
    f.inputs["IOR"].default_value = 1.5
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(f.outputs[0], mix.inputs[0])
    nt.links.new(t.outputs[0], mix.inputs[1])
    nt.links.new(g.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    MATS["Fensterglas"] = m
    return m


def einfach(name, farbe, rauheit=0.5, metall_=0.0, glanz=0.5):
    m, _ = _neu(name, farbe, rauheit, metall_, glanz)
    return m


DEFINITIONEN = {
    # Rad
    "Lack": lack,
    "Alu_schwarz": alu_schwarz,
    "Alu_schwarz_glatt": lambda: alu_schwarz("Alu_schwarz_glatt", (0.02, 0.02, 0.022), 0.28, kante_hell=False, staub_staerke=0.3),
    "Alu_roh": lambda: metall("Alu_roh", (0.6, 0.61, 0.62), 0.3, 0.4),
    "Stahl": lambda: metall("Stahl", (0.62, 0.62, 0.63), 0.2),
    "Stahl_dunkel": lambda: metall("Stahl_dunkel", (0.12, 0.12, 0.13), 0.3, staub_staerke=0.4),
    "Kette": lambda: metall("Kette", (0.2, 0.2, 0.205), 0.34, staub_staerke=0.6),
    "Kassette": lambda: metall("Kassette", (0.55, 0.55, 0.56), 0.18, 0.3),
    "Kassette_dunkel": lambda: metall("Kassette_dunkel", (0.05, 0.05, 0.055), 0.25, 0.3),
    "Kettenblatt": lambda: alu_schwarz("Kettenblatt", (0.015, 0.015, 0.016), 0.34),
    "Gummi": gummi,
    "Reifen": reifen,
    "Griff": griff,
    "Kunststoff": lambda: kunststoff("Kunststoff", (0.018, 0.018, 0.019)),
    "Kunststoff_glanz": lambda: kunststoff("Kunststoff_glanz", (0.012, 0.012, 0.013), 0.12, 0.2),
    "Motor": lambda: kunststoff("Motor", (0.02, 0.021, 0.023), 0.5, 0.9),
    "Akku_innen": lambda: kunststoff("Akku_innen", (0.015, 0.015, 0.016), 0.4, 0.0),
    "Bremsscheibe": bremsscheibe,
    "Bremssattel": lambda: alu_schwarz("Bremssattel", (0.02, 0.02, 0.022), 0.32),
    "Belag": lambda: kunststoff("Belag", (0.12, 0.1, 0.09), 0.9, 0.0),
    "Standrohr": standrohr,
    "Tauchrohr": lambda: kunststoff("Tauchrohr", (0.012, 0.012, 0.013), 0.4, 1.0),
    "Daempfer": lambda: alu_schwarz("Daempfer", (0.02, 0.02, 0.022), 0.3),
    "Kolbenstange": lambda: metall("Kolbenstange", (0.75, 0.75, 0.76), 0.06),
    "Felge": lambda: alu_schwarz("Felge", (0.016, 0.016, 0.017), 0.45, kante_hell=False, staub_staerke=1.0),
    "Speiche": speiche,
    "Nippel": lambda: metall("Nippel", (0.6, 0.6, 0.62), 0.25),
    "Nabe": lambda: alu_schwarz("Nabe", (0.02, 0.02, 0.022), 0.3),
    "Sattel": sattel,
    "Bildschirm": display,
    "Licht": lambda: leuchtend("Licht", (1.0, 0.95, 0.88), "licht", 0.0),
    "Ruecklicht": lambda: leuchtend("Ruecklicht", (1.0, 0.05, 0.02), "licht", 0.4),
    "LED": lambda: leuchtend("LED", (0.25, 1.0, 0.5), "led", 0.0, glas=False),
    "Leitung": lambda: kunststoff("Leitung", (0.012, 0.012, 0.013), 0.25, 0.4),
    "Staender": lambda: pulver("Staender", (0.022, 0.024, 0.026), 0.5),
    "Staender_Stahl": lambda: metall("Staender_Stahl", (0.65, 0.66, 0.67), 0.25, 0.5),
    # Werkstatt
    "Beton": beton,
    "Ziegel_weiss": ziegel,
    "Putz": lambda: putz("Putz", (0.70, 0.69, 0.66)),
    "Decke": lambda: putz("Decke", (0.055, 0.058, 0.06), 0.9),
    "Sockel": lambda: putz("Sockel", (0.012, 0.075, 0.078), 0.75),
    "Birke": birke,
    "Eiche": eiche,
    "Anthrazit": lambda: pulver("Anthrazit", (0.032, 0.036, 0.04), 0.5),
    "Schwarz_matt": lambda: pulver("Schwarz_matt", (0.018, 0.018, 0.019), 0.6),
    "Petrol": lambda: pulver("Petrol", (0.012, 0.11, 0.115), 0.45),
    "Verzinkt": lambda: einfach("Verzinkt", (0.55, 0.56, 0.57), 0.45, 0.85),
    "Alu": lambda: einfach("Alu", (0.62, 0.63, 0.64), 0.35, 0.9),
    "Chrom": lambda: einfach("Chrom", (0.7, 0.7, 0.72), 0.15, 1.0),
    "Gummimatte": lambda: putz("Gummimatte", (0.025, 0.025, 0.027), 0.9),
    "Griff_rot": lambda: einfach("Griff_rot", (0.42, 0.045, 0.03), 0.45),
    "Griff_gelb": lambda: einfach("Griff_gelb", (0.6, 0.38, 0.03), 0.45),
    "Griff_blau": lambda: einfach("Griff_blau", (0.03, 0.12, 0.28), 0.45),
    "Karton": karton,
    "Papier": lambda: putz("Papier", (0.78, 0.78, 0.76), 0.9),
    "Tafel": lambda: putz("Tafel", (0.05, 0.06, 0.06), 0.85),
    "Fensterglas": fensterglas,
    "LED_band": lambda: leuchte("LED_band", (1.0, 0.93, 0.84), 28.0),
    "LED_warm": lambda: leuchte("LED_warm", (1.0, 0.82, 0.62), 60.0),
    "Aussen": lambda: leuchte("Aussen", (0.82, 0.9, 1.0), 3.0),
    "Laptop_schirm": lambda: leuchte("Laptop_schirm", (0.55, 0.7, 0.75), 1.2),
    "Asphalt": lambda: putz("Asphalt", (0.12, 0.12, 0.12), 0.8),
    "Fassade": lambda: putz("Fassade", (0.62, 0.6, 0.56), 0.85),
    "Fenster_dunkel": lambda: einfach("Fenster_dunkel", (0.16, 0.18, 0.2), 0.1, 0.0, 0.8),
    "Rinde": lambda: putz("Rinde", (0.08, 0.06, 0.045), 0.9),
    "Laub": lambda: putz("Laub", (0.06, 0.12, 0.03), 0.8),
}


def holen(name):
    if name in MATS:
        return MATS[name]
    if name not in DEFINITIONEN:
        raise KeyError(f"Material {name} ist nicht definiert")
    m = DEFINITIONEN[name]()
    m.name = name
    MATS[name] = m
    return m


def zuruecksetzen():
    MATS.clear()

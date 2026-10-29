#!/usr/bin/env python3
"""Rendert die Bildfolge der Startseite mit Cycles.

    python scripts/rendern.py --probe                  ein Bild je Kapitel (Schlüsselbilder)
    python scripts/rendern.py --probe 0 3.4 4.3        bestimmte Stellen p
    python scripts/rendern.py                          die ganze Folge, fortsetzbar
    python scripts/rendern.py --von 64 --bis 128       ein Ausschnitt

Optionen: --breite=1600 --proben=128 --schnell (Vorschauqualität), --nur-lagen (nichts rendern, nur lagen.json)
Ausgabe: var/szene/bilder/bild_0000.png …, var/szene/lagen.json (Bildschirmlage von Befunden und Markierungen)
"""

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Mit "blender -b -P skript.py -- …" stehen die eigenen Argumente hinter "--"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from szene import dekor, kette, materialien, rad, regie, werkstatt
from szene.werkzeug import leeren, verlinken

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAR = os.path.join(WURZEL, "var", "szene")
BILDER = os.path.join(VAR, "bilder")
PROBEN = os.path.join(VAR, "proben")
DISPLAY = os.path.join(VAR, "display")


def option(name, standard):
    for a in ARGS:
        if a.startswith(f"--{name}="):
            return type(standard)(a.split("=", 1)[1])
    return standard


def display_inhalt(w, antrieb):
    k = w["kapitel"]
    g = int(round(w["gang"]))
    ritzel = antrieb.zaehne[g]
    if k == 1:
        return "Diagnose", None, "", [("Fehlerspeicher wird gelesen", None), ("Software 4.2.1", False), ("Motor: keine Fehler", True)]
    if k == 2:
        return "Service", None, "", [("Antrieb aus", None)]
    if k == 3:
        ueb = f"{rad.KETTENBLATT_ZAEHNE / ritzel:.2f}".replace(".", ",")
        return f"Gang {g + 1}", str(round(62 + (g + 1) * 0.6)), "U/min", [(f"Übersetzung {ueb}", None)]
    if k == 4:
        return "Bremstest", str(round(w["drehzahl"] * 0.135 * 2.5)), "km/h", [(f"Scheibe {w['temperatur']} °C", w["temperatur"] < 200)]
    if k == 5:
        return "Laufrad", None, "", [(f"Seitenschlag {w['schlag_anzeige']} mm", w["schlag_mm"] < 0.5), (f"Spannung ± {w['spannung_anzeige']} %", w["spannung_anzeige"] < 5)]
    if k == 6:
        return "Akku", None, "", [("Kapazität 86 %", True), ("412 Ladezyklen", None), ("Software 4.3.0", True)]
    if k == 7:
        return "Fertig", "0", "km/h", [("Gute Fahrt!", True)]
    return "Bereit", "0", "km/h", [("Unterstützung: Tour", None)]


class Szene:
    def __init__(self, breite, hoehe, proben, schnell=False):
        dekor.alle()
        self.s = leeren()
        materialien.zuruecksetzen()
        t0 = time.time()
        self.werkstatt = werkstatt.bauen(self.s)
        self.teile, self.gruppen, self.wurzel = rad.bauen()
        self.antrieb = kette.Antrieb(self.teile, self.gruppen)
        for name in ("felge_h", "reifen_h", "speichen_h"):
            regie.schlag_formschluessel(self.teile[name])
        for name in [n for n in self.teile if n.startswith("felge_h_text")]:
            regie.schlag_formschluessel(self.teile[name], rad.HINTEN)
        self.zustand = regie.Zustand(self.teile, self.gruppen, self.antrieb)
        print("Szene gebaut in", round(time.time() - t0, 1), "s")
        # Scheinwerferkegel für die Übergabe
        spot = bpy.data.lights.new("Scheinwerfer", "SPOT")
        spot.spot_size = math.radians(26)
        spot.spot_blend = 0.6
        spot.color = (1.0, 0.95, 0.86)
        spot.shadow_soft_size = 8
        self.spot = verlinken(bpy.data.objects.new("Scheinwerfer", spot))
        cockpit = self.gruppen["cockpit"]
        self.spot.parent = cockpit
        self.spot.location = rad.LENKERMITTE + Vector((22 + 16, 0, -44)) - Vector(cockpit["welt"])
        self.spot.rotation_euler = (0, math.radians(-78), 0)
        self.cam = verlinken(bpy.data.objects.new("Kamera", bpy.data.cameras.new("Kamera")))
        self.s.camera = self.cam
        self.display = materialien.holen("Bildschirm").node_tree.nodes["Inhalt"]
        self.display_cache = {}
        self.einstellen(breite, hoehe, proben, schnell)

    def einstellen(self, breite, hoehe, proben, schnell):
        s = self.s
        self.breite, self.hoehe = breite, hoehe
        s.render.engine = "CYCLES"
        c = s.cycles
        c.device = "CPU"
        c.samples = proben
        c.use_adaptive_sampling = True
        c.adaptive_threshold = 0.03 if schnell else 0.022
        c.adaptive_min_samples = 12 if schnell else 20
        c.use_denoising = True
        c.denoiser = "OPENIMAGEDENOISE"
        c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        c.denoising_prefilter = "ACCURATE"
        c.max_bounces = 6
        c.diffuse_bounces = 3
        c.glossy_bounces = 3
        c.transmission_bounces = 4
        c.transparent_max_bounces = 4
        c.caustics_reflective = False
        c.caustics_refractive = False
        c.sample_clamp_indirect = 6.0
        c.use_light_tree = True
        c.seed = 7
        c.use_animated_seed = False
        c.use_guiding = False
        s.render.use_persistent_data = True
        s.frame_set(100)
        s.render.motion_blur_shutter = 1.0
        s.render.motion_blur_position = "CENTER"
        s.render.resolution_x = breite
        s.render.resolution_y = hoehe
        s.render.resolution_percentage = 100
        s.render.film_transparent = False
        s.render.filter_size = 1.2
        s.view_settings.view_transform = "AgX"
        s.view_settings.look = "AgX - Medium High Contrast"
        s.view_settings.exposure = 0.0
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "8"
        s.render.image_settings.compression = 30

    def display_bild(self, w):
        inhalt = display_inhalt(w, self.antrieb)
        schluessel = json.dumps(inhalt, ensure_ascii=False)
        if schluessel not in self.display_cache:
            os.makedirs(DISPLAY, exist_ok=True)
            datei = os.path.join(DISPLAY, f"d{len(self.display_cache):03d}.png")
            kopf, gross, einheit, zeilen = inhalt
            akku = 0.86
            dekor.displayinhalt(datei, kopf, gross, einheit, zeilen, akku)
            self.display_cache[schluessel] = bpy.data.images.load(datei)
        self.display.image = self.display_cache[schluessel]

    def setzen(self, p):
        w = self.zustand.setzen(p, self.spot)
        self.s.render.use_motion_blur = w.get("bewegung", False)
        vl = bpy.context.view_layer
        vl["scan_x"] = w["scan_x"]
        vl["scan_an"] = w["scan"]
        self.display_bild(w)
        lage = regie.kamera_bei(p)
        regie.kamera_setzen(self.cam, lage, self.breite, self.hoehe)
        bpy.context.view_layer.update()
        return w, lage

    def lagen(self, lage=None):
        """Bildschirmlage (0 … 1, oben links) von Befunden, Markierungen und Bildschwerpunkt im aktuellen Bild."""
        s, cam = self.s, self.cam
        aus = {"b": [], "t": {}}
        if lage is not None:
            v = world_to_camera_view(s, cam, lage["ziel"])
            aus["f"] = [round(v.x, 4), round(1 - v.y, 4)]
        for b in regie.BEFUNDE:
            v = world_to_camera_view(s, cam, Vector(b["anker"]))
            aus["b"].append([round(v.x, 4), round(1 - v.y, 4), v.z > 0])
        for name, (anker, _, _) in regie.MARKIERUNGEN.items():
            v = world_to_camera_view(s, cam, Vector(anker))
            aus["t"][name] = [round(v.x, 4), round(1 - v.y, 4), v.z > 0]
        return aus

    def rendern(self, datei):
        self.s.render.filepath = datei
        bpy.ops.render.render(write_still=True)


def main():
    probe = "--probe" in ARGS
    nur_lagen = "--nur-lagen" in ARGS
    schnell = "--schnell" in ARGS
    breite = option("breite", 1600)
    hoehe = int(round(breite * 9 / 16))
    proben = option("proben", 32 if schnell else 48)
    sz = Szene(breite, hoehe, proben, schnell)
    if probe:
        stellen = [float(a) for a in ARGS if not a.startswith("--")] or [k + 0.3 for k in range(regie.KAPITEL)]
        os.makedirs(PROBEN, exist_ok=True)
        for p in stellen:
            w, lage = sz.setzen(p)
            t0 = time.time()
            sz.rendern(os.path.join(PROBEN, f"probe_{p:05.2f}{'_schnell' if schnell else ''}.png"))
            print(f"p={p:.2f} {lage['name']} gerendert in {time.time() - t0:.1f} s", flush=True)
        return
    gesamt = regie.KAPITEL * regie.BILDER_JE_KAPITEL  # letztes Bild = Ende des letzten Kapitels
    von = option("von", 0)
    bis = option("bis", gesamt)
    os.makedirs(BILDER, exist_ok=True)
    lagen_datei = os.path.join(VAR, "lagen-web.json" if nur_lagen else "lagen.json")
    lagen = {} if nur_lagen else (json.load(open(lagen_datei)) if os.path.exists(lagen_datei) else {})
    # Grob zu fein: erst jedes 8. Bild, dann jedes 4., 2., dann der Rest – früh eine vollständige Vorschau
    alle = [i for i in range(von, min(bis, gesamt) + 1)]
    reihenfolge = []
    for schritt in (8, 4, 2, 1):
        for i in alle:
            if i % schritt == 0 and i not in reihenfolge:
                reihenfolge.append(i)
    for i in reihenfolge:
        p = min(i / regie.BILDER_JE_KAPITEL, regie.KAPITEL - 0.001)
        datei = os.path.join(BILDER, f"bild_{i:04d}.png")
        w, lage = sz.setzen(p)
        lagen[str(i)] = sz.lagen(lage)
        if os.path.exists(datei) or nur_lagen:
            continue
        t0 = time.time()
        sz.rendern(datei + ".tmp.png")
        os.replace(datei + ".tmp.png", datei)
        with open(lagen_datei, "w") as f:
            json.dump(lagen, f)
        print(f"Bild {i}/{gesamt} (p={p:.3f}, {lage['name']}) in {time.time() - t0:.1f} s", flush=True)
    with open(lagen_datei, "w") as f:
        json.dump(lagen, f)


if __name__ == "__main__":
    main()

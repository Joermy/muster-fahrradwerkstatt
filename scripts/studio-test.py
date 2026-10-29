#!/usr/bin/env python3
"""Probebilder des Rads im neutralen Studio: python scripts/studio-test.py [ansicht …]"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Mit "blender -b -P skript.py -- …" stehen die eigenen Argumente hinter "--"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]

import bpy
from mathutils import Vector

from szene import dekor, kette, materialien, rad
from szene.werkzeug import leeren, verlinken

ZIEL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "var", "szene", "studio")

ANSICHTEN = {
    "seite": ((640, -3600, 520), (640, 0, 470), 24),
    "dreiviertel": ((2700, -2700, 1100), (620, 0, 430), 26),
    "hinten": ((-1700, -1500, 900), (300, 0, 420), 26),
    "antrieb": ((180, -900, 520), (230, 0, 360), 32),
    "cockpit": ((1500, -700, 1400), (960, 0, 1060), 34),
    "front": ((1700, -500, 700), (1200, 0, 560), 34),
    "links": ((640, 3600, 520), (640, 0, 470), 24),
    "krone": ((1900, -420, 1150), (985, 0, 900), 20),
    "bremse": ((1420, 560, 540), (1190, 52, 420), 29),
    "sattel": ((1240, 400, 560), (1183, 51, 424), 20),
}


def studio(s):
    w = bpy.data.worlds.new("Studio")
    s.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.62, 0.65, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    boden = verlinken(bpy.data.objects.new("Boden", bpy.data.meshes.new("Boden")))
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=12000)
    bm.to_mesh(boden.data)
    bm.free()
    boden.location = (600, 0, rad.BODEN)
    m = bpy.data.materials.new("Hohlkehle")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.18, 0.18, 0.19, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    boden.data.materials.append(m)
    for name, ort, staerke, groesse in (("Haupt", (900, -1600, 2600), 2.2e8, 1800), ("Kante", (-1400, 1800, 1700), 1.2e8, 1400), ("Fuell", (2600, -2200, 600), 0.8e8, 2000)):
        l = verlinken(bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")))
        l.data.energy = staerke
        l.data.size = groesse
        l.location = ort
        l.rotation_euler = (Vector((600, 0, 450)) - Vector(ort)).to_track_quat("-Z", "Y").to_euler()


def kamera(s, ansicht):
    auge, ziel, fov = ANSICHTEN[ansicht]
    cam = s.camera or verlinken(bpy.data.objects.new("Kamera", bpy.data.cameras.new("Kamera")))
    s.camera = cam
    cam.location = auge
    cam.rotation_euler = (Vector(ziel) - Vector(auge)).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle = math.radians(fov)
    cam.data.clip_start = 20
    cam.data.clip_end = 50000


def main():
    ansichten = [a for a in ARGS if not a.startswith("--")] or ["seite", "dreiviertel"]
    proben, hitze = 32, 0.0
    for a in ARGS:
        if a.startswith("--proben="):
            proben = int(a.split("=")[1])
        if a.startswith("--hitze="):
            hitze = float(a.split("=")[1])
    dekor.alle()
    s = leeren()
    materialien.zuruecksetzen()
    t0 = time.time()
    teile, gruppen, wurzel = rad.bauen()
    print("Rad gebaut in", round(time.time() - t0, 1), "s;", sum(len(o.data.polygons) for o in teile.values() if o.type == "MESH"), "Flächen")
    antrieb = kette.Antrieb(teile, gruppen)
    print(antrieb.setzen(6, 0.0, 0.0, 0.0))
    teile["bremsscheibe_v"]["hitze"] = hitze
    teile["bremsscheibe_v"]["anlauf"] = hitze * 0.9
    bild = os.path.join(dekor.ZIEL, "display-test.png")
    dekor.displayinhalt(bild, "Bereit", "0", "km/h", [("Unterstützung: Tour", None)])
    materialien.holen("Bildschirm").node_tree.nodes["Inhalt"].image = bpy.data.images.load(bild)
    bpy.context.view_layer["scan_x"] = -1e5
    bpy.context.view_layer["scan_an"] = 0.0
    studio(s)
    s.render.engine = "CYCLES"
    s.cycles.samples = proben
    s.cycles.use_denoising = True
    s.cycles.max_bounces = 6
    s.render.resolution_x = 1280
    s.render.resolution_y = 720
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    os.makedirs(ZIEL, exist_ok=True)
    for a in ansichten:
        kamera(s, a)
        s.render.filepath = os.path.join(ZIEL, f"{a}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print("gerendert", a, round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()

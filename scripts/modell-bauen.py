#!/usr/bin/env python3

import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(WURZEL, "var", "rad-roh.glb")
MASSE = os.path.join(WURZEL, "public", "assets", "js", "rad", "masse.json")

TAU = math.pi * 2
TEILUNG = 12.7


R_RAD = 358.0
HINTEN = Vector((0, 0, R_RAD))
VORN = Vector((1150, 0, R_RAD))
TRETLAGER = Vector((455, 0, 288))

SITZWINKEL = math.radians(73.5)
S_RICHTUNG = Vector((-math.cos(SITZWINKEL), 0, math.sin(SITZWINKEL)))
SITZROHR_OBEN = TRETLAGER + S_RICHTUNG * 500

LENKWINKEL = math.radians(69.5)
U = Vector((-math.cos(LENKWINKEL), 0, math.sin(LENKWINKEL)))
N = Vector((math.sin(LENKWINKEL), 0, math.cos(LENKWINKEL)))
GABEL_VERSATZ = 47.0
EINBAUHOEHE = 505.0
ACHSE_AUF_LENKACHSE = VORN - N * GABEL_VERSATZ
KRONE = ACHSE_AUF_LENKACHSE + U * EINBAUHOEHE
STEUERROHR_UNTEN = KRONE + U * 12
STEUERROHR_OBEN = STEUERROHR_UNTEN + U * 165
VORBAU = STEUERROHR_OBEN + U * 45
VORBAU_RICHTUNG = (N * math.cos(math.radians(10)) + U * math.sin(math.radians(10))).normalized()
LENKERMITTE = VORBAU + VORBAU_RICHTUNG * 85

KETTENBLATT_Y = -57.0
KETTENBLATT_ZAEHNE = 38
KASSETTE = [10, 12, 14, 16, 18, 21, 24, 28, 33, 39, 45, 51]
KASSETTE_Y_GROSS = -34.0
KASSETTE_ABSTAND = 3.9
SCHALTROLLE_ZAEHNE = 12
KURBEL = 165.0

MATERIALIEN = {}
GRUNDFARBEN = {
    "Rahmenlack": (0.02, 0.23, 0.24, 1),
    "Rahmen_matt": (0.03, 0.035, 0.04, 1),
    "Alu_schwarz": (0.03, 0.03, 0.035, 1),
    "Alu_blank": (0.8, 0.8, 0.82, 1),
    "Stahl": (0.75, 0.75, 0.76, 1),
    "Stahl_dunkel": (0.25, 0.25, 0.27, 1),
    "Kette": (0.55, 0.55, 0.57, 1),
    "Kassette": (0.7, 0.7, 0.72, 1),
    "Kettenblatt": (0.04, 0.04, 0.045, 1),
    "Gummi": (0.02, 0.02, 0.02, 1),
    "Gummi_Flanke": (0.05, 0.04, 0.035, 1),
    "Griff": (0.03, 0.03, 0.03, 1),
    "Kunststoff": (0.05, 0.05, 0.055, 1),
    "Motor": (0.08, 0.085, 0.09, 1),
    "Akku": (0.025, 0.027, 0.03, 1),
    "Bremsscheibe": (0.78, 0.78, 0.8, 1),
    "Bremssattel": (0.6, 0.32, 0.12, 1),
    "Belag": (0.25, 0.22, 0.2, 1),
    "Standrohr": (0.78, 0.6, 0.3, 1),
    "Tauchrohr": (0.04, 0.04, 0.045, 1),
    "Felge": (0.05, 0.05, 0.055, 1),
    "Speiche": (0.7, 0.7, 0.72, 1),
    "Nippel": (0.75, 0.62, 0.35, 1),
    "Nabe": (0.06, 0.06, 0.065, 1),
    "Sattel": (0.04, 0.035, 0.03, 1),
    "Display": (0.01, 0.01, 0.012, 1),
    "Bildschirm": (0.02, 0.03, 0.03, 1),
    "Licht": (1, 0.98, 0.92, 1),
    "Ruecklicht": (0.9, 0.05, 0.03, 1),
    "Leitung": (0.02, 0.02, 0.022, 1),
    "LED": (0.2, 0.9, 0.5, 1),
    "Staender": (0.75, 0.12, 0.05, 1),
    "Staender_Stahl": (0.55, 0.56, 0.58, 1),
    "Aufkleber": (0.9, 0.9, 0.88, 1),
}


def leeren():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    szene = bpy.context.scene
    szene.unit_settings.system = "METRIC"
    szene.unit_settings.scale_length = 0.001
    return szene


def material(name):
    if name in MATERIALIEN:
        return MATERIALIEN[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = GRUNDFARBEN.get(name, (0.8, 0.8, 0.8, 1))
        metall = name in ("Alu_blank", "Stahl", "Stahl_dunkel", "Kette", "Kassette", "Bremsscheibe", "Standrohr", "Speiche", "Nippel", "Staender_Stahl", "Bremssattel")
        bsdf.inputs["Metallic"].default_value = 1.0 if metall else 0.0
        bsdf.inputs["Roughness"].default_value = 0.35
    MATERIALIEN[name] = m
    return m


def verlinken(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def netz(name, punkte, flaechen, mat, uvs=None, glatt=True, winkel=40):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in punkte], [], flaechen)
    if uvs is not None:
        lage = me.uv_layers.new(name="UVMap")
        i = 0
        for f, uv in zip(me.polygons, uvs):
            for k in range(f.loop_total):
                lage.data[f.loop_start + k].uv = uv[k]
            i += 1
    me.validate(clean_customdata=False)
    me.update()
    obj = bpy.data.objects.new(name, me)
    verlinken(obj)
    me.materials.append(material(mat))
    if glatt:
        glaetten(obj, winkel)
    return obj


def glaetten(obj, winkel=40):
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.set_sharp_from_angle(angle=math.radians(winkel))


def auswerten(obj, name=None):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    neu = bpy.data.objects.new(name or obj.name, me)
    neu.matrix_world = obj.matrix_world.copy()
    verlinken(neu)
    alt = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if isinstance(alt, bpy.types.Curve):
        bpy.data.curves.remove(alt)
    elif isinstance(alt, bpy.types.Mesh) and alt.users == 0:
        bpy.data.meshes.remove(alt)
    if name:
        neu.name = name
    return neu


def backen(obj):
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    return obj


def fasen(obj, breite, segmente=2, winkel=35):
    mod = obj.modifiers.new("Fase", "BEVEL")
    mod.width = breite
    mod.segments = segmente
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(winkel)
    mod.miter_outer = "MITER_ARC"
    return auswerten(obj, obj.name)


def unterteilen(obj, stufen=2):
    mod = obj.modifiers.new("Glatt", "SUBSURF")
    mod.levels = stufen
    mod.render_levels = stufen
    return auswerten(obj, obj.name)


def verbinden(name, objekte):
    objekte = [o for o in objekte if o]
    ziel = objekte[0]
    with bpy.context.temp_override(active_object=ziel, selected_editable_objects=objekte, object=ziel):
        bpy.ops.object.join()
    ziel.name = name
    ziel.data.name = name
    return ziel


def drehpunkt(obj, punkt):
    p = Vector(punkt)
    obj.data.transform(Matrix.Translation(-p + obj.matrix_world.translation))
    obj.matrix_world = Matrix.Translation(p)
    return obj


def zusatz(obj, **werte):
    for k, w in werte.items():
        obj[k] = json.dumps(w) if isinstance(w, (list, dict)) else w
    return obj


def verschieben(obj, d):
    obj.data.transform(Matrix.Translation(Vector(d)))
    return obj


def drehen(obj, winkel, achse, um=(0, 0, 0)):
    m = Matrix.Translation(Vector(um)) @ Matrix.Rotation(winkel, 4, achse) @ Matrix.Translation(-Vector(um))
    obj.data.transform(m)
    return obj


def spline(punkte, schritt=6.0):
    p = [Vector(x) for x in punkte]
    if len(p) == 2:
        laenge = (p[1] - p[0]).length
        n = max(2, int(laenge / schritt) + 1)
        return [p[0].lerp(p[1], i / (n - 1)) for i in range(n)]
    p = [p[0] * 2 - p[1]] + p + [p[-1] * 2 - p[-2]]
    dicht = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        t0 = 0.0
        t1 = t0 + max((p1 - p0).length ** 0.5, 1e-4)
        t2 = t1 + max((p2 - p1).length ** 0.5, 1e-4)
        t3 = t2 + max((p3 - p2).length ** 0.5, 1e-4)
        n = max(2, int((p2 - p1).length / 2) + 1)
        for k in range(n):
            if k == n - 1 and i < len(p) - 3:
                continue
            t = t1 + (t2 - t1) * k / (n - 1)
            a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
            a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
            a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
            b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
            b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
            dicht.append(b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1)))
    laengen = [0.0]
    for i in range(1, len(dicht)):
        laengen.append(laengen[-1] + (dicht[i] - dicht[i - 1]).length)
    gesamt = laengen[-1]
    n = max(2, int(gesamt / schritt) + 1)
    aus = []
    j = 0
    for k in range(n):
        s = gesamt * k / (n - 1)
        while j < len(laengen) - 2 and laengen[j + 1] < s:
            j += 1
        seg = max(laengen[j + 1] - laengen[j], 1e-9)
        aus.append(dicht[j].lerp(dicht[j + 1], (s - laengen[j]) / seg))
    return aus


def rohr(name, punkte, profil, mat, um=32, schritt=6.0, kappen=(True, True), seite=Vector((0, 1, 0)), uv_laenge=None):
    pfad = spline(punkte, schritt)
    n = len(pfad)
    laengen = [0.0]
    for i in range(1, n):
        laengen.append(laengen[-1] + (pfad[i] - pfad[i - 1]).length)
    gesamt = laengen[-1]
    tang = []
    for i in range(n):
        d = pfad[min(i + 1, n - 1)] - pfad[max(i - 1, 0)]
        tang.append(d.normalized())
    b = seite - tang[0] * seite.dot(tang[0])
    if b.length < 1e-4:
        b = Vector((0, 0, 1)) - tang[0] * tang[0].z
    b.normalize()
    rahmen = []
    for i in range(n):
        if i > 0:
            b = b - tang[i] * b.dot(tang[i])
            b.normalize()
        a = b.cross(tang[i]).normalized()
        rahmen.append((a, b))
    punkte_aus = []
    flaechen = []
    uvs = []
    for i in range(n):
        t = laengen[i] / gesamt if gesamt > 0 else 0
        q = profil(t)
        ra, rb, e = q[0], q[1], q[2]
        dz = q[3] if len(q) > 3 else 0.0
        a, bb = rahmen[i]
        for k in range(um):
            w = TAU * k / um
            c, s = math.cos(w), math.sin(w)
            x = ra * math.copysign(abs(c) ** (2 / e), c)
            y = rb * math.copysign(abs(s) ** (2 / e), s)
            punkte_aus.append(pfad[i] + a * (x + dz) + bb * y)
    ul = uv_laenge or gesamt
    for i in range(n - 1):
        for k in range(um):
            k2 = (k + 1) % um
            flaechen.append((i * um + k, i * um + k2, (i + 1) * um + k2, (i + 1) * um + k))
            u0, u1 = laengen[i] / ul, laengen[i + 1] / ul
            uvs.append([(u0, k / um), (u0, (k + 1) / um), (u1, (k + 1) / um), (u1, k / um)])
    if kappen[0]:
        mitte = len(punkte_aus)
        punkte_aus.append(pfad[0] + rahmen[0][0] * (profil(0)[3] if len(profil(0)) > 3 else 0))
        for k in range(um):
            flaechen.append((mitte, (k + 1) % um, k))
            uvs.append([(0.5, 0.5), (0.5, 0.5), (0.5, 0.5)])
    if kappen[1]:
        mitte = len(punkte_aus)
        q = profil(1)
        punkte_aus.append(pfad[-1] + rahmen[-1][0] * (q[3] if len(q) > 3 else 0))
        o = (n - 1) * um
        for k in range(um):
            flaechen.append((mitte, o + k, o + (k + 1) % um))
            uvs.append([(0.5, 0.5), (0.5, 0.5), (0.5, 0.5)])
    return netz(name, punkte_aus, flaechen, mat, uvs)


def zylinder(name, a, b, r, mat, um=24, kappen=True):
    return rohr(name, [a, b], lambda t: (r, r, 2), mat, um=um, schritt=max((Vector(b) - Vector(a)).length, 1), kappen=(kappen, kappen))


def drehteil(name, profil, mat, segmente=96, mitte=(0, 0, 0), achse="Y", geschlossen=True, winkel=40):
    rmax = max(r for r, _ in profil) or 1
    m = len(profil)
    punkte = []
    for k in range(segmente):
        w = TAU * k / segmente
        c, s = math.cos(w), math.sin(w)
        for r, y in profil:
            punkte.append(Vector((r * c, y, r * s)))
    flaechen = []
    uvs = []
    kanten = m if geschlossen else m - 1
    for k in range(segmente):
        k2 = (k + 1) % segmente
        for i in range(kanten):
            i2 = (i + 1) % m
            a, b, c, d = k * m + i, k * m + i2, k2 * m + i2, k2 * m + i
            if profil[i][0] < 1e-6 and profil[i2][0] < 1e-6:
                continue
            flaechen.append((a, b, c, d))
            uvs.append([(profil[i][0] / rmax, k / segmente), (profil[i2][0] / rmax, k / segmente), (profil[i2][0] / rmax, (k + 1) / segmente), (profil[i][0] / rmax, (k + 1) / segmente)])
    obj = netz(name, punkte, flaechen, mat, uvs, True, winkel)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    glaetten(obj, winkel)
    if achse == "X":
        drehen(obj, math.pi / 2, "Z")
    elif achse == "Z":
        drehen(obj, -math.pi / 2, "X")
    verschieben(obj, mitte)
    return obj


def umriss(name, umrisse, dicke, mat, fase=0.0, aufloesung=1, y=0.0, radial_uv=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = max(dicke / 2 - fase, 0.0001)
    cu.bevel_depth = fase
    cu.bevel_resolution = aufloesung
    cu.offset = -fase
    for u in umrisse:
        sp = cu.splines.new("POLY")
        sp.points.add(len(u) - 1)
        for i, (x, z) in enumerate(u):
            sp.points[i].co = (x, z, 0, 1)
        sp.use_cyclic_u = True
    obj = bpy.data.objects.new(name, cu)
    verlinken(obj)
    cu.materials.append(material(mat))
    obj = auswerten(obj, name)
    obj.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bm.to_mesh(obj.data)
    bm.free()
    verschieben(obj, (0, y, 0))
    if radial_uv is not None:
        radiale_uv(obj, radial_uv)
    glaetten(obj, 35)
    return obj


def radiale_uv(obj, rmax, mitte=(0, 0)):
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    lage = me.uv_layers[0]
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            dx, dz = p.x - mitte[0], p.z - mitte[1]
            lage.data[li].uv = (math.hypot(dx, dz) / rmax, (math.atan2(dz, dx) / TAU) % 1.0)


def kasten(name, mitte, groesse, mat, fase=0.0, segmente=3):
    sx, sy, sz = (g / 2 for g in groesse)
    p = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz), (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = netz(name, [Vector(q) + Vector(mitte) for q in p], f, mat, glatt=False)
    if fase > 0:
        obj = fasen(obj, fase, segmente, 30)
        glaetten(obj, 35)
    return obj


def kreis(r, n, start=0.0, mitte=(0, 0)):
    return [(mitte[0] + r * math.cos(start + TAU * i / n), mitte[1] + r * math.sin(start + TAU * i / n)) for i in range(n)]


def teilkreis(zaehne):
    return TEILUNG / (2 * math.sin(math.pi / zaehne))


def zahnkranz_umriss(zaehne, versatz=0.0, proben=16):
    rp = teilkreis(zaehne)
    rolle = 4.05
    r_kopf = (TEILUNG * (0.6 + 1 / math.tan(math.pi / zaehne))) / 2 - 0.4
    schritt = TAU / zaehne
    aus = []
    for k in range(zaehne):
        for j in range(proben):
            d = (j / proben - 0.5) * schritt
            bog = rp * abs(d)
            if bog < rolle * 0.98:
                r = rp - math.sqrt(rolle * rolle - bog * bog)
            else:
                f = min(1.0, (abs(d) - rolle / rp) / (schritt / 2 - rolle / rp))
                r = rp + (r_kopf - rp) * (1 - (1 - f) ** 1.6) + 0.0
                if f > 0.92:
                    r = r_kopf
            w = versatz + k * schritt + d
            aus.append((r * math.cos(w), r * math.sin(w)))
    return aus


def rahmen():
    teile = []
    dz_unter = TRETLAGER + Vector((105, 0, 62))
    dt_oben = STEUERROHR_UNTEN + U * 28
    teile.append(rohr("Unterrohr", [dt_oben, dt_oben.lerp(dz_unter, 0.5) + Vector((0, 0, -6)), dz_unter],
                      lambda t: (37 - 3 * t, 40, 3.0), "Rahmenlack", um=40))
    tt_vorn = STEUERROHR_UNTEN + U * 128
    tt_hinten = SITZROHR_OBEN - S_RICHTUNG * 55
    teile.append(rohr("Oberrohr", [tt_vorn, tt_vorn.lerp(tt_hinten, 0.5) + Vector((0, 0, 14)), tt_hinten],
                      lambda t: (19 - 4 * t, 21 - 5 * t, 2.6), "Rahmenlack"))
    teile.append(rohr("Sitzrohr", [TRETLAGER + S_RICHTUNG * 70 + Vector((10, 0, 0)), TRETLAGER + S_RICHTUNG * 260, SITZROHR_OBEN],
                      lambda t: (21 - 4.5 * t, 20 - 3.5 * t, 2.4), "Rahmenlack"))
    teile.append(rohr("Steuerrohr", [STEUERROHR_UNTEN - U * 2, STEUERROHR_OBEN + U * 2], lambda t: (28 - 4 * t, 28 - 4 * t, 2.0), "Rahmenlack", um=48))
    teile.append(rohr("Klemme", [SITZROHR_OBEN - S_RICHTUNG * 14, SITZROHR_OBEN + S_RICHTUNG * 6], lambda t: (19, 19, 2.0), "Alu_schwarz", um=32))
    for seite in (1, -1):
        oben = SITZROHR_OBEN - S_RICHTUNG * 95 + Vector((0, 14 * seite, 0))
        unten = HINTEN + Vector((8, 66 * seite, 22))
        teile.append(rohr(f"Sitzstrebe{seite}", [oben, oben.lerp(unten, 0.45) + Vector((0, 26 * seite, 0)), unten],
                          lambda t: (8.5 - 1.5 * t, 7.5, 2.3), "Rahmenlack"))
        k_vorn = TRETLAGER + Vector((-62, 30 * seite, 2))
        k_hinten = HINTEN + Vector((14, 66 * seite, -6))
        mitte = k_vorn.lerp(k_hinten, 0.4) + Vector((0, 22 * seite, -10 if seite < 0 else -4))
        teile.append(rohr(f"Kettenstrebe{seite}", [k_vorn, mitte, k_hinten],
                          lambda t: (12 - 3 * t, 9.5 - 2 * t, 2.6), "Rahmenlack"))
        aussen = [(x, z) for x, z in kreis(17, 28)]
        aus = umriss(f"Ausfallende{seite}", [aussen, kreis(6.5, 18)], 7, "Alu_schwarz", fase=0.8, y=0)
        verschieben(aus, (HINTEN.x + 2, 69 * seite, HINTEN.z))
        teile.append(aus)
    mx, mz = 6.0, 6.0
    innen = [(mx + 67 * math.cos(math.radians(w)), mz + 67 * math.sin(math.radians(w))) for w in range(168, 8, -8)]
    aussen = []
    for w in range(10, 170, 8):
        r = 92 + 18 * math.sin(math.radians(w)) ** 2
        aussen.append((mx + 18 + r * math.cos(math.radians(w)) * (1.18 if w < 90 else 1.0), mz + r * math.sin(math.radians(w))))
    sichel = aussen + innen
    for seite, y, dicke in ((1, 53.5, 7.0), (-1, -50.0, 5.0)):
        p = umriss(f"Aufnahme{seite}", [sichel], dicke, "Rahmenlack", fase=2.0, aufloesung=2, y=0)
        verschieben(p, (TRETLAGER.x, y, TRETLAGER.z))
        teile.append(p)
    auge = umriss("Schaltauge", [[(-4, -8), (14, -8), (10, -46), (-8, -52), (-14, -30)]], 4.5, "Alu_schwarz", fase=0.6, y=0)
    verschieben(auge, (HINTEN.x, -75, HINTEN.z))
    teile.append(auge)
    for t in (0.35, 0.55):
        q = SITZROHR_OBEN.lerp(TRETLAGER, t) + N * 0
        teile.append(zylinder(f"Gewinde{t}", q + Vector((14, 0, 0)), q + Vector((24, 0, 0)), 3.2, "Alu_schwarz", 12))
    port = STEUERROHR_UNTEN + U * 70 + N * 30
    teile.append(rohr("Leitungseinlass", [port - N * 6, port + N * 4], lambda t: (6, 9, 2.2), "Kunststoff", um=20))
    r = verbinden("rahmen", teile)
    drehpunkt(r, TRETLAGER)
    return r


def akku():
    oben = STEUERROHR_UNTEN + U * 28
    unten = TRETLAGER + Vector((105, 0, 62))
    a = oben.lerp(unten, 0.09)
    b = oben.lerp(unten, 0.93)
    richtung = (b - a).normalized()
    quer = Vector((0, 1, 0)).cross(richtung).normalized()
    if quer.z > 0:
        quer = -quer
    koerper = rohr("Akku", [a + quer * 26, (a + b) / 2 + quer * 25 + Vector((0, 0, -6)), b + quer * 26],
                   lambda t: (24, 35, 3.4), "Akku", um=40)
    leds = []
    for i in range(5):
        p = a.lerp(b, 0.62 + i * 0.035) + quer * 30 + Vector((0, 34.6, 0))
        leds.append(zylinder(f"LED{i}", p - Vector((0, 0.6, 0)), p + Vector((0, 0.9, 0)), 2.2, "LED", 12))
    taste = a.lerp(b, 0.58) + quer * 30 + Vector((0, 34.4, 0))
    leds.append(zylinder("Taste", taste - Vector((0, 0.5, 0)), taste + Vector((0, 1.4, 0)), 4.2, "Kunststoff", 16))
    schloss = a.lerp(b, 0.12) + quer * 30 + Vector((0, 34.2, 0))
    leds.append(zylinder("Schloss", schloss - Vector((0, 0.5, 0)), schloss + Vector((0, 2.2, 0)), 6.0, "Alu_blank", 20))
    obj = verbinden("akku", [koerper] + leds)
    drehpunkt(obj, (a + b) / 2)
    return zusatz(obj, richtung=[richtung.x, richtung.y, richtung.z], quer=[quer.x, quer.y, quer.z])


def motor():
    teile = []
    gehaeuse = kasten("Motorgehaeuse", (TRETLAGER.x + 38, 0, TRETLAGER.z + 22), (190, 96, 150), "Motor", fase=26, segmente=5)
    teile.append(gehaeuse)
    for seite in (1, -1):
        deckel = drehteil(f"Motordeckel{seite}", [(0, 0), (60, 0), (63, 2.0 * seite), (58, 4.2 * seite), (0, 4.2 * seite)], "Alu_schwarz", 72,
                          mitte=(TRETLAGER.x + 6, 47.5 * seite, TRETLAGER.z + 6))
        teile.append(deckel)
        ring = drehteil(f"Motorring{seite}", [(40, 0), (44, 0), (44, 1.4 * seite), (40, 1.4 * seite)], "Alu_blank", 72,
                        mitte=(TRETLAGER.x + 6, 51.6 * seite, TRETLAGER.z + 6))
        teile.append(ring)
    for i in range(7):
        x = TRETLAGER.x - 30 + i * 13
        teile.append(kasten(f"Rippe{i}", (x, 0, TRETLAGER.z - 55), (5, 76, 8), "Motor", fase=1.5, segmente=2))
    obj = verbinden("motor", teile)
    return drehpunkt(obj, TRETLAGER)


def gabel():
    teile = []
    abstand = 57.0
    kopf = VORN + U * EINBAUHOEHE
    standrohr_unten = VORN + U * 205
    for seite in (1, -1):
        y = Vector((0, abstand * seite, 0))
        teile.append(zylinder(f"Standrohr{seite}", kopf + y + U * 6, standrohr_unten + y, 17, "Standrohr", 40))
        teile.append(rohr(f"Kopf{seite}", [kopf + y - U * 12, kopf + y + U * 16], lambda t: (21.5, 21.5, 2), "Alu_schwarz", um=40))
    brucke = rohr("Bruecke", [kopf + Vector((0, -abstand, 0)) + U * 6, KRONE + U * 8 + N * 4, kopf + Vector((0, abstand, 0)) + U * 6],
                  lambda t: (15, 21, 3.4), "Alu_schwarz", um=36, seite=N)
    teile.append(brucke)
    teile.append(rohr("Kronenblock", [KRONE - U * 6, KRONE + U * 20], lambda t: (24, 26, 3.2), "Alu_schwarz", um=36, seite=N))
    teile.append(zylinder("Schaft", KRONE, STEUERROHR_OBEN + U * 74, 14.3, "Alu_schwarz", 32))
    teile.append(drehteil("Lager_unten", [(15, 0), (29, 0), (29, 9), (24, 12), (15, 12)], "Alu_schwarz", 64))
    teile[-1].data.transform(Matrix.Translation(KRONE + U * 8) @ Matrix.Rotation(-(math.pi / 2 - LENKWINKEL), 4, "Y") @ Matrix.Rotation(-math.pi / 2, 4, "X"))
    for i, (h0, h1, r) in enumerate([(0, 8, 26), (8, 18, 21), (18, 28, 18)]):
        ring = drehteil(f"Spacer{i}", [(14.5, h0), (r, h0), (r, h1), (14.5, h1)], "Alu_schwarz", 48)
        ring.data.transform(Matrix.Translation(STEUERROHR_OBEN) @ Matrix.Rotation(-(math.pi / 2 - LENKWINKEL), 4, "Y") @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        teile.append(ring)
    obj = verbinden("gabel", teile)
    drehpunkt(obj, KRONE)

    unten = []
    for seite in (1, -1):
        y = Vector((0, abstand * seite, 0))
        start = VORN + y - U * 18
        unten.append(rohr(f"Tauchrohr{seite}", [start, start + U * 160, start + U * 330], lambda t: (22 - 1.5 * t, 22 - 1.5 * t, 2), "Tauchrohr", um=40))
        unten.append(drehteil(f"Abstreifer{seite}", [(17.2, 0), (23.2, 0), (23.2, 7), (19, 11), (17.2, 11)], "Gummi", 48))
        unten[-1].data.transform(Matrix.Translation(start + U * 330 + y * 0) @ Matrix.Rotation(-(math.pi / 2 - LENKWINKEL), 4, "Y") @ Matrix.Rotation(-math.pi / 2, 4, "X"))
        ausfall = umriss(f"Gabelende{seite}", [kreis(16, 24)], 14, "Tauchrohr", fase=2, y=0)
        verschieben(ausfall, (VORN.x, abstand * seite, VORN.z))
        unten.append(ausfall)
    b_mitte = VORN + U * 215 + N * 34
    unten.append(rohr("Bogen", [VORN + Vector((0, -abstand, 0)) + U * 185 + N * 14, b_mitte, VORN + Vector((0, abstand, 0)) + U * 185 + N * 14],
                      lambda t: (11, 16, 3), "Tauchrohr", um=28, seite=U))
    unten.append(zylinder("Steckachse", VORN + Vector((0, -66, 0)), VORN + Vector((0, 70, 0)), 7.5, "Alu_schwarz", 24))
    unten.append(rohr("Achshebel", [VORN + Vector((0, 72, 0)), VORN + Vector((-20, 76, 30)), VORN + Vector((-28, 77, 62))], lambda t: (6 - 2 * t, 4, 2.5), "Alu_schwarz", um=16))
    pm = VORN + Vector((0, abstand + 5, 0)) + U * 66 - N * 22
    unten.append(kasten("PostMount", pm, (34, 14, 74), "Tauchrohr", fase=4))
    drehen(unten[-1], -(math.pi / 2 - LENKWINKEL), "Y", pm)
    t = verbinden("gabel_unten", unten)
    drehpunkt(t, VORN)
    return obj, zusatz(t, achse=[U.x, U.y, U.z], federweg=100)


def cockpit():
    teile = {}
    vb = rohr("Vorbau", [VORBAU - VORBAU_RICHTUNG * 6, LENKERMITTE], lambda t: (17 - 2 * t, 19, 3.0), "Alu_schwarz", um=32)
    kopf = rohr("Vorbaukopf", [VORBAU - U * 22, VORBAU + U * 22], lambda t: (19, 19, 2.6), "Alu_schwarz", um=32)
    deckel = zylinder("Deckel", STEUERROHR_OBEN + U * 66, STEUERROHR_OBEN + U * 74, 17, "Alu_schwarz", 32)
    klemme = rohr("Lenkerklemme", [LENKERMITTE + Vector((0, -28, 0)), LENKERMITTE + Vector((0, 28, 0))], lambda t: (19, 19, 2.6), "Alu_schwarz", um=32, seite=Vector((1, 0, 0)))
    teile["vorbau"] = verbinden("vorbau", [vb, kopf, deckel, klemme])
    punkte = []
    for y in (-340, -300, -230, -150, -90, -40, 0, 40, 90, 150, 230, 300, 340):
        a = abs(y)
        anstieg = 0 if a < 40 else min(20, (a - 40) * 0.25)
        rueck = 0 if a < 120 else (a - 120) * math.tan(math.radians(9))
        punkte.append(LENKERMITTE + Vector((-rueck, y, anstieg)))
    teile["lenker"] = rohr("lenker", punkte, lambda t: (11.1 + 4.8 * max(0, 1 - abs(t - 0.5) * 9), 11.1 + 4.8 * max(0, 1 - abs(t - 0.5) * 9), 2), "Alu_schwarz", um=28, seite=Vector((0, 0, 1)))
    griffe = []
    for seite in (1, -1):
        ende = punkte[-1] if seite > 0 else punkte[0]
        innen = punkte[-3] if seite > 0 else punkte[2]
        d = (ende - innen).normalized()
        start = ende - d * 132
        griffe.append(rohr(f"Griff{seite}", [start, ende + d * 2], lambda t: (16.5 + (3.5 if t > 0.7 else 0) * min(1, (t - 0.7) * 8), 16.5, 2.3), "Griff", um=32, seite=Vector((0, 0, 1))))
        griffe.append(rohr(f"Ring{seite}", [start - d * 10, start], lambda t: (17, 17, 2), "Alu_schwarz", um=24, seite=Vector((0, 0, 1))))
    teile["griffe"] = verbinden("griffe", griffe)
    hebel = {}
    for seite in (1, -1):
        y = 255 * seite
        p = LENKERMITTE + Vector((-(255 - 120) * math.tan(math.radians(9)), y, 13))
        geber = rohr(f"Geber{seite}", [p + Vector((0, -12 * seite, 0)), p + Vector((0, 26 * seite, 0))], lambda t: (12, 14, 2.6), "Alu_schwarz", um=24, seite=Vector((1, 0, 0)))
        ausgleich = kasten(f"Behaelter{seite}", p + Vector((4, 8 * seite, 16)), (28, 22, 12), "Alu_schwarz", fase=3)
        blatt = rohr(f"Hebelblatt{seite}", [p + Vector((12, 18 * seite, -2)), p + Vector((30, 52 * seite, -8)), p + Vector((34, 98 * seite, -14))],
                     lambda t: (5.5 - 1.5 * t, 3.2, 2.8), "Alu_blank", um=16, seite=Vector((0, 0, 1)))
        hebel[seite] = verbinden("bremshebel_l" if seite > 0 else "bremshebel_r", [geber, ausgleich, blatt])
        drehpunkt(hebel[seite], p + Vector((12, 18 * seite, -2)))
    teile["bremshebel_l"] = hebel[1]
    teile["bremshebel_r"] = hebel[-1]
    s = LENKERMITTE + Vector((-(205 - 120) * math.tan(math.radians(9)), -205, 4))
    schalt = [kasten("Schaltgehaeuse", s + Vector((-6, 0, -22)), (36, 26, 30), "Kunststoff", fase=6),
              rohr("Daumenhebel", [s + Vector((10, 0, -30)), s + Vector((34, 8, -42)), s + Vector((48, 22, -44))], lambda t: (6, 3, 2.6), "Alu_schwarz", um=14, seite=Vector((0, 0, 1)))]
    teile["schalthebel"] = verbinden("schalthebel", schalt)
    dmitte = LENKERMITTE + Vector((-34, 0, 34))
    halter = rohr("Displayhalter", [LENKERMITTE + Vector((-10, 0, 14)), dmitte + Vector((4, 0, -10))], lambda t: (6, 10, 2.5), "Alu_schwarz", um=16)
    gehaeuse = kasten("Displaygehaeuse", dmitte, (16, 62, 46), "Display", fase=5)
    drehen(gehaeuse, math.radians(-28), "Y", dmitte)
    teile["display"] = verbinden("display", [halter, gehaeuse])
    w, h = 27.0, 20.0
    ecken = [Vector((0, -w, -h)), Vector((0, w, -h)), Vector((0, w, h)), Vector((0, -w, h))]
    rot = Matrix.Rotation(math.radians(-28), 3, "Y")
    ecken = [dmitte + rot @ (q + Vector((-8.3, 0, 0))) for q in ecken]
    schirm = netz("bildschirm", ecken, [(0, 1, 2, 3)], "Bildschirm", [[(1, 0), (0, 0), (0, 1), (1, 1)]], glatt=False)
    teile["bildschirm"] = schirm
    lp = LENKERMITTE + Vector((24, 0, -30))
    lampe = [rohr("Lampe", [lp - Vector((26, 0, 0)), lp + Vector((10, 0, 0))], lambda t: (14 + 4 * t, 20 + 3 * t, 3.0), "Kunststoff", um=32, kappen=(True, False)),
             rohr("Lampenhalter", [lp + Vector((-10, 0, 12)), LENKERMITTE + Vector((6, 0, -6))], lambda t: (4, 8, 2.4), "Alu_schwarz", um=12)]
    teile["licht_gehaeuse"] = verbinden("licht_gehaeuse", lampe)
    linse = drehteil("licht_vorne", [(0, 0), (16, 0), (17.5, -2.2), (0, -3.5)], "Licht", 48, achse="X")
    drehen(linse, math.pi, "Z")
    verschieben(linse, lp + Vector((11, 0, 0)))
    teile["licht_vorne"] = linse
    return teile


def leitungen():
    teile = []
    links = LENKERMITTE + Vector((-(255 - 120) * math.tan(math.radians(9)), 255, 13)) + Vector((-8, 14, -6))
    rechts = LENKERMITTE + Vector((-(255 - 120) * math.tan(math.radians(9)), -255, 13)) + Vector((-8, -14, -6))
    schalt = LENKERMITTE + Vector((-12, -205, -26))
    port = STEUERROHR_UNTEN + U * 70 + N * 34
    pm = VORN + Vector((0, 64, 0)) + U * 66 - N * 22
    teile.append(rohr("Leitung_vorn", [rechts, rechts + Vector((40, 30, -60)), LENKERMITTE + Vector((70, -20, -120)), KRONE + N * 50 + Vector((0, 30, 10)),
                                       KRONE + Vector((10, 64, -60)), pm + U * 70 + Vector((-4, 6, 0)), pm + U * 30 + Vector((0, 6, 0))],
                      lambda t: (2.6, 2.6, 2), "Leitung", um=10))
    teile.append(rohr("Leitung_hinten", [links, links + Vector((40, -20, -60)), LENKERMITTE + Vector((60, 30, -110)), port + Vector((26, 10, 30)), port + Vector((6, 6, 4)), port],
                      lambda t: (2.6, 2.6, 2), "Leitung", um=10))
    teile.append(rohr("Schaltzug", [schalt, schalt + Vector((40, 10, -50)), LENKERMITTE + Vector((66, 10, -116)), port + Vector((24, -8, 26)), port + Vector((4, -6, 2)), port + Vector((-2, -4, -2))],
                      lambda t: (2.3, 2.3, 2), "Leitung", um=10))
    k = TRETLAGER + Vector((-62, 0, 2))
    sattel_h = HINTEN + Vector((54, 64, 36))
    teile.append(rohr("Leitung_strebe", [k + Vector((-40, 44, 4)), k.lerp(HINTEN, 0.5) + Vector((0, 64, 16)), sattel_h + Vector((14, 2, 4)), sattel_h],
                      lambda t: (2.6, 2.6, 2), "Leitung", um=10))
    teile.append(rohr("Zug_strebe", [k + Vector((-40, -46, -2)), k.lerp(HINTEN, 0.5) + Vector((0, -66, 6)), HINTEN + Vector((30, -80, -2)), HINTEN + Vector((-6, -96, -26)), HINTEN + Vector((-24, -92, -44))],
                      lambda t: (2.3, 2.3, 2), "Leitung", um=10))
    return verbinden("leitungen", teile)


def sattel():
    teile = []
    stuetze_oben = SITZROHR_OBEN + S_RICHTUNG * 205
    teile.append(zylinder("Stuetze", SITZROHR_OBEN - S_RICHTUNG * 90, stuetze_oben, 15.45, "Alu_schwarz", 40))
    kopf = stuetze_oben + S_RICHTUNG * 6
    teile.append(kasten("Stuetzenkopf", kopf + Vector((0, 0, 4)), (54, 22, 14), "Alu_schwarz", fase=4))
    stuetze = verbinden("sattelstuetze", teile)
    drehpunkt(stuetze, SITZROHR_OBEN)

    mitte = kopf + Vector((-6, 0, 30))
    laenge = 270

    def profil(t):
        breite = 15 + 62 * (1 - (t / 0.62)) ** 0.0 if t > 0.62 else 15 + 62 * (1 - max(0, (0.62 - t) / 0.62) ** 2.2) ** 1
        if t > 0.62:
            breite = 15 + (77 - 15) * ((1 - t) / 0.38) ** 0.8
        else:
            breite = 77 - 10 * ((0.62 - t) / 0.62) ** 3
        hoehe = 22 if t > 0.15 else 14 + 8 * (t / 0.15)
        return (hoehe, breite, 2.6, 0)

    punkte = [mitte + Vector((-laenge * 0.48, 0, 8)), mitte + Vector((-laenge * 0.2, 0, 0)), mitte + Vector((laenge * 0.2, 0, -2)), mitte + Vector((laenge * 0.52, 0, 0))]
    polster = rohr("Polster", punkte, profil, "Sattel", um=40, seite=Vector((0, 1, 0)))
    streben = []
    for seite in (1, -1):
        streben.append(rohr(f"Strebe{seite}", [mitte + Vector((-110, 34 * seite, -6)), mitte + Vector((-70, 22 * seite, -24)), mitte + Vector((40, 14 * seite, -26)), mitte + Vector((110, 6 * seite, -10))],
                            lambda t: (3.5, 3.5, 2), "Stahl_dunkel", um=12))
    s = verbinden("sattel", [polster] + streben)
    drehpunkt(s, SITZROHR_OBEN)
    return stuetze, s


def laufrad(vorn):
    mitte = VORN if vorn else HINTEN
    teile = {}
    r_bett = 311.0
    felge = drehteil("felge", [(286, 0), (290, -13.5), (304, -15.5), (311.5, -15.2), (313.5, -13.2), (309, -12.2), (309, 12.2), (313.5, 13.2), (311.5, 15.2), (304, 15.5), (290, 13.5)],
                     "Felge", 144, winkel=34)
    v = zylinder("Ventil", Vector((0, 0, 286)), Vector((0, 0, 262)), 3.0, "Alu_blank", 12)
    vk = zylinder("Ventilkappe", Vector((0, 0, 262)), Vector((0, 0, 250)), 3.6, "Kunststoff", 12)
    teile["felge"] = verbinden("felge_v" if vorn else "felge_h", [felge, v, vk])

    profil = []
    for i in range(29):
        w = math.pi * (i / 28)
        y = -24.5 * math.cos(w)
        r = r_bett + 2 + 43.5 * math.sin(w) ** 0.85
        profil.append((r, y))
    reifen = drehteil("reifen", profil, "Gummi", 180, geschlossen=False, winkel=60)
    bloecke = []
    n = 96
    for k in range(n):
        w = TAU * k / n
        for reihe, (y0, breite, hoehe, tiefe, versatz) in enumerate([(0, 9, 2.4, 7, 0.0), (-13, 7, 2.0, 6, 0.5), (13, 7, 2.0, 6, 0.5)]):
            ww = w + versatz * TAU / n
            r0 = r_bett + 2 + 43.5 * math.sin(math.acos(max(-1, min(1, -y0 / 24.5)))) ** 0.85 - 0.6
            ra, rb = r0, r0 + hoehe
            dw = tiefe / 2 / r0
            dy = breite / 2
            ecken = []
            for (aa, yy) in [(-dw, -dy), (dw, -dy * 0.7), (dw, dy * 0.7), (-dw, dy)]:
                ecken.append((ww + aa, y0 + yy))
            pk = []
            for rr in (ra, rb):
                for (aa, yy) in ecken:
                    s = 0.82 if rr == rb else 1.0
                    aa2 = ww + (aa - ww) * s
                    pk.append(Vector((rr * math.cos(aa2), yy * (0.85 if rr == rb else 1), rr * math.sin(aa2))))
            bloecke.append(pk)
    bp = []
    bf = []
    for pk in bloecke:
        o = len(bp)
        bp.extend(pk)
        bf.extend([(o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])
    stollen = netz("stollen", bp, bf, "Gummi", glatt=False)
    flanken = []
    for seite in (1, -1):
        fl = []
        for i in range(9):
            w = math.pi * (i / 28) if seite < 0 else math.pi * (1 - i / 28)
            y = -24.6 * math.cos(w)
            r = r_bett + 2 + 43.6 * math.sin(w) ** 0.85
            fl.append((r, y))
        flanken.append(drehteil(f"Flanke{seite}", fl, "Gummi_Flanke", 180, geschlossen=False, winkel=60))
    teile["reifen"] = verbinden("reifen_v" if vorn else "reifen_h", [reifen, stollen] + flanken)
    radiale_uv(teile["reifen"], 358.0)

    if vorn:
        flansch = (35.0, 35.0)
        nabe = drehteil("nabe", [(6, -55), (17, -55), (17, -46), (27, -38), (29, -35), (27, -32), (16, -26), (14, 0), (16, 26), (27, 32), (29, 35), (27, 38), (17, 46), (17, 55), (6, 55)], "Nabe", 64)
    else:
        flansch = (36.0, -24.0)
        nabe = drehteil("nabe", [(6, -78), (17, -78), (17, -70), (16, -30), (27, -26), (29, -23), (27, -20), (16, -14), (15, 0), (16, 30), (27, 33), (29, 36), (27, 39), (17, 49), (17, 72), (6, 72)], "Nabe", 64)
    teile["nabe"] = nabe

    r_loch, r_felge = 26.0, 301.5
    sp_teile = []
    nippel = []
    info = []
    for seite_i, y_fl in enumerate(flansch):
        y_rim = 2.2 if y_fl > 0 else -2.2
        for k in range(16):
            a_h = TAU * k / 16 + (TAU / 32 if seite_i else 0)
            richtung = 1 if k % 2 == 0 else -1
            a_r = a_h + richtung * 3 * TAU / 16 + (TAU / 64) * richtung
            hub = Vector((r_loch * math.cos(a_h), y_fl, r_loch * math.sin(a_h)))
            rim = Vector((r_felge * math.cos(a_r), y_rim, r_felge * math.sin(a_r)))
            sp_teile.append(zylinder(f"Sp{seite_i}_{k}", hub, rim, 1.0, "Speiche", 6, kappen=False))
            d = (rim - hub).normalized()
            nippel.append(zylinder(f"Ni{seite_i}_{k}", rim - d * 13, rim + d * 2, 1.9, "Nippel", 8))
            info.append([round(a_r, 5), seite_i])
    teile["speichen"] = verbinden("speichen_v" if vorn else "speichen_h", sp_teile + nippel)

    r_aussen = 101.5 if vorn else 90.0
    r_innen = r_aussen - 16.5
    aussen = kreis(r_aussen, 144)
    loecher = []
    for k in range(18):
        w = TAU * k / 18
        for j, rr in enumerate((r_innen + 4.5, r_innen + 9.5, r_innen + 14.0)):
            ww = w + j * TAU / 54
            loecher.append(kreis(1.6, 10, mitte=(rr * math.cos(ww), rr * math.sin(ww))))
    fenster = []
    for k in range(6):
        w0 = TAU * k / 6
        pk = []
        for j in range(10):
            t = j / 9
            pk.append(((r_innen - 1.5) * math.cos(w0 + 0.12 + t * 0.78), (r_innen - 1.5) * math.sin(w0 + 0.12 + t * 0.78)))
        for j in range(10):
            t = 1 - j / 9
            rr = 34 + 6 * t
            pk.append((rr * math.cos(w0 + 0.42 + t * 0.48), rr * math.sin(w0 + 0.42 + t * 0.48)))
        fenster.append(pk)
    nabenloch = kreis(26, 48)
    scheibe = umriss("bremsscheibe", [aussen, nabenloch] + fenster + loecher, 1.8, "Bremsscheibe", fase=0.2, aufloesung=0, y=0, radial_uv=r_aussen)
    y_scheibe = 50.0 if vorn else 55.0
    verschieben(scheibe, (0, y_scheibe, 0))
    aufnahme = drehteil("Scheibenaufnahme", [(17, y_scheibe - 4), (30, y_scheibe - 4), (30, y_scheibe - 0.9), (17, y_scheibe - 0.9)], "Alu_schwarz", 48)
    teile["bremsscheibe"] = verbinden("bremsscheibe_v" if vorn else "bremsscheibe_h", [scheibe, aufnahme])
    radiale_uv(teile["bremsscheibe"], r_aussen)

    obj_namen = {}
    for name, obj in teile.items():
        neu = name if name.endswith(("_v", "_h")) else f"{name}_{'v' if vorn else 'h'}"
        obj.name = neu
        obj.data.name = neu
        verschieben(obj, mitte)
        obj.matrix_world = Matrix.Identity(4)
        drehpunkt(obj, mitte)
        obj_namen[neu] = obj
    zusatz(obj_namen[f"speichen_{'v' if vorn else 'h'}"], speichen=info, r_felge=r_felge, r_loch=r_loch)
    zusatz(obj_namen[f"bremsscheibe_{'v' if vorn else 'h'}"], r_aussen=r_aussen, r_innen=r_innen, y=y_scheibe)
    return obj_namen


def bremssattel(vorn):
    mitte = VORN if vorn else HINTEN
    r_aussen = 101.5 if vorn else 90.0
    y_scheibe = 50.0 if vorn else 55.0
    winkel = math.radians(152) if vorn else math.radians(24)
    r_mitte = r_aussen - 8
    ort = mitte + Vector((r_mitte * math.cos(winkel), y_scheibe, r_mitte * math.sin(winkel)))
    tangente = Vector((-math.sin(winkel), 0, math.cos(winkel)))
    radial = Vector((math.cos(winkel), 0, math.sin(winkel)))
    teile = []
    for seite in (1, -1):
        haelfte = kasten(f"Sattelhaelfte{seite}", (0, 9.5 * seite, 0), (58, 14, 30), "Bremssattel", fase=5, segmente=4)
        teile.append(haelfte)
        for i in (-1, 1):
            kolben = drehteil(f"Kolbendeckel{seite}{i}", [(0, 0), (8.5, 0), (8.5, 2.2 * seite), (0, 2.2 * seite)], "Alu_blank", 24)
            verschieben(kolben, (i * 13, 16.5 * seite, 0))
            teile.append(kolben)
    bruecke = kasten("Satteldach", (0, 0, 14), (50, 34, 9), "Bremssattel", fase=3.5)
    teile.append(bruecke)
    teile.append(zylinder("Entlueftung", Vector((22, -10, 16)), Vector((24, -10, 26)), 3.2, "Alu_blank", 12))
    for i in (-1, 1):
        teile.append(zylinder(f"Bolzen{i}", Vector((i * 20, 22, 0)), Vector((i * 20, -22, 0)), 3.6, "Stahl_dunkel", 12))
    sattel_obj = verbinden("bremssattel_v" if vorn else "bremssattel_h", teile)
    belaege = []
    for seite in (1, -1):
        b = kasten(f"belag{seite}", (0, 2.8 * seite, 0), (44, 3.2, 15), "Belag", fase=1.2, segmente=2)
        rueck = kasten(f"traeger{seite}", (0, 5.0 * seite, 0), (46, 1.4, 17), "Stahl_dunkel", fase=0.4, segmente=1)
        belaege.append(verbinden(f"belag_{'v' if vorn else 'h'}_{'l' if seite > 0 else 'r'}", [b, rueck]))
    m = Matrix.Translation(ort) @ Matrix((tangente.to_4d(), Vector((0, 1, 0, 0)), radial.to_4d(), Vector((0, 0, 0, 1)))).transposed()
    m = Matrix.Translation(ort) @ Matrix(((tangente.x, 0, radial.x, 0), (0, 1, 0, 0), (tangente.z, 0, radial.z, 0), (0, 0, 0, 1)))
    for o in [sattel_obj] + belaege:
        o.data.transform(m)
        drehpunkt(o, ort)
    zusatz(sattel_obj, quer=[0, 1, 0])
    return sattel_obj, belaege


def kassette():
    teile = []
    for i, z in enumerate(KASSETTE[::-1]):
        y = KASSETTE_Y_GROSS - i * KASSETTE_ABSTAND
        rp = teilkreis(z)
        loecher = []
        r_innen = 17.0 if z < 16 else 19.5
        if z >= 24:
            for k in range(5 if z < 39 else 6):
                n = 5 if z < 39 else 6
                w0 = TAU * k / n
                pk = []
                ra, ri = rp - 9.5, max(r_innen + 7, rp * 0.42)
                for j in range(8):
                    t = j / 7
                    pk.append((ra * math.cos(w0 + 0.15 + t * (TAU / n - 0.3)), ra * math.sin(w0 + 0.15 + t * (TAU / n - 0.3))))
                for j in range(8):
                    t = 1 - j / 7
                    pk.append((ri * math.cos(w0 + 0.28 + t * (TAU / n - 0.56)), ri * math.sin(w0 + 0.28 + t * (TAU / n - 0.56))))
                loecher.append(pk)
        rad = umriss(f"Ritzel{z}", [zahnkranz_umriss(z, versatz=0.13 * i, proben=10), kreis(r_innen, 32)] + loecher, 1.85, "Kassette", fase=0.25, aufloesung=0, y=y)
        teile.append(rad)
    teile.append(drehteil("Kassettenkoerper", [(15.5, KASSETTE_Y_GROSS + 2), (21, KASSETTE_Y_GROSS + 2), (21, KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND - 2), (15.5, KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND - 2)], "Stahl_dunkel", 48))
    teile.append(drehteil("Verschlussring", [(10, KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND - 1), (17, KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND - 1), (17, KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND - 6), (10, KASSETTE_Y_GROSS - 11 * KASSETTE_ABSTAND - 6)], "Alu_schwarz", 48))
    k = verbinden("kassette", teile)
    verschieben(k, HINTEN)
    drehpunkt(k, HINTEN)
    return zusatz(k, zaehne=KASSETTE, y_gross=KASSETTE_Y_GROSS, abstand=KASSETTE_ABSTAND)


def kurbelsatz():
    teile = {}
    rp = teilkreis(KETTENBLATT_ZAEHNE)
    fenster = []
    for k in range(4):
        w0 = TAU * k / 4 + math.pi / 4
        pk = []
        ra, ri = rp - 11, 30
        for j in range(10):
            t = j / 9
            pk.append((ra * math.cos(w0 + 0.2 + t * 1.17), ra * math.sin(w0 + 0.2 + t * 1.17)))
        for j in range(10):
            t = 1 - j / 9
            pk.append((ri * math.cos(w0 + 0.45 + t * 0.67), ri * math.sin(w0 + 0.45 + t * 0.67)))
        fenster.append(pk)
    blatt = umriss("Blatt", [zahnkranz_umriss(KETTENBLATT_ZAEHNE), kreis(14, 32)] + fenster, 2.6, "Kettenblatt", fase=0.4, y=KETTENBLATT_Y)
    stern = drehteil("Spider", [(13, KETTENBLATT_Y + 1.3), (26, KETTENBLATT_Y + 1.3), (26, KETTENBLATT_Y + 4.6), (13, KETTENBLATT_Y + 4.6)], "Alu_schwarz", 48)
    teile["kettenblatt"] = verbinden("kettenblatt", [blatt, stern])
    w0 = math.radians(-35)
    for seite, y, w in ((-1, -69, w0), (1, 62, w0 + math.pi)):
        d = Vector((math.cos(w), 0, math.sin(w)))
        ende = d * KURBEL + Vector((0, y + 4 * seite, 0))
        arm = rohr("Arm", [Vector((0, y, 0)), d * 80 + Vector((0, y + 2 * seite, 0)), ende], lambda t: (16 - 5 * t, 9 + 1 * t, 3.0), "Alu_schwarz", um=28)
        nabe_ = drehteil("Kurbelauge", [(0, y - 9), (17, y - 9), (17, y + 9), (0, y + 9)], "Alu_schwarz", 40)
        auge = drehteil("Pedalauge", [(0, ende.y - 8), (11, ende.y - 8), (11, ende.y + 8), (0, ende.y + 8)], "Alu_schwarz", 32)
        verschieben(auge, (ende.x, 0, ende.z))
        teile["kurbel_" + ("l" if seite > 0 else "r")] = verbinden("kurbel_" + ("l" if seite > 0 else "r"), [arm, nabe_, auge])
        p = []
        y0 = ende.y + 12 * seite
        p.append(zylinder("Pedalachse", Vector((0, ende.y, 0)), Vector((0, y0 + 98 * seite, 0)), 5, "Stahl", 16))
        rahmen_p = kasten("Pedalkoerper", (0, y0 + 50 * seite, 0), (98, 96, 15), "Alu_schwarz", fase=3)
        loch = kasten("x", (0, y0 + 50 * seite, 0), (62, 64, 30), "Alu_schwarz")
        mod = rahmen_p.modifiers.new("b", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = loch
        mod.solver = "EXACT"
        rahmen_p = auswerten(rahmen_p, "Pedalkoerper")
        bpy.data.objects.remove(loch, do_unlink=True)
        p.append(rahmen_p)
        for ix in (-1, 1):
            for iy in (-1, 0, 1):
                for iz in (-1, 1):
                    q = Vector((ix * 40, y0 + 50 * seite + iy * 34, iz * 7.5))
                    p.append(zylinder("Pin", q, q + Vector((0, 0, 3.2 * iz)), 1.4, "Stahl", 8))
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
    teile = {}
    rj = teilkreis(SCHALTROLLE_ZAEHNE)
    b_ort = HINTEN + Vector((-8, -82, -38))
    halter = [kasten("Halterblock", b_ort + Vector((-6, 0, -10)), (30, 18, 34), "Alu_schwarz", fase=5),
              zylinder("Halterachse", b_ort + Vector((0, 8, 0)), b_ort + Vector((0, -12, 0)), 7, "Alu_blank", 20)]
    teile["schaltwerk_halter"] = drehpunkt(verbinden("schaltwerk_halter", halter), b_ort)
    para = [rohr("Platte_aussen", [Vector((0, -6, 0)), Vector((60, -6, 0))], lambda t: (11, 3.2, 3.0), "Alu_schwarz", um=20),
            rohr("Platte_innen", [Vector((0, 8, -4)), Vector((60, 8, -4))], lambda t: (8, 2.6, 3.0), "Alu_schwarz", um=20),
            kasten("Kopf", (64, 0, 0), (26, 24, 30), "Alu_schwarz", fase=5),
            kasten("Feder", (30, -10, 6), (34, 4, 10), "Kunststoff", fase=1.5)]
    teile["schaltwerk_arm"] = verbinden("schaltwerk_arm", para)
    abstand = 96.0
    platten = []
    for seite in (1, -1):
        umr = []
        for (x, z) in kreis(rj + 7, 24, start=0):
            umr.append((x, z))
        unten_r = [(x, z - abstand) for x, z in kreis(rj + 7, 24)]
        kontur = []
        for i in range(13):
            w = math.pi * i / 12
            kontur.append(((rj + 6) * math.cos(w), (rj + 6) * math.sin(w)))
        for i in range(13):
            w = math.pi + math.pi * i / 12
            kontur.append(((rj + 8) * math.cos(w) + 4, (rj + 8) * math.sin(w) - abstand))
        pl = umriss(f"Kaefigplatte{seite}", [kontur], 2.4, "Alu_schwarz" if seite < 0 else "Alu_blank", fase=0.5, y=7.5 * seite)
        platten.append(pl)
    platten.append(zylinder("Achse_oben", Vector((0, -9, 0)), Vector((0, 9, 0)), 4, "Alu_blank", 16))
    platten.append(zylinder("Achse_unten", Vector((0, -9, -abstand)), Vector((0, 9, -abstand)), 4, "Alu_blank", 16))
    teile["schaltwerk_kaefig"] = verbinden("schaltwerk_kaefig", platten)
    for name in ("oben", "unten"):
        r = umriss(f"rolle_{name}", [zahnkranz_umriss(SCHALTROLLE_ZAEHNE), kreis(6, 16)], 3.0, "Kunststoff", fase=0.4, y=0)
        nabe = drehteil("Rollennabe", [(5.5, -4), (10, -4), (10, 4), (5.5, 4)], "Alu_blank", 24)
        teile[f"rolle_{name}"] = verbinden(f"rolle_{name}", [r, nabe])
    verschieben(teile["rolle_unten"], (0, 0, -abstand))
    drehpunkt(teile["rolle_unten"], (0, 0, -abstand))
    zusatz(teile["schaltwerk_kaefig"], abstand=abstand, zaehne=SCHALTROLLE_ZAEHNE)
    zusatz(teile["schaltwerk_halter"], ort=[b_ort.x, b_ort.y, b_ort.z])
    return teile


def kettenglieder():
    def lasche(name, y, dicke, mat):
        pk = []
        for i in range(13):
            w = math.pi / 2 + math.pi * i / 12
            pk.append((4.6 * math.cos(w), 4.6 * math.sin(w)))
        for i in range(5):
            t = i / 4
            pk.append((-0 + t * TEILUNG, -4.6 + 1.0 * math.sin(math.pi * t)))
        for i in range(13):
            w = -math.pi / 2 + math.pi * i / 12
            pk.append((TEILUNG + 4.6 * math.cos(w), 4.6 * math.sin(w)))
        for i in range(5):
            t = i / 4
            pk.append((TEILUNG - t * TEILUNG, 4.6 - 1.0 * math.sin(math.pi * t)))
        return umriss(name, [pk, kreis(1.9, 12), kreis(1.9, 12, mitte=(TEILUNG, 0))], dicke, mat, fase=0.25, y=y)

    aussen = [lasche("A1", 4.9, 1.0, "Kette"), lasche("A2", -4.9, 1.0, "Kette"),
              zylinder("Bolzen1", Vector((0, -5.6, 0)), Vector((0, 5.6, 0)), 1.85, "Stahl", 10),
              zylinder("Bolzen2", Vector((TEILUNG, -5.6, 0)), Vector((TEILUNG, 5.6, 0)), 1.85, "Stahl", 10)]
    innen = [lasche("I1", 3.3, 0.9, "Stahl_dunkel"), lasche("I2", -3.3, 0.9, "Stahl_dunkel"),
             zylinder("Rolle1", Vector((0, -2.85, 0)), Vector((0, 2.85, 0)), 3.85, "Stahl_dunkel", 16),
             zylinder("Rolle2", Vector((TEILUNG, -2.85, 0)), Vector((TEILUNG, 2.85, 0)), 3.85, "Stahl_dunkel", 16)]
    a = verbinden("glied_aussen", aussen)
    i = verbinden("glied_innen", innen)
    for o in (a, i):
        verschieben(o, (0, 0, -400))
        drehpunkt(o, (0, 0, -400))
    return a, i


def ruecklicht():
    p = SITZROHR_OBEN + S_RICHTUNG * 118
    hinten = Vector((-math.sin(SITZWINKEL), 0, -math.cos(SITZWINKEL)))
    if hinten.x > 0:
        hinten = -hinten
    schelle = rohr("Schelle", [p - S_RICHTUNG * 9, p + S_RICHTUNG * 9], lambda t: (17.2, 17.2, 2), "Kunststoff", um=32)
    gehaeuse = kasten("Ruecklichtgehaeuse", p + hinten * 24, (16, 40, 46), "Kunststoff", fase=5)
    drehen(gehaeuse, -(math.pi / 2 - SITZWINKEL), "Y", p + hinten * 24)
    linse = kasten("licht_hinten", p + hinten * 32.5, (2.5, 32, 36), "Ruecklicht", fase=1.0, segmente=2)
    drehen(linse, -(math.pi / 2 - SITZWINKEL), "Y", p + hinten * 32.5)
    return verbinden("ruecklicht", [schelle, gehaeuse]), linse


def aufkleber():
    mitte = TRETLAGER.lerp(SITZROHR_OBEN, 0.62)
    normale = Vector((0, -1, 0))
    breite, hoehe = 40.0, 28.0
    d = S_RICHTUNG
    q = Vector((1, 0, 0)).cross(Vector((0, 1, 0)))
    ecken = []
    for (u, v) in ((0, 0), (1, 0), (1, 1), (0, 1)):
        ecken.append(mitte + Vector((0, -19.4, 0)) + d * ((v - 0.5) * hoehe) + Vector((math.sin(SITZWINKEL), 0, math.cos(SITZWINKEL))) * ((u - 0.5) * breite))
    return netz("aufkleber", ecken, [(0, 3, 2, 1)], "Aufkleber", [[(0, 0), (0, 1), (1, 1), (1, 0)]], glatt=False)


def staender():
    teile = []
    klemme = SITZROHR_OBEN + S_RICHTUNG * 95
    saeule = Vector((klemme.x - 30, 470, 0))
    hoehe_kopf = klemme.z + 6
    for k in range(3):
        w = math.radians(90 + 120 * k)
        fuss = saeule + Vector((math.cos(w) * 420, math.sin(w) * 420, -260))
        teile.append(rohr(f"Bein{k}", [saeule + Vector((0, 0, 420 - 260)), fuss], lambda t: (14, 14, 2), "Staender", um=20))
        teile.append(drehteil(f"Fuss{k}", [(0, -8), (24, -8), (26, 0), (20, 6), (0, 6)], "Gummi", 24, mitte=(fuss.x, fuss.y, fuss.z - 6), achse="Z"))
    teile.append(rohr("Saeule", [saeule + Vector((0, 0, -100)), Vector((saeule.x, saeule.y, hoehe_kopf - 60))], lambda t: (22, 22, 2), "Staender", um=32))
    teile.append(rohr("Innenrohr", [Vector((saeule.x, saeule.y, hoehe_kopf - 80)), Vector((saeule.x, saeule.y, hoehe_kopf))], lambda t: (18, 18, 2), "Staender_Stahl", um=28))
    teile.append(rohr("Klemmhebel", [saeule + Vector((22, 0, 400)), saeule + Vector((60, 0, 400)), saeule + Vector((86, 0, 420))], lambda t: (5, 5, 2), "Kunststoff", um=12))
    kopf = Vector((saeule.x, saeule.y, hoehe_kopf))
    teile.append(kasten("Kopf", kopf + Vector((0, 0, 0)), (60, 60, 46), "Staender", fase=8))
    arm_ende = Vector((klemme.x, 70, klemme.z))
    teile.append(rohr("Arm", [kopf + Vector((0, -20, 0)), arm_ende + Vector((0, 28, 0))], lambda t: (15, 15, 3.4), "Staender_Stahl", um=24))
    for seite in (1, -1):
        backe = kasten(f"Backe{seite}", klemme + Vector((22 * seite, 42, 0)), (24, 52, 62), "Staender", fase=6)
        teile.append(backe)
        teile.append(kasten(f"Gummibacke{seite}", klemme + Vector((14 * seite, 22, 0)), (10, 20, 54), "Gummi", fase=3))
    teile.append(rohr("Spindel", [klemme + Vector((0, 70, 18)), klemme + Vector((0, 110, 18))], lambda t: (6, 6, 2), "Staender_Stahl", um=14))
    teile.append(drehteil("Drehgriff", [(0, 0), (22, 0), (24, 14), (18, 22), (0, 22)], "Kunststoff", 32, mitte=(klemme.x, 110, klemme.z + 18)))
    obj = verbinden("staender", teile)
    return drehpunkt(obj, klemme)


def bauen():
    leeren()
    alles = {}
    alles["rahmen"] = rahmen()
    alles["akku"] = akku()
    alles["motor"] = motor()
    g, gu = gabel()
    alles["gabel"], alles["gabel_unten"] = g, gu
    alles.update(cockpit())
    alles["leitungen"] = leitungen()
    st, sa = sattel()
    alles["sattelstuetze"], alles["sattel"] = st, sa
    for vorn in (True, False):
        alles.update(laufrad(vorn))
        sat, bel = bremssattel(vorn)
        alles[sat.name] = sat
        for b in bel:
            alles[b.name] = b
    alles["kassette"] = kassette()
    alles.update(kurbelsatz())
    alles.update(schaltwerk())
    a, i = kettenglieder()
    alles["glied_aussen"], alles["glied_innen"] = a, i
    rl, linse = ruecklicht()
    alles["ruecklicht"], alles["licht_hinten"] = rl, linse
    alles["aufkleber"] = aufkleber()
    if "--ohne-staender" not in sys.argv:
        alles["staender"] = staender()

    behalten = set(id(o) for o in alles.values())
    for o in list(bpy.data.objects):
        if id(o) not in behalten:
            bpy.data.objects.remove(o, do_unlink=True)
    for name, o in alles.items():
        o.name = name
        o.data.name = name
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
    tris = 0
    for name, o in sorted(alles.items()):
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        tris += n
        print(f"  {name:22s} {n:7d}  {[m.name for m in o.data.materials if m]}")
    print(f"Teile: {len(alles)}, Dreiecke: {tris}")

    masse = {
        "hinten": list(HINTEN), "vorn": list(VORN), "tretlager": list(TRETLAGER),
        "sitzrohr_oben": list(SITZROHR_OBEN), "lenkachse": list(U), "krone": list(KRONE), "lenkermitte": list(LENKERMITTE),
        "kettenblatt": {"zaehne": KETTENBLATT_ZAEHNE, "y": KETTENBLATT_Y},
        "kassette": {"zaehne": KASSETTE, "y_gross": KASSETTE_Y_GROSS, "abstand": KASSETTE_ABSTAND},
        "rolle_zaehne": SCHALTROLLE_ZAEHNE, "teilung": TEILUNG, "kurbel": KURBEL, "r_rad": R_RAD,
        "kaefig": 96.0,
    }
    os.makedirs(os.path.dirname(MASSE), exist_ok=True)
    with open(MASSE, "w") as f:
        json.dump(masse, f, indent=1)

    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=ZIEL, export_format="GLB", export_yup=True, export_apply=True,
        export_texcoords=True, export_normals=True, export_tangents=False,
        export_materials="EXPORT", export_extras=True, export_cameras=False, export_lights=False,
        export_animations=False, export_image_format="NONE",
    )
    print("geschrieben:", ZIEL, os.path.getsize(ZIEL))


if __name__ == "__main__":
    bauen()

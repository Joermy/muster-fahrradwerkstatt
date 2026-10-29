"""Geometrie-Helfer für Rad und Werkstatt. Maße in Millimetern, z nach oben."""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TAU = math.pi * 2


def leeren():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 0.001
    return s


def sammlung(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def verlinken(obj, ziel=None):
    (ziel or bpy.context.scene.collection).objects.link(obj)
    return obj


def material_von(mat):
    from . import materialien
    return materialien.holen(mat) if isinstance(mat, str) else mat


def netz(name, punkte, flaechen, mat, uvs=None, glatt=True, winkel=40):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in punkte], [], flaechen)
    if uvs is not None:
        lage = me.uv_layers.new(name="UVMap")
        for f, uv in zip(me.polygons, uvs):
            for k in range(f.loop_total):
                lage.data[f.loop_start + k].uv = uv[k]
    me.validate(clean_customdata=False)
    me.update()
    obj = verlinken(bpy.data.objects.new(name, me))
    if mat is not None:
        me.materials.append(material_von(mat))
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
    ziel = obj.users_collection[0] if obj.users_collection else None
    verlinken(neu, ziel)
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


def fasen(obj, breite, segmente=2, winkel=35, profil=0.5):
    if breite <= 0:
        return obj
    mod = obj.modifiers.new("Fase", "BEVEL")
    mod.width = breite
    mod.segments = segmente
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(winkel)
    mod.miter_outer = "MITER_ARC"
    mod.profile = profil
    return auswerten(obj, obj.name)


def unterteilen(obj, stufen=2):
    mod = obj.modifiers.new("Glatt", "SUBSURF")
    mod.levels = stufen
    mod.render_levels = stufen
    return auswerten(obj, obj.name)


def verbinden(name, objekte):
    objekte = [o for o in objekte if o]
    ziel = objekte[0]
    if len(objekte) > 1:
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


def verschieben(obj, d):
    obj.data.transform(Matrix.Translation(Vector(d)))
    return obj


def drehen(obj, winkel, achse, um=(0, 0, 0)):
    m = Matrix.Translation(Vector(um)) @ Matrix.Rotation(winkel, 4, achse) @ Matrix.Translation(-Vector(um))
    obj.data.transform(m)
    return obj


def zusatz(obj, **werte):
    for k, w in werte.items():
        obj[k] = w
    return obj


def spline(punkte, schritt=6.0):
    """Catmull-Rom (zentripetal) durch die Punkte, gleichmäßig nachgetastet."""
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


def rohr(name, punkte, profil, mat, um=32, schritt=6.0, kappen=(True, True), seite=Vector((0, 1, 0)), uv_laenge=None, glatt=True):
    """Zieht ein Superellipsen-Profil entlang eines Splines.

    profil(t) -> (halbachse_a, halbachse_b, exponent[, versatz_a]); a liegt in der Ebene senkrecht zu `seite`.
    """
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
    b = Vector(seite) - tang[0] * Vector(seite).dot(tang[0])
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
    punkte_aus, flaechen, uvs = [], [], []
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
    ul = uv_laenge or gesamt or 1
    for i in range(n - 1):
        for k in range(um):
            k2 = (k + 1) % um
            flaechen.append((i * um + k, i * um + k2, (i + 1) * um + k2, (i + 1) * um + k))
            u0, u1 = laengen[i] / ul, laengen[i + 1] / ul
            uvs.append([(u0, k / um), (u0, (k + 1) / um), (u1, (k + 1) / um), (u1, k / um)])
    if kappen[0]:
        mitte = len(punkte_aus)
        q = profil(0)
        punkte_aus.append(pfad[0] + rahmen[0][0] * (q[3] if len(q) > 3 else 0))
        for k in range(um):
            flaechen.append((mitte, (k + 1) % um, k))
            uvs.append([(0.5, 0.5)] * 3)
    if kappen[1]:
        mitte = len(punkte_aus)
        q = profil(1)
        punkte_aus.append(pfad[-1] + rahmen[-1][0] * (q[3] if len(q) > 3 else 0))
        o = (n - 1) * um
        for k in range(um):
            flaechen.append((mitte, o + k, o + (k + 1) % um))
            uvs.append([(0.5, 0.5)] * 3)
    return netz(name, punkte_aus, flaechen, mat, uvs, glatt)


def zylinder(name, a, b, r, mat, um=24, kappen=True, r2=None):
    a, b = Vector(a), Vector(b)
    r2 = r if r2 is None else r2
    return rohr(name, [a, b], lambda t: (r + (r2 - r) * t, r + (r2 - r) * t, 2), mat, um=um, schritt=max((b - a).length, 1), kappen=(kappen, kappen))


def drehteil(name, profil, mat, segmente=96, mitte=(0, 0, 0), achse="Y", geschlossen=True, winkel=40):
    """Drehkörper: profil ist eine Liste (r, h); gedreht um die lokale y-Achse."""
    rmax = max(r for r, _ in profil) or 1
    m = len(profil)
    punkte = []
    for k in range(segmente):
        w = TAU * k / segmente
        c, s = math.cos(w), math.sin(w)
        for r, y in profil:
            punkte.append(Vector((r * c, y, r * s)))
    flaechen, uvs = [], []
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
        drehen(obj, math.pi / 2, "X")
    verschieben(obj, mitte)
    return obj


def drehteil_achse(name, profil, mat, mitte, achse, segmente=96, winkel=40):
    """Drehkörper um eine beliebige Achse durch `mitte`."""
    obj = drehteil(name, profil, mat, segmente, winkel=winkel)
    rot = Vector((0, 1, 0)).rotation_difference(Vector(achse).normalized()).to_matrix().to_4x4()
    obj.data.transform(Matrix.Translation(Vector(mitte)) @ rot)
    return obj


def umriss(name, umrisse, dicke, mat, fase=0.0, aufloesung=1, y=0.0):
    """Extrudiert geschlossene 2D-Umrisse (x, z) symmetrisch um y; Löcher sind weitere Umrisse."""
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
    obj = verlinken(bpy.data.objects.new(name, cu))
    cu.materials.append(material_von(mat))
    obj = auswerten(obj, name)
    obj.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bm.to_mesh(obj.data)
    bm.free()
    verschieben(obj, (0, y, 0))
    glaetten(obj, 35)
    return obj


def kasten(name, mitte, groesse, mat, fase=0.0, segmente=3, winkel=30):
    sx, sy, sz = (g / 2 for g in groesse)
    p = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz), (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    obj = netz(name, [Vector(q) + Vector(mitte) for q in p], f, mat, glatt=False)
    if fase > 0:
        obj = fasen(obj, fase, segmente, winkel)
        glaetten(obj, 35)
    return obj


def kreis(r, n, start=0.0, mitte=(0, 0)):
    return [(mitte[0] + r * math.cos(start + TAU * i / n), mitte[1] + r * math.sin(start + TAU * i / n)) for i in range(n)]


def rundrechteck(b, h, r, n=6, mitte=(0, 0)):
    """Umriss eines Rechtecks mit runden Ecken, gegen den Uhrzeigersinn."""
    aus = []
    for ecke, (cx, cy) in enumerate(((b / 2 - r, -h / 2 + r), (b / 2 - r, h / 2 - r), (-b / 2 + r, h / 2 - r), (-b / 2 + r, -h / 2 + r))):
        for i in range(n + 1):
            w = -math.pi / 2 + ecke * math.pi / 2 + (math.pi / 2) * i / n
            aus.append((mitte[0] + cx + r * math.cos(w), mitte[1] + cy + r * math.sin(w)))
    return aus


def platte(name, umriss_, dicke, mat, fase=0.0, matrix=None, loecher=()):
    """Extrudiert einen 2D-Umriss in z (0 … dicke) und setzt ihn mit `matrix` in die Welt."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = max(dicke / 2 - fase, 0.0001)
    cu.bevel_depth = fase
    cu.bevel_resolution = 1
    cu.offset = -fase
    for u in [umriss_] + list(loecher):
        sp = cu.splines.new("POLY")
        sp.points.add(len(u) - 1)
        for i, (x, y) in enumerate(u):
            sp.points[i].co = (x, y, 0, 1)
        sp.use_cyclic_u = True
    obj = verlinken(bpy.data.objects.new(name, cu))
    cu.materials.append(material_von(mat))
    obj = auswerten(obj, name)
    obj.data.transform(Matrix.Translation((0, 0, dicke / 2)))
    if matrix is not None:
        obj.data.transform(matrix)
    glaetten(obj, 35)
    return obj


def torus(name, mitte, achse, profil, mat, um=96, winkel=60):
    """Drehkörper aus einem geschlossenen Profil (r, h) um `achse`."""
    punkte, flaechen = [], []
    n = len(profil)
    for k in range(um):
        w = TAU * k / um
        for (r, h) in profil:
            punkte.append(Vector((r * math.cos(w), r * math.sin(w), h)))
    for k in range(um):
        for i in range(n):
            a = k * n + i
            b = k * n + (i + 1) % n
            c = ((k + 1) % um) * n + (i + 1) % n
            d = ((k + 1) % um) * n + i
            flaechen.append((a, b, c, d))
    rot = Vector(achse).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation(Vector(mitte)) @ rot
    return netz(name, [m @ p for p in punkte], flaechen, mat, glatt=True, winkel=winkel)


def kreisprofil(r_mitte, r, n=12, h=0.0):
    return [(r_mitte + r * math.cos(TAU * i / n), h + r * math.sin(TAU * i / n)) for i in range(n)]


def boolesch(obj, werkzeug, art="DIFFERENCE", loeschen=True):
    mod = obj.modifiers.new("Bool", "BOOLEAN")
    mod.operation = art
    mod.object = werkzeug
    mod.solver = "EXACT"
    neu = auswerten(obj, obj.name)
    if loeschen:
        bpy.data.objects.remove(werkzeug, do_unlink=True)
    return neu


def kopieren(obj, name):
    neu = obj.copy()
    neu.data = obj.data.copy()
    neu.name = name
    verlinken(neu, obj.users_collection[0] if obj.users_collection else None)
    return neu


def voxel(obj, groesse, glaettung=0, faktor=0.5, reduzieren=None):
    """Verschmilzt alle Teile eines Objekts zu einer geschlossenen Hülle (Carbon-Übergänge)."""
    mod = obj.modifiers.new("Voxel", "REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = groesse
    mod.adaptivity = 0.0
    mod.use_smooth_shade = True
    obj = auswerten(obj, obj.name)
    if glaettung:
        mod = obj.modifiers.new("Glaetten", "CORRECTIVE_SMOOTH")
        mod.iterations = glaettung
        mod.factor = faktor
        mod.use_only_smooth = True
        mod.smooth_type = "SIMPLE"
        obj = auswerten(obj, obj.name)
    if reduzieren:
        mod = obj.modifiers.new("Weniger", "DECIMATE")
        mod.ratio = reduzieren
        obj = auswerten(obj, obj.name)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def welt_bbox(obj):
    ecken = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return Vector(map(min, *ecken)), Vector(map(max, *ecken))


def chaikin(punkte, schritte=3):
    """Rundet einen geschlossenen 2D-Umriss durch Eckenabschneiden."""
    p = [tuple(q) for q in punkte]
    for _ in range(schritte):
        neu = []
        n = len(p)
        for i in range(n):
            a, b = p[i], p[(i + 1) % n]
            neu.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            neu.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        p = neu
    return p

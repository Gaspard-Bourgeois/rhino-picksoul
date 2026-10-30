#! python3
# -*- coding: utf-8 -*-
"""
Distance entre deux courbes - Rhino 8 (Python 3 ou IronPython)

Principe :
  - La courbe 1 est echantillonnee en N points.
  - Pour chaque point, on cherche le point le plus proche sur la courbe 2
    (segment "minimum" local).
  - Segment MIN = le plus court de tous ces segments.
  - Segment MAX = le plus long de ces segments minimums
    (distance de Hausdorff orientee courbe 1 -> courbe 2).

Affichage :
  - Segment MIN en vert, segment MAX en rouge, sur le calque choisi (defaut : calque actuel)
  - Pastilles de texte (TextDot) avec les valeurs, de la meme couleur
  - Resume dans la ligne de commande
"""
import math
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
import System.Drawing as sd

COLOR_MIN = sd.Color.FromArgb(0, 170, 70)    # vert
COLOR_MAX = sd.Color.FromArgb(220, 30, 30)   # rouge
STICKY_KEY = "dist_courbes_pas_mm"
DEFAULT_STEP_MM = 0.1      # pas d'echantillonnage par defaut (mm)
MAX_POINTS = 100000        # garde-fou


def sample_params(crv, n):
    """Parametres repartis uniformement en longueur (repli : en parametre)."""
    try:
        ts = crv.DivideByCount(n, True)
        if ts and len(ts) > 1:
            return list(ts)
    except Exception:
        pass
    dom = crv.Domain
    return [dom.ParameterAt(i / float(n)) for i in range(n + 1)]


def closest_on(crv, pt):
    res = crv.ClosestPoint(pt)
    # res = (bool, t) en Python 3 comme en IronPython
    ok, t = res[0], res[1]
    if not ok:
        return None
    return crv.PointAt(t)


def main():
    # --- Choix de la courbe 1 + option "Pas" (distance d'echantillonnage, en mm)
    step_mm = sc.sticky.get(STICKY_KEY, DEFAULT_STEP_MM)
    opt_step = Rhino.Input.Custom.OptionDouble(step_mm, True, 0.0001)

    layer_name = rs.CurrentLayer()  # calque par defaut = calque actuel

    go = Rhino.Input.Custom.GetObject()
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go.SubObjectSelect = False
    go.AddOptionDouble("Pas_mm", opt_step)
    go.AddOption("Calque")
    while True:
        go.SetCommandPrompt("Courbe 1 (depart) [calque : {}]".format(layer_name))
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            if go.Option().EnglishName == "Calque":
                name = rs.GetString("Nom du calque (vide = calque actuel)", layer_name)
                if name is not None:
                    name = name.strip()
                    layer_name = name if name else rs.CurrentLayer()
            continue  # opt_step est deja mis a jour par Rhino
        if res == Rhino.Input.GetResult.Object:
            break
        return
    id1 = go.Object(0).ObjectId
    step_mm = opt_step.CurrentValue
    sc.sticky[STICKY_KEY] = step_mm

    id2 = rs.GetObject("Courbe 2 (arrivee)", rs.filter.curve)
    if not id2:
        return

    c1 = rs.coercecurve(id1)
    c2 = rs.coercecurve(id2)
    if c1 is None or c2 is None:
        print("Selection de courbes invalide.")
        return

    # Pas converti dans l'unite du document -> nombre de points
    scale = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Millimeters, sc.doc.ModelUnitSystem)
    step_doc = step_mm * scale
    length = c1.GetLength()
    n = int(math.ceil(length / step_doc)) if step_doc > 0 else MAX_POINTS
    n = max(n, 10)
    if n > MAX_POINTS:
        print("Pas trop fin : limite a {} points (pas reel {:.4f} mm).".format(
            MAX_POINTS, length / MAX_POINTS / scale))
        n = MAX_POINTS

    # --- Calcul ---------------------------------------------------------
    results = []  # (distance, point sur c1, point sur c2)
    for t in sample_params(c1, n):
        p1 = c1.PointAt(t)
        p2 = closest_on(c2, p1)
        if p2 is None:
            continue
        results.append((p1.DistanceTo(p2), p1, p2))

    if not results:
        print("Aucune distance calculee.")
        return

    d_min, a_min, b_min = min(results, key=lambda r: r[0])
    d_max, a_max, b_max = max(results, key=lambda r: r[0])

    # Affinage du minimum global avec les vraies courbes (si disponible)
    try:
        res = Rhino.Geometry.Curve.ClosestPoints(c1, c2)
        if res[0]:
            pa, pb = res[1], res[2]
            d = pa.DistanceTo(pb)
            if d < d_min:
                d_min, a_min, b_min = d, pa, pb
    except Exception:
        pass

    mean = sum(r[0] for r in results) / float(len(results))

    # --- Affichage ------------------------------------------------------
    if not rs.IsLayer(layer_name):
        rs.AddLayer(layer_name)

    rs.EnableRedraw(False)
    try:
        def draw(a, b, d, color, label):
            seg = rs.AddLine(a, b)
            rs.ObjectLayer(seg, layer_name)
            rs.ObjectColor(seg, color)
            mid = Rhino.Geometry.Point3d((a.X + b.X) / 2.0, (a.Y + b.Y) / 2.0, (a.Z + b.Z) / 2.0)
            dot = rs.AddTextDot("{} = {:.3f}".format(label, d), mid)
            rs.ObjectLayer(dot, layer_name)
            rs.ObjectColor(dot, color)
            return [seg, dot]

        created = draw(a_min, b_min, d_min, COLOR_MIN, "MIN")
        created += draw(a_max, b_max, d_max, COLOR_MAX, "MAX")

        # Groupe unique contenant les 2 segments et les 2 pastilles
        grp = rs.AddGroup()
        rs.AddObjectsToGroup(created, grp)
    finally:
        rs.EnableRedraw(True)

    unit = str(sc.doc.ModelUnitSystem)
    print("-" * 44)
    print("Distance courbe 1 -> courbe 2 ({} points, pas {:g} mm, unite : {})".format(
        len(results), step_mm, unit))
    print("  MIN  : {:.4f}   (vert)".format(d_min))
    print("  MAX  : {:.4f}   (rouge)".format(d_max))
    print("  Calque : {}".format(layer_name))
    print("  Moy. : {:.4f}".format(mean))
    print("  Ecart MAX - MIN : {:.4f}".format(d_max - d_min))
    print("-" * 44)


if __name__ == "__main__":
    main()

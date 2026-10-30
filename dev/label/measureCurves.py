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
  - Segment MIN en vert (calque Distance_MIN), segment MAX en rouge (calque Distance_MAX)
  - Pastilles de texte (TextDot) avec les valeurs, de la meme couleur
  - Resume dans la ligne de commande
"""
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
import System.Drawing as sd

LAYER_MIN = "Distance_MIN"
LAYER_MAX = "Distance_MAX"
COLOR_MIN = sd.Color.FromArgb(0, 170, 70)    # vert
COLOR_MAX = sd.Color.FromArgb(220, 30, 30)   # rouge
STICKY_KEY = "dist_courbes_nb_points"
DEFAULT_N = 200


def ensure_layer(name, color):
    if not rs.IsLayer(name):
        rs.AddLayer(name, color)
    else:
        rs.LayerColor(name, color)


def clear_layer(name):
    objs = rs.ObjectsByLayer(name)
    if objs:
        rs.DeleteObjects(objs)


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
    id1 = rs.GetObject("Courbe 1 (depart)", rs.filter.curve, preselect=True)
    if not id1:
        return
    id2 = rs.GetObject("Courbe 2 (arrivee)", rs.filter.curve)
    if not id2:
        return

    c1 = rs.coercecurve(id1)
    c2 = rs.coercecurve(id2)
    if c1 is None or c2 is None:
        print("Selection de courbes invalide.")
        return

    n_default = sc.sticky.get(STICKY_KEY, DEFAULT_N)
    n = rs.GetInteger("Nombre de points d'echantillonnage sur la courbe 1", n_default, 10, 20000)
    if n is None:
        return
    sc.sticky[STICKY_KEY] = n

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
    ensure_layer(LAYER_MIN, COLOR_MIN)
    ensure_layer(LAYER_MAX, COLOR_MAX)
    clear_layer(LAYER_MIN)
    clear_layer(LAYER_MAX)

    rs.EnableRedraw(False)
    try:
        def draw(a, b, d, layer, label):
            seg = rs.AddLine(a, b)
            rs.ObjectLayer(seg, layer)
            rs.ObjectColor(seg, rs.LayerColor(layer))
            mid = Rhino.Geometry.Point3d((a.X + b.X) / 2.0, (a.Y + b.Y) / 2.0, (a.Z + b.Z) / 2.0)
            dot = rs.AddTextDot("{} = {:.3f}".format(label, d), mid)
            rs.ObjectLayer(dot, layer)
            rs.ObjectColor(dot, rs.LayerColor(layer))

        draw(a_min, b_min, d_min, LAYER_MIN, "MIN")
        draw(a_max, b_max, d_max, LAYER_MAX, "MAX")
    finally:
        rs.EnableRedraw(True)

    unit = str(sc.doc.ModelUnitSystem)
    print("-" * 44)
    print("Distance courbe 1 -> courbe 2 ({} points, unite : {})".format(len(results), unit))
    print("  MIN  : {:.4f}   (vert, calque {})".format(d_min, LAYER_MIN))
    print("  MAX  : {:.4f}   (rouge, calque {})".format(d_max, LAYER_MAX))
    print("  Moy. : {:.4f}".format(mean))
    print("  Ecart MAX - MIN : {:.4f}".format(d_max - d_min))
    print("-" * 44)


if __name__ == "__main__":
    main()

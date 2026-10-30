#! python3
# -*- coding: utf-8 -*-
"""
Distance entre deux courbes - Rhino 8 (Python 3 ou IronPython)

Les courbes peuvent etre dans des blocs : clic sur le bloc = toutes ses courbes,
Ctrl+Maj+clic = une courbe precise a l'interieur du bloc (blocs imbriques geres).

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
import fnmatch
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
import System.Drawing as sd

COLOR_MIN = sd.Color.FromArgb(0, 170, 70)    # vert
COLOR_MAX = sd.Color.FromArgb(220, 30, 30)   # rouge
STICKY_KEY = "dist_courbes_pas_mm"
DEFAULT_STEP_MM = 0.1      # pas d'echantillonnage par defaut (mm)
MAX_POINTS = 100000        # garde-fou


def choose_layer(default_layer):
    """Saisie du calque : nom exact, motif avec * (virgules possibles) ou liste.
    Propose de creer le calque s'il est introuvable. Retourne le nom, ou None."""
    show_list = "ListeDesCalques"
    user_input = rs.GetString("Calque de destination", default_layer, [show_list])
    if not user_input:
        return None
    if user_input == show_list:
        user_input = rs.GetLayer()
        if not user_input:
            return None

    patterns = [p.strip().lower() for p in user_input.split(",") if p.strip()]
    matched = None
    for lay in rs.LayerNames() or []:
        for pat in patterns:
            if fnmatch.fnmatch(lay.lower(), pat):
                matched = lay
                break
        if matched:
            break

    if not matched:
        rep = rs.GetString('Calque introuvable, voulez-vous creer "' + user_input + '"', "oui", ["oui", "non"])
        if rep == "oui":
            rs.AddLayer(user_input)
            matched = user_input
    return matched


def collect_curves(robj, xf, out):
    """Ajoute a `out` les courbes de robj (en coordonnees monde).
    Descend recursivement dans les blocs (blocs imbriques inclus)."""
    if isinstance(robj, Rhino.DocObjects.InstanceObject):
        xf2 = Rhino.Geometry.Transform.Multiply(xf, robj.InstanceXform)
        for sub in robj.InstanceDefinition.GetObjects():
            collect_curves(sub, xf2, out)
    else:
        g = robj.Geometry
        if isinstance(g, Rhino.Geometry.Curve):
            d = g.DuplicateCurve()
            d.Transform(xf)
            out.append(d)


def curves_from_objref(objref):
    """Courbes (monde) d'un objet choisi : courbe simple, sous-objet d'un bloc
    (Ctrl+Maj+clic) ou bloc entier (toutes ses courbes)."""
    obj = objref.Object()
    out = []
    if isinstance(obj, Rhino.DocObjects.InstanceObject):
        ci = objref.GeometryComponentIndex
        sub = None
        try:
            if ci.ComponentIndexType == Rhino.Geometry.ComponentIndexType.InstanceDefinitionPart and ci.Index >= 0:
                sub = obj.SubObjectFromComponentIndex(ci)
        except Exception:
            sub = None
        if sub is not None:
            collect_curves(sub, obj.InstanceXform, out)
        else:
            collect_curves(obj, Rhino.Geometry.Transform.Identity, out)
    else:
        crv = objref.Curve()
        if crv is not None:
            out.append(crv.DuplicateCurve())
    return out


CURVE_OR_BLOCK = Rhino.DocObjects.ObjectType.Curve | Rhino.DocObjects.ObjectType.InstanceReference


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


def closest_on(crvs, pt):
    """Point le plus proche de pt sur un ensemble de courbes."""
    best = None
    bd = None
    for crv in crvs:
        res = crv.ClosestPoint(pt)  # (bool, t)
        if not res[0]:
            continue
        q = crv.PointAt(res[1])
        d = pt.DistanceTo(q)
        if bd is None or d < bd:
            best, bd = q, d
    return best


def main():
    # --- Choix de la courbe 1 + option "Pas" (distance d'echantillonnage, en mm)
    step_mm = sc.sticky.get(STICKY_KEY, DEFAULT_STEP_MM)
    opt_step = Rhino.Input.Custom.OptionDouble(step_mm, True, 0.0001)

    layer_name = rs.CurrentLayer()  # calque par defaut = calque actuel

    go = Rhino.Input.Custom.GetObject()
    go.GeometryFilter = CURVE_OR_BLOCK
    go.SubObjectSelect = True   # Ctrl+Maj+clic : courbe a l'interieur d'un bloc
    go.AddOptionDouble("Pas_mm", opt_step)
    go.AddOption("Calque")
    while True:
        go.SetCommandPrompt("Courbe 1 (depart) [calque : {}]".format(layer_name))
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            if go.Option().EnglishName == "Calque":
                chosen = choose_layer(layer_name)
                if chosen:
                    layer_name = chosen
            continue  # opt_step est deja mis a jour par Rhino
        if res == Rhino.Input.GetResult.Object:
            break
        return
    c1 = curves_from_objref(go.Object(0))
    step_mm = opt_step.CurrentValue
    sc.sticky[STICKY_KEY] = step_mm

    go2 = Rhino.Input.Custom.GetObject()
    go2.SetCommandPrompt("Courbe 2 (arrivee)")
    go2.GeometryFilter = CURVE_OR_BLOCK
    go2.SubObjectSelect = True
    if go2.Get() != Rhino.Input.GetResult.Object:
        return
    c2 = curves_from_objref(go2.Object(0))

    if not c1 or not c2:
        print("Aucune courbe trouvee dans la selection.")
        return

    # Pas converti dans l'unite du document -> nombre de points par courbe
    scale = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Millimeters, sc.doc.ModelUnitSystem)
    step_doc = step_mm * scale
    counts = [max(10, int(math.ceil(c.GetLength() / step_doc))) if step_doc > 0 else 10 for c in c1]
    total = sum(counts)
    if total > MAX_POINTS:
        print("Pas trop fin : limite a {} points.".format(MAX_POINTS))
        counts = [max(10, int(n * MAX_POINTS / float(total))) for n in counts]

    # --- Calcul ---------------------------------------------------------
    results = []  # (distance, point sur c1, point sur c2)
    for crv, n in zip(c1, counts):
        for t in sample_params(crv, n):
            p1 = crv.PointAt(t)
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
        for ca in c1:
            for cb in c2:
                res = Rhino.Geometry.Curve.ClosestPoints(ca, cb)
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
            # Distance nulle (courbes qui se touchent/se croisent) : une ligne de
            # longueur 0 est refusee par Rhino -> on place un point a la place.
            if a.DistanceTo(b) > sc.doc.ModelAbsoluteTolerance * 1e-3:
                seg = rs.AddLine(a, b)
            else:
                seg = rs.AddPoint(a)
            if not seg:
                return []
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
        if created:
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

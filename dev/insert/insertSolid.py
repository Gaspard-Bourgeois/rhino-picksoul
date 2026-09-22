"""
Extend surfaces (neighbors only) until they touch, then create a solid.
IronPython 2.7 - Rhino 8
Inspiré du pattern d'options interactives de smartMove.py
"""
import Rhino
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import System

TOL = sc.doc.ModelAbsoluteTolerance


# ---------------------------------------------------------------------------
# SELECTION + OPTIONS (pattern inspiré de getWithOption dans smartMove.py)
# ---------------------------------------------------------------------------
def getSurfacesWithOptions(_message, extend_step_default=5.0, max_iter_default=40):
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(_message)
    go.SubObjectSelect = False
    go.GroupSelect = True
    go.AcceptNothing(True)
    go.GeometryFilter = (Rhino.DocObjects.ObjectType.Surface |
                          Rhino.DocObjects.ObjectType.Brep)

    extendStepOpt = Rhino.Input.Custom.OptionDouble(extend_step_default, 0.0001, 1.0e6)
    maxIterOpt = Rhino.Input.Custom.OptionInteger(max_iter_default, 1, 1000)
    go.AddOptionDouble("Increment", extendStepOpt)
    go.AddOptionInteger("MaxIter", maxIterOpt)

    while True:
        get_rc = go.GetMultiple(2, 0)
        if get_rc == Rhino.Input.GetResult.Object:
            break
        if go.CommandResult() != Rhino.Commands.Result.Success:
            break
        if get_rc == Rhino.Input.GetResult.Option:
            continue

    ids = []
    count = go.ObjectCount
    for i in range(count):
        objref = go.Object(i)
        ids.append(objref.ObjectId)

    extend_step = extendStepOpt.CurrentValue
    max_iter = maxIterOpt.CurrentValue
    go.Dispose()
    return ids, extend_step, max_iter


# ---------------------------------------------------------------------------
# ADJACENCE - Arbre couvrant minimal sur la distance des bounding box
# ---------------------------------------------------------------------------
def bbox_distance(bbox_a, bbox_b):
    """Distance min entre deux bounding box alignées (0 si elles se recouvrent)."""
    dx = max(bbox_a.Min.X - bbox_b.Max.X, bbox_b.Min.X - bbox_a.Max.X, 0)
    dy = max(bbox_a.Min.Y - bbox_b.Max.Y, bbox_b.Min.Y - bbox_a.Max.Y, 0)
    dz = max(bbox_a.Min.Z - bbox_b.Max.Z, bbox_b.Min.Z - bbox_a.Max.Z, 0)
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def build_neighbor_pairs(breps):
    """
    Construit la liste des couples 'voisins' via un arbre couvrant minimal
    (Prim) sur la distance des bounding box. Chaque surface est reliée à
    ses voisines les plus proches, pas à toutes les autres.
    """
    n = len(breps)
    bboxes = [b.GetBoundingBox(True) for b in breps]

    in_tree = [False] * n
    in_tree[0] = True
    edges = []

    for _ in range(n - 1):
        best_dist = None
        best_pair = None
        for i in range(n):
            if not in_tree[i]:
                continue
            for j in range(n):
                if in_tree[j]:
                    continue
                d = bbox_distance(bboxes[i], bboxes[j])
                if best_dist is None or d < best_dist:
                    best_dist = d
                    best_pair = (i, j)
        if best_pair is None:
            break
        i, j = best_pair
        in_tree[j] = True
        edges.append((i, j))

    return edges


# ---------------------------------------------------------------------------
# EXTENSION
# ---------------------------------------------------------------------------
def surfaces_intersect(brep_a, brep_b):
    rc = rg.Intersect.Intersection.BrepBrep(brep_a, brep_b, TOL)
    if not rc[0]:
        return False
    curves, points = rc[1], rc[2]
    return (curves is not None and len(curves) > 0) or (points is not None and len(points) > 0)


def extend_all_edges(brep, extend_step):
    face = brep.Faces[0]
    srf = face.ToNurbsSurface()
    changed = False

    for side in [rg.IsoStatus.West, rg.IsoStatus.East,
                 rg.IsoStatus.South, rg.IsoStatus.North]:
        try:
            extended = srf.Extend(side, extend_step, True)
            if extended is not None:
                srf = extended
                changed = True
        except Exception:
            pass

    if changed:
        return srf.ToBrep()
    return brep


# ---------------------------------------------------------------------------
# COEUR DU SCRIPT
# ---------------------------------------------------------------------------
def extendAndCreateSolid(ids, extend_step=5.0, max_iter=40):
    breps = []
    for id_ in ids:
        obj = rs.coercebrep(id_)
        if obj:
            breps.append(obj.Duplicate())

    if len(breps) < 2:
        print("Il faut au moins 2 surfaces.")
        return

    neighbor_pairs = build_neighbor_pairs(breps)
    print("{} couples voisins détectés (sur {} surfaces).".format(
        len(neighbor_pairs), len(breps)))

    sc.doc.Objects.UnselectAll()
    iteration = 0
    all_neighbors_touch = False

    while iteration < max_iter and not all_neighbors_touch:
        iteration += 1
        all_neighbors_touch = True

        for i in range(len(breps)):
            breps[i] = extend_all_edges(breps[i], extend_step)

        for (i, j) in neighbor_pairs:
            if not surfaces_intersect(breps[i], breps[j]):
                all_neighbors_touch = False

        print("Itération {} - prolongement total: {} - voisins tous en contact: {}".format(
            iteration, iteration * extend_step, all_neighbors_touch))

    if not all_neighbors_touch:
        print("Echec: certains voisins ne se touchent pas apres {} iterations "
              "(prolongement max: {}). Augmenter extend_step ou max_iter.".format(
                  max_iter, max_iter * extend_step))
        return

    new_ids = []
    for id_, brep in zip(ids, breps):
        new_id = sc.doc.Objects.AddBrep(brep)
        if new_id != System.Guid.Empty:
            new_ids.append(new_id)
            sc.doc.Objects.Delete(id_, True)

    sc.doc.Views.Redraw()

    rs.SelectObjects(new_ids)
    rs.Command("_CreateSolid _Enter", echo=False)


# ---------------------------------------------------------------------------
# ENTREE INTERACTIVE
# ---------------------------------------------------------------------------
def RunCommand(is_interactive):
    ids, extend_step, max_iter = getSurfacesWithOptions(
        "Selectionner les surfaces a prolonger (options: Increment / MaxIter)")

    if not ids:
        print("Aucune surface selectionnee.")
        return 0

    extendAndCreateSolid(ids, extend_step, max_iter)
    return 0


if __name__ == "__main__":
    RunCommand(True)
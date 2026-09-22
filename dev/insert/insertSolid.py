"""
Extend surfaces (standalone or extracted from a polysurface) until
neighbors touch, then create a solid.
Failure-safe: keeps whatever surfaces were successfully extended,
colors them blue, and remembers them (via sc.sticky) across script
runs so you can just add one more surface and re-run.

IronPython 2.7 - Rhino 8
"""
import Rhino
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import System

TOL = sc.doc.ModelAbsoluteTolerance
EXTENDED_COLOR = (0, 102, 255)  # bleu unique pour identifier les surfaces générées par ce script
STICKY_KEY = "ExtendCreateSolid_pending_ids"


# ---------------------------------------------------------------------------
# GESTION DE L'ETAT PERSISTANT (sc.sticky) ENTRE DEUX EXECUTIONS
# ---------------------------------------------------------------------------
def get_pending_entries():
    """Récupère les surfaces laissées en bleu par une exécution précédente."""
    ids = sc.sticky.get(STICKY_KEY, [])
    entries = []
    valid_ids = []
    for id_ in ids:
        obj = sc.doc.Objects.Find(id_)
        if obj is None:
            continue  # objet supprimé entre-temps par l'utilisateur
        brep = rs.coercebrep(id_)
        if brep is not None:
            entries.append({"brep": brep, "orig_id": id_, "is_extracted": False})
            valid_ids.append(id_)
    sc.sticky[STICKY_KEY] = valid_ids  # nettoie les ids devenus invalides
    return entries


def set_pending_ids(ids):
    sc.sticky[STICKY_KEY] = list(ids)


def clear_pending():
    sc.sticky[STICKY_KEY] = []


# ---------------------------------------------------------------------------
# SELECTION + OPTIONS - uniquement pour les NOUVELLES surfaces à ajouter
# Accepte des surfaces standalone ET des faces individuelles de polysurfaces
# ---------------------------------------------------------------------------
def getSurfacesWithOptions(_message, extend_step_default=5.0, max_iter_default=40, min_count=0):
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(_message)
    go.SubObjectSelect = True   # permet de cliquer une face d'une polysurface
    go.GroupSelect = True
    go.AcceptNothing(True)
    # Ignore toute présélection existante : force un pick interactif propre,
    # c'est ce qui règle le problème d'exécution "automatique" au relancement.
    go.EnablePreSelect(False, True)
    go.GeometryFilter = (Rhino.DocObjects.ObjectType.Surface |
                          Rhino.DocObjects.ObjectType.Brep |
                          Rhino.DocObjects.ObjectType.Extrusion)

    extendStepOpt = Rhino.Input.Custom.OptionDouble(extend_step_default, 0.0001, 1.0e6)
    maxIterOpt = Rhino.Input.Custom.OptionInteger(max_iter_default, 1, 1000)
    resetOpt = Rhino.Input.Custom.OptionToggle(False, "False", "True")
    go.AddOptionDouble("Increment", extendStepOpt)
    go.AddOptionInteger("MaxIter", maxIterOpt)
    go.AddOptionToggle("ResetPending", resetOpt)

    while True:
        get_rc = go.GetMultiple(min_count, 0)
        if get_rc == Rhino.Input.GetResult.Object:
            break
        if get_rc == Rhino.Input.GetResult.Nothing:
            break
        if go.CommandResult() != Rhino.Commands.Result.Success:
            break
        if get_rc == Rhino.Input.GetResult.Option:
            continue

    entries = []
    count = go.ObjectCount
    for i in range(count):
        objref = go.Object(i)
        face = objref.Face()  # non-None si une face de polysurface a été cliquée

        if face is not None:
            dup_brep = face.DuplicateFace(False)
            entries.append({"brep": dup_brep, "orig_id": objref.ObjectId, "is_extracted": True})
        else:
            dup_brep = objref.Brep()
            if dup_brep is None:
                dup_brep = rs.coercebrep(objref.ObjectId)
            if dup_brep is not None:
                entries.append({"brep": dup_brep, "orig_id": objref.ObjectId, "is_extracted": False})

    extend_step = extendStepOpt.CurrentValue
    max_iter = maxIterOpt.CurrentValue
    do_reset = resetOpt.CurrentValue
    go.Dispose()
    return entries, extend_step, max_iter, do_reset


# ---------------------------------------------------------------------------
# ADJACENCE - Arbre couvrant minimal sur la distance des bounding box
# ---------------------------------------------------------------------------
def bbox_distance(bbox_a, bbox_b):
    dx = max(bbox_a.Min.X - bbox_b.Max.X, bbox_b.Min.X - bbox_a.Max.X, 0)
    dy = max(bbox_a.Min.Y - bbox_b.Max.Y, bbox_b.Min.Y - bbox_a.Max.Y, 0)
    dz = max(bbox_a.Min.Z - bbox_b.Max.Z, bbox_b.Min.Z - bbox_a.Max.Z, 0)
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def build_neighbor_pairs(breps):
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
# COMMIT DES RESULTATS DANS LE DOCUMENT
# ---------------------------------------------------------------------------
def commit_extended_surfaces(entries, mark_blue):
    new_ids = []
    for entry in entries:
        new_id = sc.doc.Objects.AddBrep(entry["brep"])
        if new_id == System.Guid.Empty:
            continue
        new_ids.append(new_id)

        if not entry["is_extracted"]:
            sc.doc.Objects.Delete(entry["orig_id"], True)

        if mark_blue:
            rs.ObjectColorSource(new_id, 1)  # 1 = ColorFromObject
            rs.ObjectColor(new_id, EXTENDED_COLOR)

    return new_ids


# ---------------------------------------------------------------------------
# COEUR DU SCRIPT
# ---------------------------------------------------------------------------
def extendAndCreateSolid(entries, extend_step=5.0, max_iter=40):
    if len(entries) < 2:
        print("Il faut au moins 2 surfaces.")
        set_pending_ids([e["orig_id"] for e in entries])
        return

    breps = [e["brep"] for e in entries]
    neighbor_pairs = build_neighbor_pairs(breps)
    print("{} couples voisins detectes (sur {} surfaces).".format(
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

        print("Iteration {} - prolongement total: {} - voisins tous en contact: {}".format(
            iteration, iteration * extend_step, all_neighbors_touch))

    for i, entry in enumerate(entries):
        entry["brep"] = breps[i]

    if not all_neighbors_touch:
        print("Echec: certains voisins ne se touchent pas apres {} iterations "
              "(prolongement max: {}).".format(max_iter, max_iter * extend_step))
        new_ids = commit_extended_surfaces(entries, mark_blue=True)
        set_pending_ids(new_ids)
        rs.SelectObjects(new_ids)
        sc.doc.Views.Redraw()
        print("{} surfaces conservees en bleu (memorisees). "
              "Relancez le script pour ajouter une surface.".format(len(new_ids)))
        return

    new_ids = commit_extended_surfaces(entries, mark_blue=False)
    sc.doc.Views.Redraw()

    ids_before = set(obj.Id for obj in sc.doc.Objects)

    rs.SelectObjects(new_ids)
    rs.Command("_CreateSolid _Enter", echo=False)

    ids_after = set(obj.Id for obj in sc.doc.Objects)
    created_ids = list(ids_after - ids_before - set(new_ids))

    solid_created = False
    for cid in created_ids:
        obj = sc.doc.Objects.Find(cid)
        if obj and obj.Geometry and isinstance(obj.Geometry, rg.Brep) and obj.Geometry.IsSolid:
            solid_created = True
            break

    if solid_created:
        for nid in new_ids:
            sc.doc.Objects.Delete(nid, True)
        clear_pending()
        sc.doc.Views.Redraw()
        print("Solide cree avec succes.")
    else:
        for nid in new_ids:
            rs.ObjectColorSource(nid, 1)
            rs.ObjectColor(nid, EXTENDED_COLOR)
        set_pending_ids(new_ids)
        rs.SelectObjects(new_ids)
        sc.doc.Views.Redraw()
        print("CreateSolid n'a pas abouti malgre le contact des voisins. "
              "Surfaces conservees en bleu (memorisees). Relancez le script pour ajouter une surface.")


# ---------------------------------------------------------------------------
# ENTREE INTERACTIVE
# ---------------------------------------------------------------------------
def RunCommand(is_interactive):
    pending_entries = get_pending_entries()

    if pending_entries:
        msg = ("{} surface(s) memorisee(s) depuis le dernier essai. "
               "Cliquer pour en ajouter, ou Entree pour relancer tel quel "
               "(options: Increment / MaxIter / ResetPending)").format(len(pending_entries))
        min_count = 0
    else:
        msg = "Selectionner les surfaces a prolonger (options: Increment / MaxIter)"
        min_count = 2

    new_entries, extend_step, max_iter, do_reset = getSurfacesWithOptions(msg, min_count=min_count)

    if do_reset:
        print("Surfaces memorisees effacees.")
        clear_pending()
        pending_entries = []

    entries = pending_entries + new_entries

    if not entries:
        print("Aucune surface selectionnee.")
        return 0

    extendAndCreateSolid(entries, extend_step, max_iter)
    return 0


if __name__ == "__main__":
    RunCommand(True)
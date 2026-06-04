# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import math

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
NB_JOINTS  = 7
KEY_ANGLE   = "JointAngle"
KEY_JOINT   = "JointIndex"
KEY_LEVEL0  = "BlockNameLevel_0"
KEY_LEVEL1  = "BlockNameLevel_1"


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES GÉOMÉTRIQUES
# ─────────────────────────────────────────────────────────────────────────────

def rotation_z(angle_deg):
    return Rhino.Geometry.Transform.Rotation(
        math.radians(angle_deg),
        Rhino.Geometry.Vector3d.ZAxis,
        Rhino.Geometry.Point3d.Origin)

def xform_to_list(xf):
    return [
        [xf.M00, xf.M01, xf.M02, xf.M03],
        [xf.M10, xf.M11, xf.M12, xf.M13],
        [xf.M20, xf.M21, xf.M22, xf.M23],
        [xf.M30, xf.M31, xf.M32, xf.M33],
    ]

def mul(a, b):
    return Rhino.Geometry.Transform.Multiply(a, b)

def try_invert(xf):
    inv = Rhino.Geometry.Transform(xf)
    if inv.TryGetInverse(inv):
        return inv
    return None

def get_instance_xform(obj_id):
    obj = sc.doc.Objects.FindId(obj_id)
    if obj is None:
        return None
    ir = obj.Geometry
    if not isinstance(ir, Rhino.Geometry.InstanceReferenceGeometry):
        return None
    return ir.Xform


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES DOCUMENT  (repris de decompose_reciproque)
# ─────────────────────────────────────────────────────────────────────────────

def get_next_instance_index(block_name):
    """Indice Y unique global pour block_name (même logique que decompose_reciproque)."""
    max_index = 0
    all_objs = rs.AllObjects()
    if not all_objs:
        return 1
    for obj in all_objs:
        keys = rs.GetUserText(obj)
        if not keys:
            continue
        for key in keys:
            if not key.startswith("BlockNameLevel_"):
                continue
            value = rs.GetUserText(obj, key)
            if value and "#" in value:
                try:
                    name_part, index_part = value.split("#", 1)
                    if name_part == block_name:
                        idx = int(index_part)
                        if idx > max_index:
                            max_index = idx
                except ValueError:
                    pass
    return max_index + 1


def create_pose_block():
    """Crée le bloc 'Pose' (trièdre RVB) s'il n'existe pas."""
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        items = []
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
        rs.EnableRedraw(True)


def decompose_block_instance(obj_id, robot_name, instance_index):
    """
    Décompose une instance de bloc (obj_id) en appliquant les UserTexts
    hiérarchiques BlockNameLevel_0 et retourne les objets issus.
    Reproduit la logique de decompose_reciproque pour le niveau 0.
    """
    if not rs.IsBlockInstance(obj_id):
        return []

    block_name = rs.BlockInstanceName(obj_id)
    if block_name == "Pose":
        return [obj_id]

    block_xform = rs.BlockInstanceXform(obj_id)

    create_pose_block()
    exploded = rs.ExplodeBlockInstance(obj_id)
    if not exploded:
        exploded = []

    pose_id = rs.InsertBlock("Pose", [0,0,0])
    rs.TransformObject(pose_id, block_xform)

    targets = list(exploded) + [pose_id]

    for item in targets:
        rs.SetUserText(item, KEY_LEVEL0, "{}#{}".format(robot_name, instance_index))

    return targets


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 – RÉSOLUTION DES ENTRÉES
# ─────────────────────────────────────────────────────────────────────────────

def resolve_input():
    """
    Retourne (robot_name, instance_index, group) où :
      - robot_name     : nom du bloc parent (ex. "GP215")
      - instance_index : indice du groupe décomposé
      - group          : dict {joint_idx (int): obj_id} des 7 instances

    Cas A – sélection valide (instance avec BlockNameLevel_0 = "Nom#N") :
        On retrouve toutes les instances du groupe #N dans le document.
        Leur position courante EST la position de repos issue de la décomposition.

    Cas B – pas de sélection valide :
        On demande le nom, on insère le bloc à l'origine, on le décompose.
        Les instances obtenues sont la position de repos.
    """
    sel = rs.SelectedObjects()

    # ── Cas A : objet sélectionné avec clé hiérarchique valide ───────────────
    if sel and len(sel) == 1:
        obj_id = sel[0]
        if rs.IsBlockInstance(obj_id):
            lv0 = rs.GetUserText(obj_id, KEY_LEVEL0)
            if lv0 and "#" in lv0:
                name_part, index_part = lv0.split("#", 1)
                try:
                    ref_index = int(index_part)
                    group = find_group_in_document(name_part, ref_index)
                    if group:
                        print(name_part, ref_index, group)
                        return name_part, ref_index, group
                except ValueError:
                    pass

    # ── Cas B : insertion + décomposition ────────────────────────────────────
    name = rs.GetString("Nom du bloc robot", "GP215")
    if not name:
        return None, None, None
    robot_name = name.strip()

    if not rs.IsBlock(robot_name):
        rs.MessageBox("Le bloc '{}' n'existe pas.".format(robot_name), 0, "Erreur")
        return None, None, None

    instance_index = get_next_instance_index(robot_name)

    # Insertion à l'origine
    parent_id = rs.InsertBlock(robot_name, [0,0,0])
    if parent_id is None:
        rs.MessageBox("Echec de l'insertion du bloc '{}'.".format(robot_name), 0, "Erreur")
        return None, None, None

    # Décomposition
    all_items = decompose_block_instance(parent_id, robot_name, instance_index)

    # Reconstruction du groupe depuis les objets issus de la décomposition
    group = {}
    for item in all_items:
        if not rs.IsBlockInstance(item):
            continue
        bname = rs.BlockInstanceName(item)
        if bname == "Pose":
            continue
        try:
            joint_idx = int(bname)
            group[joint_idx] = item
        except ValueError:
            pass

    # Vérification
    for i in range(NB_JOINTS):
        if i not in group:
            rs.MessageBox(
                "Segment {} manquant après décomposition de '{}'.".format(i, robot_name),
                0, "Erreur")
            return None, None, None

    return robot_name, instance_index, group


def find_group_in_document(robot_name, instance_index):
    """
    Retrouve dans le document les instances ayant
    BlockNameLevel_0 == "<robot_name>#<instance_index>"
    dont le nom de bloc est un entier 0–6.
    Retourne {joint_idx: obj_id} ou None.
    """
    target = "{}#{}".format(robot_name, instance_index)
    group = {}
    all_objs = rs.AllObjects()

    if not all_objs:
        return None
    for obj in all_objs:
        if not rs.IsBlockInstance(obj):
            continue
        if rs.GetUserText(obj, KEY_LEVEL0) != target:
            continue
        if not (type(rs.ObjectName(obj)) is str and rs.ObjectName(obj).isdigit()):
            continue

        joint_idx = int(rs.ObjectName(obj))
        group[joint_idx] = obj

    for i in range(NB_JOINTS):
        if i not in group:
            return None
    return group


def read_stored_angles(group):
    stored = {}
    for joint_idx, obj_id in group.items():
        angle_str = rs.GetUserText(obj_id, KEY_ANGLE)
        if angle_str is not None:
            try:
                stored[joint_idx] = float(angle_str)
            except ValueError:
                pass
    return stored


def ask_joint_angles(stored_angles):
    angles = [0.0] * NB_JOINTS
    for i in range(1, NB_JOINTS):
        default_val = stored_angles.get(i, 0.0)
        gp = Rhino.Input.Custom.GetNumber()
        gp.SetCommandPrompt("Angle articulation {} (degrés)".format(i))
        gp.SetDefaultNumber(default_val)
        if gp.Get() == Rhino.Input.GetResult.Cancel:
            return None
        angles[i] = gp.Number()
    return angles


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 – CINÉMATIQUE SÉRIE
# ─────────────────────────────────────────────────────────────────────────────

def apply_serial_kinematics(group, angles_deg, robot_name, instance_index):
    """
    Les instances du groupe sont à leur position de repos T0[i]
    (issue de la définition parente GP215, obtenue par décomposition).

    Cinématique série :
        T_local[0] = T0[0]
        T_local[i] = inv(T0[i-1]) × T0[i]      (transformée relative parent→enfant)

        W[0] = T0[0]                             (base : pas de rotation)
        W[i] = W[i-1] × Rz(angle[i]) × T_local[i]

    On applique ensuite le delta :
        delta[i] = W[i] × inv(T0[i])
    """
    # Lecture des transformées de repos
    T0 = {}
    for i in range(NB_JOINTS):
        xf = get_instance_xform(group[i])
        if xf is None:
            rs.MessageBox("Transformée illisible pour le segment {}.".format(i), 0, "Erreur")
            return False
        T0[i] = xf

    # Transformées locales parent→enfant
    T_local = {0: T0[0]}
    for i in range(1, NB_JOINTS):
        inv_parent = try_invert(T0[i - 1])
        if inv_parent is None:
            rs.MessageBox("Impossible d'inverser T0[{}].".format(i - 1), 0, "Erreur")
            return False
        T_local[i] = mul(inv_parent, T0[i])

    # Transformées monde après application des angles
    W = {0: T0[0]}
    for i in range(1, NB_JOINTS):
        W[i] = mul(W[i - 1], mul(rotation_z(angles_deg[i]), T_local[i]))

    # Application du delta et écriture des UserTexts
    for i in range(NB_JOINTS):
        obj_id = group[i]

        inv_T0 = try_invert(T0[i])
        if inv_T0 is None:
            rs.MessageBox("Impossible d'inverser T0[{}].".format(i), 0, "Erreur")
            return False

        delta = mul(W[i], inv_T0)
        rs.TransformObject(obj_id, xform_to_list(delta))

        # Clés/valeurs : angle affecté et numéro d'articulation
        rs.SetUserText(obj_id, KEY_ANGLE, str(angles_deg[i]))
        rs.SetUserText(obj_id, KEY_JOINT, str(i))
        # Rappel du robot parent
        rs.SetUserText(obj_id, KEY_LEVEL0, "{}#{}".format(robot_name, instance_index))
        rs.SetUserText(obj_id, KEY_LEVEL1, "{}#{}".format(rs.BlockInstanceName(obj_id), instance_index))

    return True


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Résolution des entrées (Cas A ou Cas B) ───────────────────────────
    robot_name, instance_index, group = resolve_input()
    if robot_name is None:
        return

    # ── 2. Angles par défaut ─────────────────────────────────────────────────
    stored_angles = read_stored_angles(group)

    # ── 3. Saisie des angles ─────────────────────────────────────────────────
    angles = ask_joint_angles(stored_angles)
    if angles is None:
        print("Opération annulée.")
        return

    # ── 4. Application de la cinématique ─────────────────────────────────────
    rs.EnableRedraw(False)
    ok = apply_serial_kinematics(group, angles, robot_name, instance_index)
    rs.EnableRedraw(True)

    if ok:
        rs.UnselectAllObjects()
        rs.SelectObjects(list(group.values()))
        print("Robot '{}#{}' positionné.".format(robot_name, instance_index))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.UI
import scriptcontext as sc
import math
import Eto.Forms as ef
import Eto.Drawing as ed

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
NB_JOINTS = 7
KEY_ANGLE  = "JointAngle"
KEY_JOINT  = "JointIndex"
KEY_LEVEL0 = "BlockNameLevel_0"
KEY_LEVEL1 = "BlockNameLevel_1"

# Limites angulaires par articulation [min, max] en degrés
JOINT_LIMITS = [
    (0,    0),      # 0 : base fixe, non utilisée
    (-180, 180),    # 1
    (-90,  90),     # 2
    (-180, 180),    # 3
    (-180, 180),    # 4
    (-135, 135),    # 5
    (-360, 360),    # 6
]


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
    """
    Inversion correcte pour IronPython / RhinoCommon.
    Transform.TryGetInverse retourne (bool, Transform) comme tuple en Python.
    """
    ok, inv = xf.TryGetInverse()
    if ok:
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
# UTILITAIRES DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_next_instance_index(block_name):
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
# LECTURE PRÉ-SÉLECTION
# ─────────────────────────────────────────────────────────────────────────────

def read_preselection():
    """Lit les GUIDs sélectionnés avant que le script ne prenne la main."""
    selected = []
    for obj in sc.doc.Objects:
        if obj.IsSelected(False) > 0:
            selected.append(obj.Id)
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 – RÉSOLUTION DES ENTRÉES
# ─────────────────────────────────────────────────────────────────────────────

def resolve_input():
    """
    Retourne (robot_name, instance_index, group).

    Cas A – pré-sélection d'une instance avec BlockNameLevel_0 valide :
        Retrouve le groupe complet. Pas d'insertion.

    Cas B – pas de pré-sélection :
        Demande le nom du bloc, demande un point d'insertion (Entrée = origine),
        insère et décompose.
    """
    # ── Cas A ────────────────────────────────────────────────────────────────
    presel = read_preselection()
    if presel:
        for obj_id in presel:
            if not rs.IsBlockInstance(obj_id):
                continue
            lv0 = rs.GetUserText(obj_id, KEY_LEVEL0)
            if not lv0 or "#" not in lv0:
                continue
            name_part, index_part = lv0.split("#", 1)
            try:
                ref_index = int(index_part)
            except ValueError:
                continue
            group = find_group_in_document(name_part, ref_index)
            if group:
                print("Cas A : robot '{}#{}' détecté.".format(name_part, ref_index))
                return name_part, ref_index, group

    # ── Cas B ────────────────────────────────────────────────────────────────
    name = rs.GetString("Nom du bloc robot", "GP215")
    if not name:
        return None, None, None
    robot_name = name.strip()

    if not rs.IsBlock(robot_name):
        rs.MessageBox("Le bloc '{}' n'existe pas.".format(robot_name), 0, "Erreur")
        return None, None, None

    instance_index = get_next_instance_index(robot_name)

    # Point d'insertion (Entrée = origine)
    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt(
        "Point d'insertion du robot '{}' (Entrée = origine)".format(robot_name))
    gp.AcceptNothing(True)
    result = gp.Get()

    if result == Rhino.Input.GetResult.Point:
        pt = gp.Point()
        insert_xform = Rhino.Geometry.Transform.Translation(pt.X, pt.Y, pt.Z)
    else:
        insert_xform = Rhino.Geometry.Transform.Identity

    # Insertion à l'origine puis déplacement
    parent_id = rs.InsertBlock(robot_name, [0, 0, 0])
    if parent_id is None:
        rs.MessageBox("Echec de l'insertion du bloc '{}'.".format(robot_name), 0, "Erreur")
        return None, None, None

    rs.TransformObject(parent_id, xform_to_list(insert_xform))

    # Décomposition
    all_items = decompose_block_instance(parent_id, robot_name, instance_index)

    # Reconstruction du groupe
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

    for i in range(NB_JOINTS):
        if i not in group:
            rs.MessageBox(
                "Segment {} manquant après décomposition de '{}'.\n"
                "Vérifiez que le bloc contient des sous-blocs nommés 0 à {}.".format(
                    i, robot_name, NB_JOINTS - 1),
                0, "Erreur")
            return None, None, None

    return robot_name, instance_index, group


def find_group_in_document(robot_name, instance_index):
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
        bname = rs.BlockInstanceName(obj)
        try:
            joint_idx = int(bname)
            group[joint_idx] = obj
        except ValueError:
            pass
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


# ─────────────────────────────────────────────────────────────────────────────
# CINÉMATIQUE (sans UI)
# ─────────────────────────────────────────────────────────────────────────────

def compute_and_apply(group, angles_deg, T0_rest, robot_name, instance_index):
    """
    Calcule et applique la cinématique série depuis les positions de repos T0_rest.
    T0_rest : dict {i: Transform} — ne change jamais pendant la session de curseurs.
    """
    T_local = {0: T0_rest[0]}
    for i in range(1, NB_JOINTS):
        inv_parent = try_invert(T0_rest[i - 1])
        if inv_parent is None:
            print("Inversion impossible T0[{}]".format(i - 1))
            return False
        T_local[i] = mul(inv_parent, T0_rest[i])

    W = {0: T0_rest[0]}
    for i in range(1, NB_JOINTS):
        W[i] = mul(W[i - 1], mul(rotation_z(angles_deg[i]), T_local[i]))

    for i in range(NB_JOINTS):
        obj_id = group[i]
        inv_T0 = try_invert(T0_rest[i])
        if inv_T0 is None:
            print("Inversion impossible W T0[{}]".format(i))
            return False
        delta = mul(W[i], inv_T0)
        rs.TransformObject(obj_id, xform_to_list(delta))
        rs.SetUserText(obj_id, KEY_ANGLE,  str(angles_deg[i]))
        rs.SetUserText(obj_id, KEY_JOINT,  str(i))
        rs.SetUserText(obj_id, KEY_LEVEL0, "{}#{}".format(robot_name, instance_index))
        rs.SetUserText(obj_id, KEY_LEVEL1, "{}#{}".format(
            rs.BlockInstanceName(obj_id), instance_index))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# BOÎTE DE DIALOGUE ETO AVEC CURSEURS
# ─────────────────────────────────────────────────────────────────────────────

class RobotPoseDialog(ef.Dialog):
    """
    Formulaire Eto : un curseur + champ numérique par articulation (1–6).
    Applique la cinématique en temps réel à chaque mouvement de curseur.
    """

    def __init__(self, group, stored_angles, T0_rest, robot_name, instance_index):
        super(RobotPoseDialog, self).__init__()

        self._group          = group
        self._T0_rest        = T0_rest
        self._robot_name     = robot_name
        self._instance_index = instance_index

        # Angles courants (index 0 inutilisé mais présent pour l'alignement)
        self._angles = [0.0] * NB_JOINTS
        for i in range(1, NB_JOINTS):
            self._angles[i] = stored_angles.get(i, 0.0)

        self._sliders  = {}   # joint_idx -> Slider
        self._spinners = {}   # joint_idx -> NumericStepper
        self._updating = False

        self._build_ui()
        self._apply_kinematics()   # Affichage initial

    # ── Construction de l'interface ──────────────────────────────────────────

    def _build_ui(self):
        self.Title   = "Pose robot – articulations"
        self.Padding = ed.Padding(12)
        self.Resizable = True

        layout = ef.TableLayout()
        layout.Spacing = ed.Size(6, 6)
        layout.Padding = ed.Padding(4)

        # En-têtes
        layout.Rows.Add(ef.TableRow(
            ef.TableCell(self._label("Articulation", bold=True)),
            ef.TableCell(self._label("Min",          bold=True)),
            ef.TableCell(self._label("Curseur",      bold=True)),
            ef.TableCell(self._label("Max",          bold=True)),
            ef.TableCell(self._label("Valeur (°)",   bold=True)),
        ))

        for i in range(1, NB_JOINTS):
            lo, hi = JOINT_LIMITS[i]

            # Slider (entier × 10 pour avoir 0.1° de résolution)
            slider = ef.Slider()
            slider.MinValue = int(lo * 10)
            slider.MaxValue = int(hi * 10)
            slider.Value    = int(self._angles[i] * 10)
            slider.Width    = 260
            slider.Tag      = i
            slider.ValueChanged += self._on_slider_changed
            self._sliders[i] = slider

            # NumericStepper
            spin = ef.NumericStepper()
            spin.MinValue     = lo
            spin.MaxValue     = hi
            spin.Value        = self._angles[i]
            spin.DecimalPlaces = 1
            spin.Increment    = 1.0
            spin.Width        = 72
            spin.Tag          = i
            spin.ValueChanged += self._on_spin_changed
            self._spinners[i] = spin

            row = ef.TableRow(
                ef.TableCell(self._label("Joint {}".format(i))),
                ef.TableCell(self._label(str(lo))),
                ef.TableCell(slider),
                ef.TableCell(self._label(str(hi))),
                ef.TableCell(spin),
            )
            layout.Rows.Add(row)

        # Boutons
        btn_ok     = ef.Button(Text="OK")
        btn_cancel = ef.Button(Text="Annuler")
        btn_ok.Click     += self._on_ok
        btn_cancel.Click += self._on_cancel

        btn_row = ef.TableRow(
            ef.TableCell(ef.Panel()),   # spacer
            ef.TableCell(ef.Panel()),
            ef.TableCell(ef.Panel()),
            ef.TableCell(btn_cancel),
            ef.TableCell(btn_ok),
        )
        layout.Rows.Add(ef.TableRow())   # ligne vide
        layout.Rows.Add(btn_row)

        self.Content = layout
        self.DefaultButton = btn_ok
        self.AbortButton   = btn_cancel

    @staticmethod
    def _label(text, bold=False):
        lbl = ef.Label(Text=text)
        if bold:
            lbl.Font = ed.Font(lbl.Font.Family, lbl.Font.Size,
                               ed.FontStyle.Bold)
        return lbl

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_slider_changed(self, sender, e):
        if self._updating:
            return
        i = sender.Tag
        val = sender.Value / 10.0
        self._angles[i] = val
        self._updating = True
        self._spinners[i].Value = val
        self._updating = False
        self._apply_kinematics()

    def _on_spin_changed(self, sender, e):
        if self._updating:
            return
        i = sender.Tag
        val = sender.Value
        self._angles[i] = val
        self._updating = True
        self._sliders[i].Value = int(val * 10)
        self._updating = False
        self._apply_kinematics()

    def _on_ok(self, sender, e):
        self.Result = True
        self.Close()

    def _on_cancel(self, sender, e):
        self.Result = False
        self.Close()

    # ── Cinématique temps réel ────────────────────────────────────────────────

    def _apply_kinematics(self):
        rs.EnableRedraw(False)
        compute_and_apply(
            self._group,
            self._angles,
            self._T0_rest,
            self._robot_name,
            self._instance_index)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

    # ── Accesseur résultat ────────────────────────────────────────────────────

    @property
    def angles(self):
        return list(self._angles)


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 1. Résolution des entrées
    robot_name, instance_index, group = resolve_input()
    if robot_name is None:
        return

    # 2. Angles stockés
    stored_angles = read_stored_angles(group)

    # 3. Capture des transformées de repos UNE SEULE FOIS
    #    (avant tout mouvement de curseur)
    T0_rest = {}
    for i in range(NB_JOINTS):
        xf = get_instance_xform(group[i])
        if xf is None:
            rs.MessageBox(
                "Transformée illisible pour le segment {}.".format(i), 0, "Erreur")
            return
        T0_rest[i] = xf

    # 4. Affichage du formulaire Eto
    dlg = RobotPoseDialog(group, stored_angles, T0_rest, robot_name, instance_index)
    rc  = dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    if rc:
        rs.UnselectAllObjects()
        rs.SelectObjects(list(group.values()))
        print("Robot '{}#{}' positionné. Angles : {}".format(
            robot_name, instance_index,
            [round(a, 1) for a in dlg.angles]))
    else:
        # Annulation : remettre à la pose de repos
        rs.EnableRedraw(False)
        for i in range(NB_JOINTS):
            xf_current = get_instance_xform(group[i])
            inv_current = try_invert(xf_current)
            if inv_current and T0_rest[i]:
                delta = mul(T0_rest[i], inv_current)
                rs.TransformObject(group[i], xform_to_list(delta))
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Annulé – pose de repos restaurée.")


if __name__ == "__main__":
    main()
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
NB_JOINTS      = 7
KEY_ANGLE      = "JointAngle"
KEY_JOINT      = "JointIndex"
KEY_LEVEL0     = "BlockNameLevel_0"
KEY_LEVEL1     = "BlockNameLevel_1"
KEY_REST_XFORM = "RestXform"       # 16 flottants séparés par ';'
KEY_MIN_ANGLE  = "minAngle"
KEY_MAX_ANGLE  = "maxAngle"

DEFAULT_MIN = -180.0
DEFAULT_MAX =  180.0


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

def xform_to_str(xf):
    """Sérialise un Transform en chaîne de 16 valeurs séparées par ';'."""
    vals = [
        xf.M00, xf.M01, xf.M02, xf.M03,
        xf.M10, xf.M11, xf.M12, xf.M13,
        xf.M20, xf.M21, xf.M22, xf.M23,
        xf.M30, xf.M31, xf.M32, xf.M33,
    ]
    return ";".join(repr(v) for v in vals)

def str_to_xform(s):
    """Désérialise un Transform depuis une chaîne de 16 valeurs."""
    try:
        vals = [float(x) for x in s.split(";")]
        if len(vals) != 16:
            return None
        xf = Rhino.Geometry.Transform()
        xf.M00 = vals[0];  xf.M01 = vals[1];  xf.M02 = vals[2];  xf.M03 = vals[3]
        xf.M10 = vals[4];  xf.M11 = vals[5];  xf.M12 = vals[6];  xf.M13 = vals[7]
        xf.M20 = vals[8];  xf.M21 = vals[9];  xf.M22 = vals[10]; xf.M23 = vals[11]
        xf.M30 = vals[12]; xf.M31 = vals[13]; xf.M32 = vals[14]; xf.M33 = vals[15]
        return xf
    except Exception:
        return None

def mul(a, b):
    return Rhino.Geometry.Transform.Multiply(a, b)

def try_invert(xf):
    """
    Inversion correcte pour IronPython / RhinoCommon.
    TryGetInverse retourne (bool, Transform) en Python.
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
    """
    Décompose le bloc parent et estampille chaque enfant avec KEY_LEVEL0.
    Retourne la liste de tous les objets créés.
    La pose de repos (RestXform) est stockée ICI, une seule fois, sur chaque enfant.
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
        # Stockage de la pose de repos absolue pour éviter la dérive
        if rs.IsBlockInstance(item):
            xf = get_instance_xform(item)
            if xf is not None:
                rs.SetUserText(item, KEY_REST_XFORM, xform_to_str(xf))

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
# RECONSTRUCTION DU GROUPE
# ─────────────────────────────────────────────────────────────────────────────

def joint_index_from_object(obj_id):
    """
    Détermine l'index d'articulation d'un objet selon la priorité :
      1. UserText KEY_JOINT  (JointIndex)
      2. Object Name  (rs.ObjectName)
      3. Block Name   (rs.BlockInstanceName) — dernier recours
    Retourne un int 0–(NB_JOINTS-1) ou None.
    """
    # Priorité 1 : clé JointIndex
    val = rs.GetUserText(obj_id, KEY_JOINT)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass

    # Priorité 2 : nom d'objet
    oname = rs.ObjectName(obj_id)
    if oname:
        try:
            return int(oname)
        except ValueError:
            pass

    # Priorité 3 : nom de bloc
    if rs.IsBlockInstance(obj_id):
        bname = rs.BlockInstanceName(obj_id)
        if bname and bname != "Pose":
            try:
                return int(bname)
            except ValueError:
                pass

    return None


def find_group_in_document(robot_name, instance_index):
    """
    Retrouve les instances ayant KEY_LEVEL0 == "<robot_name>#<instance_index>".
    L'index d'articulation est déterminé par joint_index_from_object().
    Retourne {joint_idx: obj_id} ou None si le groupe est incomplet.
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
        idx = joint_index_from_object(obj)
        if idx is None:
            continue
        if 0 <= idx < NB_JOINTS:
            group[idx] = obj

    for i in range(NB_JOINTS):
        if i not in group:
            return None
    return group


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 – RÉSOLUTION DES ENTRÉES
# ─────────────────────────────────────────────────────────────────────────────

def resolve_input():
    """
    Retourne (robot_name, instance_index, group).

    Cas A – pré-sélection d'une instance avec KEY_LEVEL0 valide :
        Retrouve le groupe. Le joint 0 fournit automatiquement le point
        d'insertion (sa RestXform ou sa xform courante).

    Cas B – pas de pré-sélection :
        Demande le nom du bloc.
        Si joint 0 du groupe précédent existe → utilise sa position.
        Sinon demande un point (Entrée = origine).
        Insère, positionne et décompose le bloc parent.
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

    # Cherche la xform du joint 0 du groupe précédent comme point d'insertion
    insert_xform = _find_previous_joint0_xform(robot_name, instance_index)

    if insert_xform is None:
        # Demande un point à l'utilisateur
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

    # Insertion à l'origine puis application de la xform d'insertion
    parent_id = rs.InsertBlock(robot_name, [0, 0, 0])
    if parent_id is None:
        rs.MessageBox("Echec de l'insertion de '{}'.".format(robot_name), 0, "Erreur")
        return None, None, None

    rs.TransformObject(parent_id, xform_to_list(insert_xform))

    # Décomposition (stocke RestXform sur chaque enfant)
    all_items = decompose_block_instance(parent_id, robot_name, instance_index)

    # Reconstruction du groupe
    group = {}
    for item in all_items:
        if not rs.IsBlockInstance(item):
            continue
        if rs.BlockInstanceName(item) == "Pose":
            continue
        idx = joint_index_from_object(item)
        if idx is not None and 0 <= idx < NB_JOINTS:
            group[idx] = item

    for i in range(NB_JOINTS):
        if i not in group:
            rs.MessageBox(
                "Segment {} manquant après décomposition de '{}'.\n"
                "Vérifiez que les sous-blocs sont nommés 0 à {}.".format(
                    i, robot_name, NB_JOINTS - 1),
                0, "Erreur")
            return None, None, None

    return robot_name, instance_index, group


def _find_previous_joint0_xform(robot_name, instance_index):
    """
    Si un groupe précédent du même robot existe, retourne la RestXform
    (ou xform courante) de son joint 0, pour réutiliser la position.
    """
    if instance_index <= 1:
        return None
    prev_group = find_group_in_document(robot_name, instance_index - 1)
    if not prev_group or 0 not in prev_group:
        return None
    # Préfère la RestXform stockée
    rest_str = rs.GetUserText(prev_group[0], KEY_REST_XFORM)
    if rest_str:
        xf = str_to_xform(rest_str)
        if xf is not None:
            return xf
    return get_instance_xform(prev_group[0])


# ─────────────────────────────────────────────────────────────────────────────
# LECTURE DES ANGLES ET LIMITES STOCKÉS
# ─────────────────────────────────────────────────────────────────────────────

def read_stored_angles(group):
    stored = {}
    for joint_idx, obj_id in group.items():
        val = rs.GetUserText(obj_id, KEY_ANGLE)
        if val is not None:
            try:
                stored[joint_idx] = float(val)
            except ValueError:
                pass
    return stored


def read_joint_limits(group):
    """
    Lit minAngle / maxAngle depuis les UserTexts de chaque instance.
    Défaut : ±180°. Joint 0 toujours (0, 0) — fixe.
    Retourne {joint_idx: (min_deg, max_deg)}.
    """
    limits = {}
    for i in range(NB_JOINTS):
        obj_id = group.get(i)
        if i == 0 or obj_id is None:
            limits[i] = (0.0, 0.0)
            continue
        try:
            lo = float(rs.GetUserText(obj_id, KEY_MIN_ANGLE) or DEFAULT_MIN)
        except (ValueError, TypeError):
            lo = DEFAULT_MIN
        try:
            hi = float(rs.GetUserText(obj_id, KEY_MAX_ANGLE) or DEFAULT_MAX)
        except (ValueError, TypeError):
            hi = DEFAULT_MAX
        limits[i] = (lo, hi)
    return limits


# ─────────────────────────────────────────────────────────────────────────────
# CINÉMATIQUE SÉRIE
# ─────────────────────────────────────────────────────────────────────────────

def compute_and_apply(group, angles_deg, T0_rest, robot_name, instance_index):
    """
    Cinématique série depuis les poses de repos T0_rest (figées à l'ouverture).

    Pour chaque articulation i :
      T_local[0] = T0_rest[0]
      T_local[i] = inv(T0_rest[i-1]) × T0_rest[i]   (offset parent→enfant)

      W[0] = T0_rest[0]
      W[i] = W[i-1] × T_local[i] × Rz(angle[i])   ← Rz POST-multiplié : repère LOCAL

    Puis delta[i] = W[i] × inv(T0_rest[i])
    On applique delta directement — T0_rest ne bouge jamais.

    NOTE : joint 0 n'a pas d'angle (fixe), W[0] = T0_rest[0].
    """
    # Transformées locales parent→enfant (calculées depuis les repos figés)
    T_local = {0: T0_rest[0]}
    for i in range(1, NB_JOINTS):
        inv_parent = try_invert(T0_rest[i - 1])
        if inv_parent is None:
            print("ERREUR : inversion impossible T0_rest[{}]".format(i - 1))
            return False
        T_local[i] = mul(inv_parent, T0_rest[i])

    # Transformées monde avec angles
    # Post-multiplication de Rz : la rotation s'applique dans le repère LOCAL
    # du joint i (autour de son propre axe Z), et non dans celui du parent.
    #   W[i] = W[i-1] × T_local[i] × Rz(angle[i])
    W = {0: T0_rest[0]}   # base fixe
    for i in range(1, NB_JOINTS):
        W[i] = mul(mul(W[i - 1], T_local[i]), rotation_z(angles_deg[i]))

    # Application : delta = W[i] × inv(T0_rest[i])
    # Cela ramène chaque segment de sa pose de repos à sa pose finale EN UNE PASSE.
    for i in range(NB_JOINTS):
        obj_id = group[i]

        inv_T0 = try_invert(T0_rest[i])
        if inv_T0 is None:
            print("ERREUR : inversion impossible T0_rest[{}] (delta)".format(i))
            return False

        delta = mul(W[i], inv_T0)

        # On repart de la pose de repos avant d'appliquer delta,
        # pour éviter toute accumulation entre deux appels successifs.
        inv_current = try_invert(get_instance_xform(obj_id))
        if inv_current is not None:
            reset = mul(T0_rest[i], inv_current)
            rs.TransformObject(obj_id, xform_to_list(reset))

        rs.TransformObject(obj_id, xform_to_list(delta))

        # Mise à jour des UserTexts
        rs.SetUserText(obj_id, KEY_ANGLE,  str(angles_deg[i]))
        rs.SetUserText(obj_id, KEY_JOINT,  str(i))
        rs.SetUserText(obj_id, KEY_LEVEL0, "{}#{}".format(robot_name, instance_index))
        rs.SetUserText(obj_id, KEY_LEVEL1, "{}#{}".format(
            rs.BlockInstanceName(obj_id), instance_index))

    return True


def restore_rest_pose(group, T0_rest):
    """Remet chaque segment à sa pose de repos (annulation)."""
    for i in range(NB_JOINTS):
        obj_id = group[i]
        xf_cur = get_instance_xform(obj_id)
        if xf_cur is None:
            continue
        inv_cur = try_invert(xf_cur)
        if inv_cur is None:
            continue
        reset = mul(T0_rest[i], inv_cur)
        rs.TransformObject(obj_id, xform_to_list(reset))


# ─────────────────────────────────────────────────────────────────────────────
# BOÎTE DE DIALOGUE ETO AVEC CURSEURS
# ─────────────────────────────────────────────────────────────────────────────

class RobotPoseDialog(ef.Dialog):
    """
    Formulaire Eto : un curseur + NumericStepper par articulation (1–6).
    Applique la cinématique en temps réel.
    Le résultat (validé ou annulé) est lu via self.validated après fermeture.
    """

    def __init__(self, group, stored_angles, joint_limits,
                 T0_rest, robot_name, instance_index):
        super(RobotPoseDialog, self).__init__()

        self._group          = group
        self._T0_rest        = T0_rest
        self._robot_name     = robot_name
        self._instance_index = instance_index
        self._limits         = joint_limits
        self._updating       = False
        self.validated       = False   # résultat lisible après fermeture

        # Angles courants
        self._angles = [0.0] * NB_JOINTS
        for i in range(1, NB_JOINTS):
            self._angles[i] = stored_angles.get(i, 0.0)

        self._sliders  = {}
        self._spinners = {}

        self._build_ui()
        self._refresh_viewport()   # Affichage initial sans toucher aux instances

    # ── Construction UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.Title     = "Pose robot – {}#{}".format(
            self._robot_name, self._instance_index)
        self.Padding   = ed.Padding(12)
        self.Resizable = True

        layout = ef.TableLayout()
        layout.Spacing = ed.Size(6, 4)

        layout.Rows.Add(ef.TableRow(
            ef.TableCell(self._lbl("Joint",      True)),
            ef.TableCell(self._lbl("Min",        True)),
            ef.TableCell(self._lbl("Curseur",    True)),
            ef.TableCell(self._lbl("Max",        True)),
            ef.TableCell(self._lbl("Angle (°)",  True)),
        ))

        for i in range(1, NB_JOINTS):
            lo, hi = self._limits[i]

            # Slider : résolution 0.1° → valeurs × 10
            slider = ef.Slider()
            slider.MinValue = int(lo * 10)
            slider.MaxValue = int(hi * 10)
            slider.Value    = int(self._angles[i] * 10)
            slider.Width    = 280
            slider.Tag      = i
            slider.ValueChanged += self._on_slider
            self._sliders[i] = slider

            # NumericStepper
            spin = ef.NumericStepper()
            spin.MinValue      = lo
            spin.MaxValue      = hi
            spin.Value         = self._angles[i]
            spin.DecimalPlaces = 1
            spin.Increment     = 1.0
            spin.Width         = 72
            spin.Tag           = i
            spin.ValueChanged  += self._on_spin
            self._spinners[i] = spin

            layout.Rows.Add(ef.TableRow(
                ef.TableCell(self._lbl("J{}".format(i))),
                ef.TableCell(self._lbl("{:.0f}".format(lo))),
                ef.TableCell(slider),
                ef.TableCell(self._lbl("{:.0f}".format(hi))),
                ef.TableCell(spin),
            ))

        # Boutons OK / Annuler
        btn_ok     = ef.Button(Text="OK")
        btn_cancel = ef.Button(Text="Annuler")
        btn_ok.Click     += self._on_ok
        btn_cancel.Click += self._on_cancel

        spacer = ef.TableCell(ef.Panel())
        layout.Rows.Add(ef.TableRow())
        layout.Rows.Add(ef.TableRow(
            spacer,
            ef.TableCell(ef.Panel()),
            ef.TableCell(ef.Panel()),
            ef.TableCell(btn_cancel),
            ef.TableCell(btn_ok),
        ))

        self.Content       = layout
        self.DefaultButton = btn_ok
        self.AbortButton   = btn_cancel

    @staticmethod
    def _lbl(text, bold=False):
        lbl = ef.Label(Text=str(text))
        if bold:
            lbl.Font = ed.Font(lbl.Font.Family, lbl.Font.Size, ed.FontStyle.Bold)
        return lbl

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_slider(self, sender, e):
        if self._updating:
            return
        i   = sender.Tag
        val = round(sender.Value / 10.0, 1)
        self._angles[i] = val
        self._updating  = True
        self._spinners[i].Value = val
        self._updating  = False
        self._refresh_viewport()

    def _on_spin(self, sender, e):
        if self._updating:
            return
        i   = sender.Tag
        val = round(sender.Value, 1)
        self._angles[i] = val
        self._updating  = True
        self._sliders[i].Value = int(val * 10)
        self._updating  = False
        self._refresh_viewport()

    def _on_ok(self, sender, e):
        self.validated = True
        self.Close()

    def _on_cancel(self, sender, e):
        self.validated = False
        self.Close()

    # ── Mise à jour viewport ─────────────────────────────────────────────────

    def _refresh_viewport(self):
        rs.EnableRedraw(False)
        compute_and_apply(
            self._group,
            self._angles,
            self._T0_rest,
            self._robot_name,
            self._instance_index)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

    # ── Accesseur ────────────────────────────────────────────────────────────

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

    # 2. Angles et limites stockés
    stored_angles = read_stored_angles(group)
    joint_limits  = read_joint_limits(group)

    # 3. Capture des poses de repos UNE SEULE FOIS
    #    On préfère la RestXform stockée (stable) ; sinon xform courante.
    T0_rest = {}
    for i in range(NB_JOINTS):
        rest_str = rs.GetUserText(group[i], KEY_REST_XFORM)
        xf = str_to_xform(rest_str) if rest_str else None
        if xf is None:
            xf = get_instance_xform(group[i])
            if xf is None:
                rs.MessageBox(
                    "Transformée illisible pour le segment {}.".format(i),
                    0, "Erreur")
                return
            # Stockage pour les sessions futures
            rs.SetUserText(group[i], KEY_REST_XFORM, xform_to_str(xf))
        T0_rest[i] = xf

    # 4. Formulaire Eto
    dlg = RobotPoseDialog(
        group, stored_angles, joint_limits,
        T0_rest, robot_name, instance_index)

    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    # 5. Résultat après fermeture (ShowModal ne retourne pas de bool fiable)
    if dlg.validated:
        # Appliquer une dernière fois avec les angles finaux du formulaire
        rs.EnableRedraw(False)
        ok = compute_and_apply(
            group, dlg.angles, T0_rest, robot_name, instance_index)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

        if ok:
            rs.UnselectAllObjects()
            rs.SelectObjects(list(group.values()))
            print("Robot '{}#{}' positionné. Angles : {}".format(
                robot_name, instance_index,
                [round(a, 1) for a in dlg.angles]))
    else:
        # Annulation : restaurer la pose de repos
        rs.EnableRedraw(False)
        restore_rest_pose(group, T0_rest)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Annulé – pose de repos restaurée.")


if __name__ == "__main__":
    main()

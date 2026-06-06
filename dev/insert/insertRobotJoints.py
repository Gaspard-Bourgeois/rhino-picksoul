# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.UI
import scriptcontext as sc
import math
import Eto.Forms as ef
import Eto.Drawing as ed

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES PARTAGÉES (issues de defineJoints)
# ─────────────────────────────────────────────────────────────────────────────
KEY_JOINT_TYPE   = "JointType"      # "fixed" | "slider" | "pivot"
KEY_JOINT_PARENT = "JointParent"    # UID de l'instance parente
KEY_INSTANCE_UID = "InstanceUID"    # UUID stable
KEY_MIN_ANGLE    = "minAngle"
KEY_MAX_ANGLE    = "maxAngle"
KEY_MIN_TRANS    = "minTrans"
KEY_MAX_TRANS    = "maxTrans"

KEY_ANGLE        = "JointAngle"     # valeur courante (angle ou translation)
KEY_LEVEL0       = "BlockNameLevel_0"
KEY_LEVEL1       = "BlockNameLevel_1"
KEY_REST_XFORM   = "RestXform"

JOINT_FIXED  = "fixed"
JOINT_SLIDER = "slider"
JOINT_PIVOT  = "pivot"

DEFAULT_MIN_ANGLE = -180.0
DEFAULT_MAX_ANGLE =  180.0
DEFAULT_MIN_TRANS =    0.0
DEFAULT_MAX_TRANS =  100.0


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES GÉOMÉTRIQUES
# ─────────────────────────────────────────────────────────────────────────────

def rotation_z(angle_deg):
    return Rhino.Geometry.Transform.Rotation(
        math.radians(angle_deg),
        Rhino.Geometry.Vector3d.ZAxis,
        Rhino.Geometry.Point3d.Origin)

def translation_z(dist):
    return Rhino.Geometry.Transform.Translation(
        Rhino.Geometry.Vector3d(0.0, 0.0, dist))

def xform_to_list(xf):
    return [
        [xf.M00, xf.M01, xf.M02, xf.M03],
        [xf.M10, xf.M11, xf.M12, xf.M13],
        [xf.M20, xf.M21, xf.M22, xf.M23],
        [xf.M30, xf.M31, xf.M32, xf.M33],
    ]

def xform_to_str(xf):
    vals = [
        xf.M00, xf.M01, xf.M02, xf.M03,
        xf.M10, xf.M11, xf.M12, xf.M13,
        xf.M20, xf.M21, xf.M22, xf.M23,
        xf.M30, xf.M31, xf.M32, xf.M33,
    ]
    return ";".join(repr(v) for v in vals)

def str_to_xform(s):
    try:
        vals = [float(x) for x in s.split(";")]
        if len(vals) != 16:
            return None
        xf = Rhino.Geometry.Transform()
        xf.M00=vals[0];  xf.M01=vals[1];  xf.M02=vals[2];  xf.M03=vals[3]
        xf.M10=vals[4];  xf.M11=vals[5];  xf.M12=vals[6];  xf.M13=vals[7]
        xf.M20=vals[8];  xf.M21=vals[9];  xf.M22=vals[10]; xf.M23=vals[11]
        xf.M30=vals[12]; xf.M31=vals[13]; xf.M32=vals[14]; xf.M33=vals[15]
        return xf
    except Exception:
        return None

def mul(a, b):
    return Rhino.Geometry.Transform.Multiply(a, b)

def try_invert(xf):
    ok, inv = xf.TryGetInverse()
    return inv if ok else None

def get_instance_xform(obj_id):
    obj = sc.doc.Objects.FindId(obj_id)
    if obj is None:
        return None
    ir = obj.Geometry
    if not isinstance(ir, Rhino.Geometry.InstanceReferenceGeometry):
        return None
    return ir.Xform


# ─────────────────────────────────────────────────────────────────────────────
# LECTURE DE LA CONFIGURATION DEPUIS LE BLOC MAÎTRE
# ─────────────────────────────────────────────────────────────────────────────

def read_master_block_config(master_block_name):
    """
    Lit la configuration cinématique depuis les sous-instances du bloc maître.
    Seules les InstanceReferenceGeometry sont retenues.

    Retourne une liste ordonnée de dicts :
    {
        'uid'      : str,           # UID stable
        'type'     : str,           # JOINT_FIXED | JOINT_SLIDER | JOINT_PIVOT
        'parent_uid': str,          # UID du parent ("" si aucun)
        'min_val'  : float,         # minAngle ou minTrans selon type
        'max_val'  : float,         # maxAngle ou maxTrans selon type
        'obj_name' : str,
        'block_name': str,
    }
    Retourne None si le bloc n'existe pas ou est vide.
    """
    if not rs.IsBlock(master_block_name):
        return None
    all_ids = rs.BlockObjects(master_block_name) or []
    configs = []
    for obj_id in all_ids:
        obj = sc.doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        if not isinstance(obj.Geometry, Rhino.Geometry.InstanceReferenceGeometry):
            continue

        uid        = rs.GetUserText(obj_id, KEY_INSTANCE_UID) or ""
        jtype      = rs.GetUserText(obj_id, KEY_JOINT_TYPE)   or JOINT_FIXED
        parent_uid = rs.GetUserText(obj_id, KEY_JOINT_PARENT) or ""
        oname      = rs.ObjectName(obj_id)          or ""
        bname      = rs.BlockInstanceName(obj_id)   or ""

        if jtype == JOINT_PIVOT:
            try:    lo = float(rs.GetUserText(obj_id, KEY_MIN_ANGLE) or DEFAULT_MIN_ANGLE)
            except: lo = DEFAULT_MIN_ANGLE
            try:    hi = float(rs.GetUserText(obj_id, KEY_MAX_ANGLE) or DEFAULT_MAX_ANGLE)
            except: hi = DEFAULT_MAX_ANGLE
        elif jtype == JOINT_SLIDER:
            try:    lo = float(rs.GetUserText(obj_id, KEY_MIN_TRANS) or DEFAULT_MIN_TRANS)
            except: lo = DEFAULT_MIN_TRANS
            try:    hi = float(rs.GetUserText(obj_id, KEY_MAX_TRANS) or DEFAULT_MAX_TRANS)
            except: hi = DEFAULT_MAX_TRANS
        else:
            lo, hi = 0.0, 0.0

        configs.append({
            "uid":        uid,
            "type":       jtype,
            "parent_uid": parent_uid,
            "min_val":    lo,
            "max_val":    hi,
            "obj_name":   oname,
            "block_name": bname,
        })

    return configs if configs else None


def build_joint_order(configs):
    """
    Trie les configs selon l'ordre topologique (parents avant enfants).
    Retourne la liste des indices originaux dans le nouvel ordre.
    """
    n = len(configs)
    uid_to_idx = {c["uid"]: i for i, c in enumerate(configs)}

    children  = {i: [] for i in range(n)}
    in_degree = {i: 0  for i in range(n)}
    for i, c in enumerate(configs):
        p_uid = c["parent_uid"]
        if p_uid and p_uid in uid_to_idx:
            p = uid_to_idx[p_uid]
            if p != i:
                children[p].append(i)
                in_degree[i] += 1

    queue = sorted(i for i in range(n) if in_degree[i] == 0)
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for child in sorted(children[node]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
    order.extend(i for i in range(n) if i not in order)
    return order


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_next_instance_index(block_name):
    max_index = 0
    all_objs = rs.AllObjects() or []
    for obj in all_objs:
        keys = rs.GetUserText(obj) or []
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


def read_preselection():
    return [obj.Id for obj in sc.doc.Objects if obj.IsSelected(False) > 0]


# ─────────────────────────────────────────────────────────────────────────────
# RECONSTRUCTION DU GROUPE DEPUIS KEY_LEVEL0 + UID
# ─────────────────────────────────────────────────────────────────────────────

def find_group_by_uid(master_name, instance_index, configs):
    """
    Retrouve les instances du document portant
    KEY_LEVEL0 == "<master_name>#<instance_index>".

    Associe chaque instance à son entrée de config via KEY_INSTANCE_UID.
    Retourne {config_idx: obj_id} ou None si incomplet.
    """
    target    = "{}#{}".format(master_name, instance_index)
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    group     = {}

    for obj_id in (rs.AllObjects() or []):
        if not rs.IsBlockInstance(obj_id):
            continue
        if rs.GetUserText(obj_id, KEY_LEVEL0) != target:
            continue
        uid = rs.GetUserText(obj_id, KEY_INSTANCE_UID) or ""
        if uid in uid_to_ci:
            group[uid_to_ci[uid]] = obj_id

    if len(group) < len(configs):
        return None
    return group


def decompose_and_stamp(obj_id, master_name, instance_index, configs):
    """
    Explose le bloc maître et estampille chaque enfant avec :
      - KEY_LEVEL0, KEY_REST_XFORM, KEY_INSTANCE_UID (copié depuis la config).
    Retourne {config_idx: obj_id} ou None.
    """
    if not rs.IsBlockInstance(obj_id):
        return None

    block_xform = rs.BlockInstanceXform(obj_id)
    create_pose_block()

    exploded = rs.ExplodeBlockInstance(obj_id) or []

    # Instance Pose (repère visuel de base)
    pose_id = rs.InsertBlock("Pose", [0, 0, 0])
    rs.TransformObject(pose_id, block_xform)
    rs.SetUserText(pose_id, KEY_LEVEL0,
                   "{}#{}".format(master_name, instance_index))
    if rs.IsBlockInstance(pose_id):
        xf = get_instance_xform(pose_id)
        if xf is not None:
            rs.SetUserText(pose_id, KEY_REST_XFORM, xform_to_str(xf))

    # Appariement exploded ↔ configs par UID
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    group = {}

    for item in exploded:
        if not rs.IsBlockInstance(item):
            continue
        uid = rs.GetUserText(item, KEY_INSTANCE_UID) or ""
        ci  = uid_to_ci.get(uid)
        if ci is None:
            continue
        rs.SetUserText(item, KEY_LEVEL0,
                       "{}#{}".format(master_name, instance_index))
        rs.SetUserText(item, KEY_LEVEL1, "{}#{}".format(
            rs.BlockInstanceName(item), instance_index))
        xf = get_instance_xform(item)
        if xf is not None:
            rs.SetUserText(item, KEY_REST_XFORM, xform_to_str(xf))
        group[ci] = item

    if len(group) < len(configs):
        rs.MessageBox(
            "Appariement incomplet après décomposition.\n"
            "Vérifiez que les InstanceUID sont définis sur chaque sous-bloc.",
            0, "Erreur")
        return None
    return group


# ─────────────────────────────────────────────────────────────────────────────
# RÉSOLUTION DES ENTRÉES
# ─────────────────────────────────────────────────────────────────────────────

def resolve_input(configs):
    """
    Cas A – pré-sélection : retrouve le groupe via KEY_LEVEL0 + UID.
    Cas B – saisie manuelle : insère, explose, estampille.
    Retourne (master_name, instance_index, group) ou (None, None, None).
    """
    presel = read_preselection()
    if presel:
        for obj_id in presel:
            if not rs.IsBlockInstance(obj_id):
                continue
            lv0 = rs.GetUserText(obj_id, KEY_LEVEL0) or ""
            if "#" not in lv0:
                continue
            master_name, idx_str = lv0.split("#", 1)
            try:
                ref_index = int(idx_str)
            except ValueError:
                continue
            # Recharge la config depuis le bon bloc maître
            cfg = read_master_block_config(master_name)
            if cfg is None:
                continue
            grp = find_group_by_uid(master_name, ref_index, cfg)
            if grp:
                print("Cas A : '{}#{}' détecté.".format(master_name, ref_index))
                return master_name, ref_index, grp, cfg

    # Cas B
    name = rs.GetString("Nom du bloc maître", "")
    if not name:
        return None, None, None, None
    master_name = name.strip()

    if not rs.IsBlock(master_name):
        rs.MessageBox("Le bloc '{}' n'existe pas.".format(master_name), 0, "Erreur")
        return None, None, None, None

    cfg = read_master_block_config(master_name)
    if cfg is None:
        rs.MessageBox(
            "Aucune configuration cinématique trouvée dans '{}'.\n"
            "Lancez d'abord defineJoints sur ce bloc.".format(master_name),
            0, "Erreur")
        return None, None, None, None

    instance_index = get_next_instance_index(master_name)

    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt(
        "Point d'insertion de '{}' (Entrée = origine)".format(master_name))
    gp.AcceptNothing(True)
    result = gp.Get()
    if result == Rhino.Input.GetResult.Point:
        pt = gp.Point()
        insert_xf = Rhino.Geometry.Transform.Translation(pt.X, pt.Y, pt.Z)
    else:
        insert_xf = Rhino.Geometry.Transform.Identity

    parent_id = rs.InsertBlock(master_name, [0, 0, 0])
    if parent_id is None:
        rs.MessageBox("Echec de l'insertion de '{}'.".format(master_name), 0, "Erreur")
        return None, None, None, None

    rs.TransformObject(parent_id, xform_to_list(insert_xf))

    grp = decompose_and_stamp(parent_id, master_name, instance_index, cfg)
    if grp is None:
        return None, None, None, None

    return master_name, instance_index, grp, cfg


# ─────────────────────────────────────────────────────────────────────────────
# LECTURE DES VALEURS COURANTES
# ─────────────────────────────────────────────────────────────────────────────

def read_stored_values(group, configs):
    """
    Retourne {config_idx: float} — valeur courante (angle ou translation).
    """
    stored = {}
    for ci, obj_id in group.items():
        val = rs.GetUserText(obj_id, KEY_ANGLE)
        if val is not None:
            try:
                stored[ci] = float(val)
            except ValueError:
                pass
    return stored


# ─────────────────────────────────────────────────────────────────────────────
# CINÉMATIQUE GÉNÉRIQUE (pivot + slider)
# ─────────────────────────────────────────────────────────────────────────────

def compute_and_apply(group, values, configs, joint_order,
                      T0_rest, master_name, instance_index):
    """
    Cinématique en chaîne ouverte depuis T0_rest (pose neutre).

    Pour chaque joint i (dans l'ordre topologique) :
      - T_local[i] = inv(T0_rest[parent]) × T0_rest[i]
      - W[i] = W[parent] × T_local[i] × J(val)
        où J(val) = Rz(val)   si pivot
                  = Tz(val)   si slider  (axe Z local)
                  = Identité  si fixed

    delta[i] = W[i] × inv(T0_rest[i])
    """
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    n = len(configs)

    # Calcul des W dans l'ordre topologique
    W = {}
    for ci in joint_order:
        c       = configs[ci]
        jtype   = c["type"]
        val     = values.get(ci, 0.0)
        p_uid   = c["parent_uid"]
        p_ci    = uid_to_ci.get(p_uid, -1)

        if p_ci < 0 or p_ci not in T0_rest:
            # Racine : W = T0_rest[ci] (base fixe, pas d'articulation)
            W[ci] = T0_rest[ci]
        else:
            inv_parent = try_invert(T0_rest[p_ci])
            if inv_parent is None:
                print("ERREUR : inversion T0_rest[{}]".format(p_ci))
                return False
            T_local = mul(inv_parent, T0_rest[ci])

            if jtype == JOINT_PIVOT:
                J = rotation_z(val)
            elif jtype == JOINT_SLIDER:
                J = translation_z(val)
            else:
                J = Rhino.Geometry.Transform.Identity

            W[ci] = mul(mul(W[p_ci], T_local), J)

    # Application des deltas
    for ci in joint_order:
        obj_id = group.get(ci)
        if obj_id is None:
            continue

        inv_T0 = try_invert(T0_rest[ci])
        if inv_T0 is None:
            print("ERREUR : inversion T0_rest[{}] (delta)".format(ci))
            return False

        delta = mul(W[ci], inv_T0)

        # Remise à la pose neutre avant application
        xf_cur = get_instance_xform(obj_id)
        if xf_cur is not None:
            inv_cur = try_invert(xf_cur)
            if inv_cur is not None:
                reset = mul(T0_rest[ci], inv_cur)
                rs.TransformObject(obj_id, xform_to_list(reset))

        rs.TransformObject(obj_id, xform_to_list(delta))

        # UserTexts
        rs.SetUserText(obj_id, KEY_ANGLE,  str(values.get(ci, 0.0)))
        rs.SetUserText(obj_id, KEY_LEVEL0, "{}#{}".format(master_name, instance_index))
        rs.SetUserText(obj_id, KEY_LEVEL1, "{}#{}".format(
            rs.BlockInstanceName(obj_id), instance_index))

    return True


# ─────────────────────────────────────────────────────────────────────────────
# BOÎTE DE DIALOGUE ETO
# ─────────────────────────────────────────────────────────────────────────────

class RobotPoseDialog(ef.Dialog):
    """
    Un curseur + NumericStepper par articulation non-fixe.
    Applique la cinématique en temps réel.
    """

    def __init__(self, group, stored_values, configs, joint_order,
                 T0_rest, master_name, instance_index):
        super(RobotPoseDialog, self).__init__()

        self._group          = group
        self._configs        = configs
        self._joint_order    = joint_order
        self._T0_rest        = T0_rest
        self._master_name    = master_name
        self._instance_index = instance_index
        self._updating       = False
        self.validated       = False

        # Valeurs courantes indexées par config_idx
        self._values = {}
        for ci, c in enumerate(configs):
            self._values[ci] = stored_values.get(ci, 0.0)

        self._sliders  = {}
        self._spinners = {}

        self._build_ui()

    # ── Construction UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.Title     = "Pose – {}#{}".format(self._master_name, self._instance_index)
        self.Padding   = ed.Padding(12)
        self.Resizable = True

        layout = ef.TableLayout()
        layout.Spacing = ed.Size(6, 4)

        layout.Rows.Add(ef.TableRow(
            ef.TableCell(self._lbl("Joint",     True)),
            ef.TableCell(self._lbl("Type",      True)),
            ef.TableCell(self._lbl("Min",       True)),
            ef.TableCell(self._lbl("Curseur",   True)),
            ef.TableCell(self._lbl("Max",       True)),
            ef.TableCell(self._lbl("Valeur",    True)),
            ef.TableCell(self._lbl("Unité",     True)),
        ))

        # Lignes dans l'ordre topologique, joints non-fixe seulement
        for ci in self._joint_order:
            c = self._configs[ci]
            if c["type"] == JOINT_FIXED:
                continue

            lo  = c["min_val"]
            hi  = c["max_val"]
            val = self._values[ci]

            # Label joint : obj_name ou block_name
            label = c["obj_name"] or c["block_name"] or "Joint {}".format(ci)

            # Unité
            unit = "°" if c["type"] == JOINT_PIVOT else "mm"

            # Slider : résolution 0.1 → ×10
            slider = ef.Slider()
            slider.MinValue = int(lo  * 10)
            slider.MaxValue = int(hi  * 10)
            slider.Value    = int(val * 10)
            slider.Width    = 260
            slider.Tag      = ci
            slider.ValueChanged += self._on_slider
            self._sliders[ci] = slider

            spin = ef.NumericStepper()
            spin.MinValue      = lo
            spin.MaxValue      = hi
            spin.Value         = val
            spin.DecimalPlaces = 1
            spin.Increment     = 1.0
            spin.Width         = 72
            spin.Tag           = ci
            spin.ValueChanged  += self._on_spin
            self._spinners[ci] = spin

            layout.Rows.Add(ef.TableRow(
                ef.TableCell(self._lbl(label)),
                ef.TableCell(self._lbl(c["type"])),
                ef.TableCell(self._lbl("{:.1f}".format(lo))),
                ef.TableCell(slider),
                ef.TableCell(self._lbl("{:.1f}".format(hi))),
                ef.TableCell(spin),
                ef.TableCell(self._lbl(unit)),
            ))

        # Boutons
        btn_ok     = ef.Button(Text="OK")
        btn_cancel = ef.Button(Text="Annuler")
        btn_ok.Click     += self._on_ok
        btn_cancel.Click += self._on_cancel

        layout.Rows.Add(ef.TableRow())
        layout.Rows.Add(ef.TableRow(
            ef.TableCell(ef.Panel()),
            ef.TableCell(ef.Panel()),
            ef.TableCell(ef.Panel()),
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
        ci  = sender.Tag
        val = round(sender.Value / 10.0, 1)
        self._values[ci] = val
        self._updating   = True
        self._spinners[ci].Value = val
        self._updating   = False
        self._refresh_viewport()

    def _on_spin(self, sender, e):
        if self._updating:
            return
        ci  = sender.Tag
        val = round(sender.Value, 1)
        self._values[ci] = val
        self._updating   = True
        self._sliders[ci].Value = int(val * 10)
        self._updating   = False
        self._refresh_viewport()

    def _on_ok(self, sender, e):
        self.validated = True
        self.Close()

    def _on_cancel(self, sender, e):
        self.validated = False
        self.Close()

    def _refresh_viewport(self):
        rs.EnableRedraw(False)
        compute_and_apply(
            self._group, self._values, self._configs, self._joint_order,
            self._T0_rest, self._master_name, self._instance_index)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

    @property
    def values(self):
        return dict(self._values)


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def moveJoints():
    # 1. Résolution des entrées (configs chargées depuis le bloc maître)
    master_name, instance_index, group, configs = resolve_input(None)
    if master_name is None:
        return

    # 2. Ordre topologique des joints
    joint_order = build_joint_order(configs)

    # 3. T0_rest depuis KEY_REST_XFORM — obligatoire
    T0_rest = {}
    for ci in range(len(configs)):
        obj_id = group.get(ci)
        if obj_id is None:
            rs.MessageBox("Instance manquante pour config {}.".format(ci), 0, "Erreur")
            return
        rest_str = rs.GetUserText(obj_id, KEY_REST_XFORM)
        xf = str_to_xform(rest_str) if rest_str else None
        if xf is None:
            rs.MessageBox(
                "RestXform manquante pour '{}' (config {}).\n"
                "Réinsérez le bloc pour initialiser la pose neutre.".format(
                    configs[ci]["obj_name"] or configs[ci]["block_name"], ci),
                0, "Erreur")
            return
        T0_rest[ci] = xf

    # 4. Valeurs stockées + capture état avant édition
    stored_values = read_stored_values(group, configs)
    values_before = {ci: stored_values.get(ci, 0.0) for ci in range(len(configs))}

    T0_before = {}
    for ci in range(len(configs)):
        xf = get_instance_xform(group[ci])
        if xf is None:
            rs.MessageBox(
                "Transformée courante illisible pour config {}.".format(ci),
                0, "Erreur")
            return
        T0_before[ci] = xf

    # 5. Application des valeurs stockées avant ouverture du dialogue
    rs.EnableRedraw(False)
    compute_and_apply(group, values_before, configs, joint_order,
                      T0_rest, master_name, instance_index)
    rs.EnableRedraw(True)
    sc.doc.Views.Redraw()

    # 6. Dialogue
    dlg = RobotPoseDialog(
        group, stored_values, configs, joint_order,
        T0_rest, master_name, instance_index)
    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    # 7. Résultat
    if dlg.validated:
        rs.EnableRedraw(False)
        ok = compute_and_apply(group, dlg.values, configs, joint_order,
                               T0_rest, master_name, instance_index)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

        if ok:
            rs.UnselectAllObjects()
            target_lv0   = "{}#{}".format(master_name, instance_index)
            all_selected = list(group.values())
            for obj in (rs.AllObjects() or []):
                if (rs.IsBlockInstance(obj)
                        and rs.BlockInstanceName(obj) == "Pose"
                        and rs.GetUserText(obj, KEY_LEVEL0) == target_lv0):
                    all_selected.append(obj)
            rs.SelectObjects(all_selected)
            print("'{}#{}' positionné : {}".format(
                master_name, instance_index,
                {configs[ci]["obj_name"] or str(ci): round(v, 1)
                 for ci, v in dlg.values.items()
                 if configs[ci]["type"] != JOINT_FIXED}))
    else:
        # Annulation : restauration exacte
        rs.EnableRedraw(False)
        for ci in range(len(configs)):
            obj_id = group[ci]
            xf_cur = get_instance_xform(obj_id)
            if xf_cur is not None:
                inv_cur = try_invert(xf_cur)
                if inv_cur is not None:
                    reset = mul(T0_before[ci], inv_cur)
                    rs.TransformObject(obj_id, xform_to_list(reset))
            rs.SetUserText(obj_id, KEY_ANGLE, str(values_before[ci]))
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Annulé – état avant édition restauré.")


if __name__ == "__main__":
    moveJoints()
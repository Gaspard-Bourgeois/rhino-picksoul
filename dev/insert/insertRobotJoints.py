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
KEY_JOINT_TYPE   = "JointType"
KEY_JOINT_PARENT = "JointParent"
KEY_INSTANCE_UID = "InstanceUID"
KEY_MIN_ANGLE    = "minAngle"
KEY_MAX_ANGLE    = "maxAngle"
KEY_MIN_TRANS    = "minTrans"
KEY_MAX_TRANS    = "maxTrans"
KEY_ANGLE        = "JointAngle"
KEY_LEVEL0       = "BlockNameLevel_0"
KEY_LEVEL1       = "BlockNameLevel_1"

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
    Retourne une liste de dicts ou None.
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
        oname      = rs.ObjectName(obj_id)        or ""
        bname      = rs.BlockInstanceName(obj_id) or ""

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

        # Xform locale dans le bloc maître (offset à angle/distance = 0)
        xf_in_master = get_instance_xform(obj_id)

        configs.append({
            "uid":          uid,
            "type":         jtype,
            "parent_uid":   parent_uid,
            "min_val":      lo,
            "max_val":      hi,
            "obj_name":     oname,
            "block_name":   bname,
            "xf_in_master": xf_in_master,  # Transform locale dans le bloc maître
        })

    return configs if configs else None


def build_joint_order(configs):
    """Tri topologique : parents avant enfants."""
    n         = len(configs)
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    children  = {i: [] for i in range(n)}
    in_degree = {i: 0  for i in range(n)}

    for i, c in enumerate(configs):
        p = uid_to_ci.get(c["parent_uid"], -1)
        if 0 <= p < n and p != i:
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
# CALCUL DE T0_REST DEPUIS LE BLOC MAÎTRE + POSITION RÉELLE DE LA RACINE
# ─────────────────────────────────────────────────────────────────────────────

def compute_t0_rest(group, configs, joint_order):
    """
    Recalcule T0_rest[ci] pour chaque joint sans KEY_REST_XFORM.

    Principe :
      - Le joint racine (FIXED, pas de parent valide) : T0_rest = xform
        absolue de l'instance dans le document.  C'est l'ancre réelle.
      - Pour les autres joints (dans l'ordre topologique) :
          T0_rest[ci] = T0_rest[parent] × inv(xf_master[parent]) × xf_master[ci]
        soit : on applique à l'offset local du bloc maître la transformation
        monde du parent à pose neutre.

    xf_master[ci] est la xform de l'objet dans la définition du bloc maître
    (stockée dans configs à la lecture).  Elle représente l'offset à val=0.
    """
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    T0_rest   = {}

    for ci in joint_order:
        c     = configs[ci]
        p_uid = c["parent_uid"]
        p_ci  = uid_to_ci.get(p_uid, -1)

        xf_master_ci = c["xf_in_master"]

        if p_ci < 0 or p_ci not in T0_rest:
            # Racine : utilise la xform absolue réelle de l'instance dans le doc
            xf_abs = get_instance_xform(group[ci])
            if xf_abs is None:
                return None
            T0_rest[ci] = xf_abs
        else:
            # Recalcul depuis le parent :
            # T0_rest[ci] = T0_rest[parent] × inv(xf_master[parent]) × xf_master[ci]
            xf_master_parent = configs[p_ci]["xf_in_master"]
            inv_master_parent = try_invert(xf_master_parent)
            if inv_master_parent is None:
                return None
            T0_rest[ci] = mul(mul(T0_rest[p_ci], inv_master_parent), xf_master_ci)

    return T0_rest


# ─────────────────────────────────────────────────────────────────────────────
# RECHERCHE DU GROUPE DÉCOMPOSÉ DANS LE DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

def find_highest_level_key(obj_id):
    """
    Retourne (clé, valeur) de BlockNameLevel_j avec j le plus élevé,
    ou (None, None).
    """
    keys     = rs.GetUserText(obj_id) or []
    best_j   = -1
    best_key = None
    best_val = None
    for key in keys:
        if not key.startswith("BlockNameLevel_"):
            continue
        try:
            j = int(key[len("BlockNameLevel_"):])
        except ValueError:
            continue
        if j > best_j:
            best_j   = j
            best_key = key
            best_val = rs.GetUserText(obj_id, key)
    return best_key, best_val


def find_decomposed_group(master_name, instance_index, configs):
    """
    Retrouve les instances décomposées portant
    BlockNameLevel_j == "<master_name>#<instance_index>"
    pour le j le plus élevé présent dans le document.

    Retourne (group, level_key) ou (None, None).
    group = {config_idx: obj_id}
    """
    target    = "{}#{}".format(master_name, instance_index)
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    candidates = {}   # j → {ci: obj_id}

    for obj_id in (rs.AllObjects() or []):
        if not rs.IsBlockInstance(obj_id):
            continue
        key, val = find_highest_level_key(obj_id)
        if val != target:
            continue
        try:
            j = int(key[len("BlockNameLevel_"):])
        except ValueError:
            continue
        uid = rs.GetUserText(obj_id, KEY_INSTANCE_UID) or ""
        ci  = uid_to_ci.get(uid, -1)
        if ci < 0:
            continue
        if j not in candidates:
            candidates[j] = {}
        candidates[j][ci] = obj_id

    if not candidates:
        return None, None

    n_configs = len(configs)
    for j in sorted(candidates.keys(), reverse=True):
        grp = candidates[j]
        if len(grp) >= n_configs:
            return grp, "BlockNameLevel_{}".format(j)

    return None, None


def check_group_coherence(group, configs):
    """Vérifie que chaque config a une instance et que le block_name concorde."""
    errors = []
    for ci, c in enumerate(configs):
        obj_id = group.get(ci)
        if obj_id is None:
            errors.append("Config {} '{}' : instance introuvable.".format(
                ci, c["obj_name"] or c["block_name"]))
            continue
        actual = rs.BlockInstanceName(obj_id) or ""
        if c["block_name"] and actual != c["block_name"]:
            errors.append("Config {} : attendu '{}', trouvé '{}'.".format(
                ci, c["block_name"], actual))
    return errors


# ─────────────────────────────────────────────────────────────────────────────
# RÉSOLUTION DES ENTRÉES
# ─────────────────────────────────────────────────────────────────────────────

def read_preselection():
    return [obj.Id for obj in sc.doc.Objects if obj.IsSelected(False) > 0]


def resolve_input():
    presel = read_preselection()

    # ── Cas A : pré-sélection ────────────────────────────────────────────────
    if presel:
        for obj_id in presel:
            if not rs.IsBlockInstance(obj_id):
                continue
            key, val = find_highest_level_key(obj_id)

            if key is None:
                rs.MessageBox(
                    "L'instance '{}' n'est pas décomposée.\n"
                    "Décomposez-la d'abord puis relancez moveJoints.".format(
                        rs.BlockInstanceName(obj_id) or "?"),
                    0, "Décomposition requise")
                return None, None, None, None, None

            if not val or "#" not in val:
                continue
            master_name, idx_str = val.split("#", 1)
            try:
                instance_index = int(idx_str)
            except ValueError:
                continue

            configs = read_master_block_config(master_name)
            if configs is None:
                rs.MessageBox(
                    "Bloc maître '{}' introuvable ou sans configuration.\n"
                    "Lancez defineJoints sur ce bloc.".format(master_name),
                    0, "Erreur")
                return None, None, None, None, None

            group, level_key = find_decomposed_group(
                master_name, instance_index, configs)
            if group is None:
                rs.MessageBox(
                    "Groupe introuvable pour '{}#{}'.".format(
                        master_name, instance_index),
                    0, "Erreur")
                return None, None, None, None, None

            errors = check_group_coherence(group, configs)
            if errors:
                rs.MessageBox(
                    "Incohérence groupe / bloc maître :\n" +
                    "\n".join(errors), 0, "Erreur de cohérence")
                return None, None, None, None, None

            print("Groupe '{}#{}' détecté ({}).".format(
                master_name, instance_index, level_key))
            return master_name, instance_index, group, configs, level_key

    # ── Cas B : saisie manuelle ──────────────────────────────────────────────
    name = rs.GetString("Nom du bloc maître (ex: GP215)")
    if not name:
        return None, None, None, None, None
    master_name = name.strip()

    configs = read_master_block_config(master_name)
    if configs is None:
        rs.MessageBox(
            "Bloc maître '{}' introuvable ou sans configuration.".format(master_name),
            0, "Erreur")
        return None, None, None, None, None

    idx_str = rs.GetString("Index de l'instance (ex: 1)")
    if not idx_str:
        return None, None, None, None, None
    try:
        instance_index = int(idx_str.strip())
    except ValueError:
        rs.MessageBox("Index invalide.", 0, "Erreur")
        return None, None, None, None, None

    group, level_key = find_decomposed_group(master_name, instance_index, configs)
    if group is None:
        rs.MessageBox(
            "Aucun groupe décomposé pour '{}#{}'.\n"
            "Décomposez d'abord l'instance.".format(master_name, instance_index),
            0, "Décomposition requise")
        return None, None, None, None, None

    errors = check_group_coherence(group, configs)
    if errors:
        rs.MessageBox(
            "Incohérence groupe / bloc maître :\n" +
            "\n".join(errors), 0, "Erreur de cohérence")
        return None, None, None, None, None

    return master_name, instance_index, group, configs, level_key


# ─────────────────────────────────────────────────────────────────────────────
# LECTURE DES VALEURS COURANTES
# ─────────────────────────────────────────────────────────────────────────────

def read_stored_values(group, configs):
    """
    Lit KEY_ANGLE sur chaque instance.
    Retourne {ci: float}, 0.0 par défaut.
    """
    stored = {}
    for ci in range(len(configs)):
        obj_id = group.get(ci)
        if obj_id is None:
            continue
        val = rs.GetUserText(obj_id, KEY_ANGLE)
        if val is not None:
            try:
                stored[ci] = float(val)
            except ValueError:
                pass
    return stored


# ─────────────────────────────────────────────────────────────────────────────
# CINÉMATIQUE GÉNÉRIQUE
# ─────────────────────────────────────────────────────────────────────────────

def compute_and_apply(group, values, configs, joint_order,
                      T0_rest, master_name, instance_index):
    """
    Cinématique en chaîne ouverte depuis T0_rest (pose neutre recalculée).

    W[racine] = T0_rest[racine]   (position absolue fixe)
    W[ci]     = W[parent] × T_local[ci] × J(val)

    T_local[ci] = inv(T0_rest[parent]) × T0_rest[ci]
    J(val)      = Rz(val) | Tz(val) | Id

    delta[ci]   = W[ci] × inv(T0_rest[ci])
    """
    uid_to_ci = {c["uid"]: i for i, c in enumerate(configs)}
    W = {}

    for ci in joint_order:
        c     = configs[ci]
        p_ci  = uid_to_ci.get(c["parent_uid"], -1)
        val   = values.get(ci, 0.0)

        if p_ci < 0 or p_ci not in T0_rest:
            W[ci] = T0_rest[ci]
        else:
            inv_p = try_invert(T0_rest[p_ci])
            if inv_p is None:
                print("ERREUR : inversion T0_rest[{}]".format(p_ci))
                return False
            T_local = mul(inv_p, T0_rest[ci])

            if c["type"] == JOINT_PIVOT:
                J = rotation_z(val)
            elif c["type"] == JOINT_SLIDER:
                J = translation_z(val)
            else:
                J = Rhino.Geometry.Transform.Identity

            W[ci] = mul(mul(W[p_ci], T_local), J)

    for ci in joint_order:
        obj_id = group.get(ci)
        if obj_id is None:
            continue
        inv_T0 = try_invert(T0_rest[ci])
        if inv_T0 is None:
            print("ERREUR : inversion T0_rest[{}]".format(ci))
            return False
        delta = mul(W[ci], inv_T0)

        # Remise à la pose neutre puis delta
        xf_cur = get_instance_xform(obj_id)
        if xf_cur is not None:
            inv_cur = try_invert(xf_cur)
            if inv_cur is not None:
                reset = mul(T0_rest[ci], inv_cur)
                rs.TransformObject(obj_id, xform_to_list(reset))

        rs.TransformObject(obj_id, xform_to_list(delta))
        rs.SetUserText(obj_id, KEY_ANGLE,  str(values.get(ci, 0.0)))
        rs.SetUserText(obj_id, KEY_LEVEL0, "{}#{}".format(master_name, instance_index))
        rs.SetUserText(obj_id, KEY_LEVEL1, "{}#{}".format(
            rs.BlockInstanceName(obj_id), instance_index))

    return True


# ─────────────────────────────────────────────────────────────────────────────
# BOÎTE DE DIALOGUE ETO
# ─────────────────────────────────────────────────────────────────────────────

class RobotPoseDialog(ef.Dialog):

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

        # Valeurs initiales : stockées ou 0
        self._values = {ci: stored_values.get(ci, 0.0)
                        for ci in range(len(configs))}

        self._sliders  = {}
        self._spinners = {}
        self._build_ui()

    def _build_ui(self):
        self.Title     = "Pose – {}#{}".format(
            self._master_name, self._instance_index)
        self.Padding   = ed.Padding(12)
        self.Resizable = True

        layout = ef.TableLayout()
        layout.Spacing = ed.Size(6, 4)

        layout.Rows.Add(ef.TableRow(
            ef.TableCell(self._lbl("Joint",   True)),
            ef.TableCell(self._lbl("Type",    True)),
            ef.TableCell(self._lbl("Min",     True)),
            ef.TableCell(self._lbl("Curseur", True)),
            ef.TableCell(self._lbl("Max",     True)),
            ef.TableCell(self._lbl("Valeur",  True)),
            ef.TableCell(self._lbl("Unité",   True)),
        ))

        for ci in self._joint_order:
            c = self._configs[ci]
            if c["type"] == JOINT_FIXED:
                continue

            lo  = c["min_val"]
            hi  = c["max_val"]
            val = self._values[ci]
            unit  = "°" if c["type"] == JOINT_PIVOT else "mm"
            label = c["obj_name"] or c["block_name"] or "J{}".format(ci)

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
    # 1. Résolution du groupe décomposé + config du bloc maître
    master_name, instance_index, group, configs, level_key = resolve_input()
    if master_name is None:
        return

    joint_order = build_joint_order(configs)

    # 2. T0_rest recalculé depuis le bloc maître + position réelle de la racine
    T0_rest = compute_t0_rest(group, configs, joint_order)
    if T0_rest is None:
        rs.MessageBox(
            "Impossible de recalculer la pose neutre.\n"
            "Vérifiez que les instances sont présentes dans le document.",
            0, "Erreur")
        return

    # 3. Valeurs courantes (KEY_ANGLE) — 0 si absentes
    stored_values = read_stored_values(group, configs)

    # 4. Capture de l'état avant édition pour restauration en cas d'annulation
    T0_before     = {}
    values_before = {ci: stored_values.get(ci, 0.0) for ci in range(len(configs))}
    for ci in range(len(configs)):
        xf = get_instance_xform(group[ci])
        if xf is None:
            rs.MessageBox(
                "Transformée courante illisible (config {}).".format(ci),
                0, "Erreur")
            return
        T0_before[ci] = xf

    # 5. Application des valeurs courantes avant ouverture du dialogue
    #    (synchronise le viewport avec les curseurs)
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
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.UI
import scriptcontext as sc
import Eto.Forms as ef
import Eto.Drawing as ed
import uuid

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
KEY_JOINT_TYPE   = "JointType"     # "fixed" | "slider" | "pivot"
KEY_JOINT_PARENT = "JointParent"   # UID de l'instance parente
KEY_INSTANCE_UID = "InstanceUID"   # UUID stable généré une fois
KEY_MIN_ANGLE    = "minAngle"
KEY_MAX_ANGLE    = "maxAngle"
KEY_MIN_TRANS    = "minTrans"
KEY_MAX_TRANS    = "maxTrans"

JOINT_FIXED  = "fixed"
JOINT_SLIDER = "slider"
JOINT_PIVOT  = "pivot"

DEFAULT_SLIDER_MIN =   0.0
DEFAULT_SLIDER_MAX = 100.0
DEFAULT_PIVOT_MIN  =   0.0
DEFAULT_PIVOT_MAX  = 360.0

# Largeurs de colonnes (px) — partagées header et lignes
COL_WIDTHS = {
    "idx":    30,
    "oname": 120,
    "bname": 130,
    "type":   90,
    "parent":210,
    "min":    80,
    "max":    80,
    "unit":   30,
}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

def resolve_block_name(raw_name):
    if "#" in raw_name:
        return raw_name.split("#", 1)[0]
    return raw_name


def ensure_uid(obj_id):
    """
    Retourne l'UID stable de l'objet.
    S'il n'existe pas encore, en génère un et le stocke.
    """
    uid = rs.GetUserText(obj_id, KEY_INSTANCE_UID)
    if not uid:
        uid = str(uuid.uuid4())
        rs.SetUserText(obj_id, KEY_INSTANCE_UID, uid)
    return uid


def get_block_instance_sub_infos(block_name):
    """
    Retourne uniquement les sous-objets de type InstanceReferenceGeometry,
    chacun enrichi d'un UID stable.
    { 'id', 'uid', 'obj_name', 'block_name' }
    """
    if not rs.IsBlock(block_name):
        return []
    all_ids = rs.BlockObjects(block_name) or []
    infos = []
    for obj_id in all_ids:
        obj = sc.doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        if not isinstance(obj.Geometry, Rhino.Geometry.InstanceReferenceGeometry):
            continue
        uid   = ensure_uid(obj_id)
        oname = rs.ObjectName(obj_id)   or ""
        bname = rs.BlockInstanceName(obj_id) or ""
        infos.append({
            "id":         obj_id,
            "uid":        uid,
            "obj_name":   oname,
            "block_name": bname,
        })
    return infos


def read_existing_keys(sub_infos):
    """
    Lit les UserTexts sur les sous-instances filtrées.
    KEY_JOINT_PARENT est un UID — résolu en index local pour l'UI.
    Retourne une liste de dicts.
    """
    uid_to_idx = {info["uid"]: i for i, info in enumerate(sub_infos)}
    result = []
    for info in sub_infos:
        obj_id = info["id"]
        jtype  = rs.GetUserText(obj_id, KEY_JOINT_TYPE) or JOINT_FIXED

        parent_uid = rs.GetUserText(obj_id, KEY_JOINT_PARENT) or ""
        parent_idx = uid_to_idx.get(parent_uid, -1)

        try:    lo_a = float(rs.GetUserText(obj_id, KEY_MIN_ANGLE) or DEFAULT_PIVOT_MIN)
        except: lo_a = DEFAULT_PIVOT_MIN
        try:    hi_a = float(rs.GetUserText(obj_id, KEY_MAX_ANGLE) or DEFAULT_PIVOT_MAX)
        except: hi_a = DEFAULT_PIVOT_MAX
        try:    lo_t = float(rs.GetUserText(obj_id, KEY_MIN_TRANS) or DEFAULT_SLIDER_MIN)
        except: lo_t = DEFAULT_SLIDER_MIN
        try:    hi_t = float(rs.GetUserText(obj_id, KEY_MAX_TRANS) or DEFAULT_SLIDER_MAX)
        except: hi_t = DEFAULT_SLIDER_MAX

        result.append({
            "type":       jtype,
            "parent_idx": parent_idx,
            "min_a": lo_a, "max_a": hi_a,
            "min_t": lo_t, "max_t": hi_t,
        })
    return result


def collect_existing_instances(block_name):
    instances = []
    for obj_id in (rs.AllObjects() or []):
        if not rs.IsBlockInstance(obj_id):
            continue
        if rs.BlockInstanceName(obj_id) != block_name:
            continue
        xf    = rs.BlockInstanceXform(obj_id)
        layer = rs.ObjectLayer(obj_id)
        keys  = rs.GetUserText(obj_id) or []
        utexts = {k: rs.GetUserText(obj_id, k) for k in keys}
        instances.append({"xform": xf, "layer": layer, "utexts": utexts})
    return instances


def write_keys_and_rebuild(block_name, sub_infos, joint_data):
    """
    Écrit les UserTexts (KEY_JOINT_PARENT = UID du parent),
    reconstruit le bloc et réinsère les instances existantes.
    """
    if len(sub_infos) != len(joint_data):
        return False

    existing = collect_existing_instances(block_name)

    for info, data in zip(sub_infos, joint_data):
        obj_id = info["id"]
        rs.SetUserText(obj_id, KEY_JOINT_TYPE, data["type"])

        pidx = data["parent_idx"]
        if 0 <= pidx < len(sub_infos):
            rs.SetUserText(obj_id, KEY_JOINT_PARENT, sub_infos[pidx]["uid"])
        else:
            rs.SetUserText(obj_id, KEY_JOINT_PARENT, "")

        if data["type"] == JOINT_PIVOT:
            rs.SetUserText(obj_id, KEY_MIN_ANGLE, str(data["min_a"]))
            rs.SetUserText(obj_id, KEY_MAX_ANGLE, str(data["max_a"]))
            rs.SetUserText(obj_id, KEY_MIN_TRANS, "")
            rs.SetUserText(obj_id, KEY_MAX_TRANS, "")
        elif data["type"] == JOINT_SLIDER:
            rs.SetUserText(obj_id, KEY_MIN_TRANS, str(data["min_t"]))
            rs.SetUserText(obj_id, KEY_MAX_TRANS, str(data["max_t"]))
            rs.SetUserText(obj_id, KEY_MIN_ANGLE, "")
            rs.SetUserText(obj_id, KEY_MAX_ANGLE, "")
        else:
            rs.SetUserText(obj_id, KEY_MIN_ANGLE, "")
            rs.SetUserText(obj_id, KEY_MAX_ANGLE, "")
            rs.SetUserText(obj_id, KEY_MIN_TRANS, "")
            rs.SetUserText(obj_id, KEY_MAX_TRANS, "")

    all_block_objs = rs.BlockObjects(block_name) or []
    rs.DeleteBlock(block_name)
    rs.AddBlock(all_block_objs, Rhino.Geometry.Point3d.Origin, block_name, False)

    for inst in existing:
        new_id = rs.InsertBlock(block_name, [0, 0, 0])
        if new_id is None:
            continue
        rs.TransformObject(new_id, inst["xform"])
        try:    rs.ObjectLayer(new_id, inst["layer"])
        except: pass
        for k, v in inst["utexts"].items():
            if v:
                rs.SetUserText(new_id, k, v)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# ORDONNANCEMENT TOPOLOGIQUE
# ─────────────────────────────────────────────────────────────────────────────

def topological_sort(n, data_list):
    children  = {i: [] for i in range(n)}
    in_degree = {i: 0  for i in range(n)}
    for i, data in enumerate(data_list):
        p = data.get("parent_idx", -1)
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
# BOÎTE DE DIALOGUE ETO
# ─────────────────────────────────────────────────────────────────────────────

class JointDefDialog(ef.Dialog):

    def __init__(self, block_name, sub_infos, existing_data):
        super(JointDefDialog, self).__init__()

        self._block_name = block_name
        self._sub_infos  = sub_infos
        self._n          = len(sub_infos)
        self.validated   = False

        self._data = []
        for i in range(self._n):
            if i < len(existing_data):
                self._data.append(dict(existing_data[i]))
            else:
                self._data.append({
                    "type": JOINT_FIXED, "parent_idx": -1,
                    "min_a": DEFAULT_PIVOT_MIN,  "max_a": DEFAULT_PIVOT_MAX,
                    "min_t": DEFAULT_SLIDER_MIN, "max_t": DEFAULT_SLIDER_MAX,
                })

        self._order = list(range(self._n))

        self._type_drops   = [None] * self._n
        self._parent_drops = [None] * self._n
        self._min_spins    = [None] * self._n
        self._max_spins    = [None] * self._n
        self._unit_labels  = [None] * self._n
        self._idx_labels   = [None] * self._n
        self._row_panels   = [None] * self._n
        self._scroll       = None

        self._build_ui()
        self._refresh_order()

    # ── Construction UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.Title       = "Liaisons cinématiques – {}".format(self._block_name)
        self.Padding     = ed.Padding(10)
        self.Resizable   = True
        self.MinimumSize = ed.Size(820, 400)

        outer = ef.DynamicLayout()
        outer.Spacing = ed.Size(0, 4)

        # ── En-tête : même structure de cellules que les lignes ──────────────
        outer.AddRow(self._build_header())

        # ── Lignes dans scroll ───────────────────────────────────────────────
        self._rows_layout = ef.DynamicLayout()
        self._rows_layout.Spacing = ed.Size(0, 2)
        for i in range(self._n):
            panel = self._build_row(i)
            self._row_panels[i] = panel
            self._rows_layout.AddRow(panel)

        scroll = ef.Scrollable()
        scroll.Content             = self._rows_layout
        scroll.ExpandContentHeight = False
        scroll.Height              = min(36 * self._n + 16, 520)
        self._scroll = scroll
        outer.AddRow(scroll)

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_ok     = ef.Button(Text="OK")
        btn_cancel = ef.Button(Text="Annuler")
        btn_ok.Click     += self._on_ok
        btn_cancel.Click += self._on_cancel

        btn_panel = ef.DynamicLayout()
        btn_panel.Spacing = ed.Size(6, 0)
        btn_panel.BeginHorizontal()
        btn_panel.AddSpace()
        btn_panel.Add(btn_cancel)
        btn_panel.Add(btn_ok)
        btn_panel.EndHorizontal()
        outer.AddRow(btn_panel)

        self.Content       = outer
        self.DefaultButton = btn_ok
        self.AbortButton   = btn_cancel

    def _make_row_layout(self, cells):
        """
        Construit un TableLayout horizontal à partir d'une liste de contrôles,
        en appliquant COL_WIDTHS dans l'ordre des colonnes.
        cells : liste de (contrôle, clé_largeur)
        """
        tl = ef.TableLayout()
        tl.Spacing = ed.Size(6, 0)
        tl.Padding = ed.Padding(2, 1)
        row = ef.TableRow()
        for ctrl, wkey in cells:
            w = COL_WIDTHS.get(wkey, 80)
            ctrl.Width = w
            row.Cells.Add(ef.TableCell(ctrl, False))
        tl.Rows.Add(row)
        panel = ef.Panel()
        panel.Content = tl
        return panel

    def _build_header(self):
        labels = [
            ("#",           "idx"),
            ("Nom objet",   "oname"),
            ("Nom bloc",    "bname"),
            ("Liaison",     "type"),
            ("Parent",      "parent"),
            ("Min",         "min"),
            ("Max",         "max"),
            ("Unité",       "unit"),
        ]
        cells = []
        for text, wkey in labels:
            lbl = ef.Label(Text=text)
            lbl.Font = ed.Font(lbl.Font.Family, lbl.Font.Size, ed.FontStyle.Bold)
            cells.append((lbl, wkey))
        return self._make_row_layout(cells)

    def _build_row(self, i):
        info = self._sub_infos[i]
        d    = self._data[i]

        # Colonne #
        idx_lbl      = ef.Label(Text="")
        self._idx_labels[i] = idx_lbl

        # Nom objet / Nom bloc
        lbl_oname = ef.Label(Text=info["obj_name"]   or "—")
        lbl_bname = ef.Label(Text=info["block_name"] or "—")

        # Type
        drop = ef.DropDown()
        for t in [JOINT_FIXED, JOINT_SLIDER, JOINT_PIVOT]:
            drop.Items.Add(t)
        drop.SelectedKey = d["type"]
        drop.Tag         = i
        drop.SelectedIndexChanged += self._on_type_changed
        self._type_drops[i] = drop

        # Parent — exclut self
        pdrop = ef.DropDown()
        pdrop.Items.Add("— aucun —")
        for j, other in enumerate(self._sub_infos):
            if j == i:
                continue   # une instance ne peut pas être son propre parent
            label = "{} / {}".format(
                other["obj_name"]   or "—",
                other["block_name"] or "—")
            pdrop.Items.Add(label)
        # Mapping : SelectedIndex dans pdrop → index original
        # pdrop index 0 = aucun ; 1..n-1 = les autres dans ordre naturel sans i
        pidx = d["parent_idx"]
        pdrop.SelectedIndex = self._orig_to_pdrop(i, pidx)
        pdrop.Tag = i
        pdrop.SelectedIndexChanged += self._on_parent_changed
        self._parent_drops[i] = pdrop

        # Min / Max
        min_spin = ef.NumericStepper()
        max_spin = ef.NumericStepper()
        for sp in (min_spin, max_spin):
            sp.DecimalPlaces = 2
            sp.Increment     = 1.0
        self._min_spins[i] = min_spin
        self._max_spins[i] = max_spin
        self._apply_limits_to_spinners(i)

        # Unité
        unit_lbl = ef.Label(Text=self._unit_for(d["type"]))
        self._unit_labels[i] = unit_lbl

        self._set_row_enabled(i, d["type"])

        cells = [
            (idx_lbl,  "idx"),
            (lbl_oname,"oname"),
            (lbl_bname,"bname"),
            (drop,     "type"),
            (pdrop,    "parent"),
            (min_spin, "min"),
            (max_spin, "max"),
            (unit_lbl, "unit"),
        ]
        return self._make_row_layout(cells)

    # ── Mapping DropDown parent ↔ index original ─────────────────────────────

    def _pdrop_entries(self, self_idx):
        """
        Retourne la liste des index originaux dans l'ordre du DropDown parent
        de la ligne self_idx (index 0 du drop = aucun, donc décalé de 1).
        """
        return [j for j in range(self._n) if j != self_idx]

    def _orig_to_pdrop(self, self_idx, orig_idx):
        """orig_idx → SelectedIndex dans le DropDown (0 = aucun)."""
        if orig_idx < 0:
            return 0
        entries = self._pdrop_entries(self_idx)
        try:
            return entries.index(orig_idx) + 1
        except ValueError:
            return 0

    def _pdrop_to_orig(self, self_idx, selected_index):
        """SelectedIndex dans le DropDown → orig_idx (-1 si aucun)."""
        if selected_index <= 0:
            return -1
        entries = self._pdrop_entries(self_idx)
        idx = selected_index - 1
        if 0 <= idx < len(entries):
            return entries[idx]
        return -1

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _unit_for(jtype):
        return "°" if jtype == JOINT_PIVOT else ("mm" if jtype == JOINT_SLIDER else "")

    def _apply_limits_to_spinners(self, i):
        d  = self._data[i]
        ms = self._min_spins[i]
        xs = self._max_spins[i]
        if d["type"] == JOINT_PIVOT:
            for sp in (ms, xs): sp.MinValue, sp.MaxValue = -720.0, 720.0
            ms.Value, xs.Value = d["min_a"], d["max_a"]
        elif d["type"] == JOINT_SLIDER:
            for sp in (ms, xs): sp.MinValue, sp.MaxValue = -10000.0, 10000.0
            ms.Value, xs.Value = d["min_t"], d["max_t"]
        else:
            ms.Value = xs.Value = 0.0

    def _set_row_enabled(self, i, jtype):
        enabled = jtype != JOINT_FIXED
        self._parent_drops[i].Enabled = enabled
        self._min_spins[i].Enabled    = enabled
        self._max_spins[i].Enabled    = enabled

    # ── Ordonnancement ───────────────────────────────────────────────────────

    def _refresh_order(self):
        self._order = topological_sort(self._n, self._data)
        new_layout = ef.DynamicLayout()
        new_layout.Spacing = ed.Size(0, 2)
        for pos, orig_idx in enumerate(self._order):
            self._idx_labels[orig_idx].Text = str(pos + 1)
            new_layout.AddRow(self._row_panels[orig_idx])
        self._scroll.Content = new_layout

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_type_changed(self, sender, e):
        i     = sender.Tag
        jtype = sender.SelectedKey or JOINT_FIXED
        self._data[i]["type"] = jtype
        if jtype == JOINT_PIVOT:
            self._data[i]["min_a"] = DEFAULT_PIVOT_MIN
            self._data[i]["max_a"] = DEFAULT_PIVOT_MAX
        elif jtype == JOINT_SLIDER:
            self._data[i]["min_t"] = DEFAULT_SLIDER_MIN
            self._data[i]["max_t"] = DEFAULT_SLIDER_MAX
        self._apply_limits_to_spinners(i)
        self._unit_labels[i].Text = self._unit_for(jtype)
        self._set_row_enabled(i, jtype)
        self._refresh_order()

    def _on_parent_changed(self, sender, e):
        i    = sender.Tag
        orig = self._pdrop_to_orig(i, sender.SelectedIndex)
        self._data[i]["parent_idx"] = orig
        self._refresh_order()

    def _on_ok(self, sender, e):
        for i in range(self._n):
            jtype = self._type_drops[i].SelectedKey or JOINT_FIXED
            orig  = self._pdrop_to_orig(i, self._parent_drops[i].SelectedIndex)
            self._data[i]["type"]       = jtype
            self._data[i]["parent_idx"] = orig
            if jtype == JOINT_PIVOT:
                self._data[i]["min_a"] = self._min_spins[i].Value
                self._data[i]["max_a"] = self._max_spins[i].Value
            elif jtype == JOINT_SLIDER:
                self._data[i]["min_t"] = self._min_spins[i].Value
                self._data[i]["max_t"] = self._max_spins[i].Value

        errors = []
        for i in range(self._n):
            d    = self._data[i]
            name = self._sub_infos[i]["obj_name"] or self._sub_infos[i]["block_name"] or str(i)
            if d["type"] != JOINT_FIXED and d["parent_idx"] < 0:
                errors.append("'{}' : parent requis pour liaison '{}'.".format(name, d["type"]))
            if d["type"] != JOINT_FIXED:
                lo = d["min_a"] if d["type"] == JOINT_PIVOT else d["min_t"]
                hi = d["max_a"] if d["type"] == JOINT_PIVOT else d["max_t"]
                if lo >= hi:
                    errors.append("'{}' : Min doit être < Max.".format(name))
        if errors:
            rs.MessageBox("\n".join(errors), 0, "Erreurs de validation")
            return

        self.validated = True
        self.Close()

    def _on_cancel(self, sender, e):
        self.validated = False
        self.Close()

    @property
    def joint_data(self):
        return [dict(d) for d in self._data]


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    presel   = [obj.Id for obj in sc.doc.Objects if obj.IsSelected(False) > 0]
    raw_name = None
    if presel:
        for obj_id in presel:
            if rs.IsBlockInstance(obj_id):
                raw_name = rs.BlockInstanceName(obj_id)
                break
    if raw_name is None:
        raw_name = rs.GetString("Nom du bloc à configurer")
        if not raw_name:
            return

    block_name = resolve_block_name(raw_name.strip())
    if not rs.IsBlock(block_name):
        rs.MessageBox("Le bloc '{}' n'existe pas.".format(block_name), 0, "Erreur")
        return

    sub_infos = get_block_instance_sub_infos(block_name)
    if not sub_infos:
        rs.MessageBox(
            "Le bloc '{}' ne contient aucune sous-instance.".format(block_name),
            0, "Erreur")
        return

    existing_data = read_existing_keys(sub_infos)

    dlg = JointDefDialog(block_name, sub_infos, existing_data)
    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    if not dlg.validated:
        print("Annulé – aucune modification.")
        return

    ok = write_keys_and_rebuild(block_name, sub_infos, dlg.joint_data)
    if ok:
        sc.doc.Views.Redraw()
        print("Bloc '{}' mis à jour.".format(block_name))
        for i, d in enumerate(dlg.joint_data):
            pidx = d["parent_idx"]
            pname = (sub_infos[pidx]["obj_name"] or sub_infos[pidx]["block_name"]) \
                    if pidx >= 0 else "—"
            if d["type"] == JOINT_PIVOT:
                limit_str = " [{:.1f}°…{:.1f}°]".format(d["min_a"], d["max_a"])
            elif d["type"] == JOINT_SLIDER:
                limit_str = " [{:.1f}…{:.1f} mm]".format(d["min_t"], d["max_t"])
            else:
                limit_str = ""
            print("  {} / {} : {} → {}{}".format(
                sub_infos[i]["obj_name"]   or "—",
                sub_infos[i]["block_name"] or "—",
                d["type"], pname, limit_str))
    else:
        rs.MessageBox(
            "Erreur lors de la reconstruction du bloc '{}'.".format(block_name),
            0, "Erreur")


if __name__ == "__main__":
    main()
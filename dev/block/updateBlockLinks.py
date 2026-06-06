# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import Rhino.UI
import scriptcontext as sc
import Eto.Forms as ef
import Eto.Drawing as ed

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
KEY_JOINT_TYPE   = "JointType"     # "fixed" | "slider" | "pivot"
KEY_JOINT_PARENT = "JointParent"   # index positionnel 0-based dans le bloc (int str)
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


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES DOCUMENT
# ─────────────────────────────────────────────────────────────────────────────

def resolve_block_name(raw_name):
    if "#" in raw_name:
        return raw_name.split("#", 1)[0]
    return raw_name


def get_block_instance_sub_infos(block_name):
    """
    Retourne uniquement les sous-objets de type InstanceReferenceGeometry.
    Chaque entrée : { 'id', 'obj_name', 'block_name', 'pos_index' }
    pos_index = index dans la liste filtrée (0-based), stable comme clé de parenté.
    """
    if not rs.IsBlock(block_name):
        return []
    all_ids = rs.BlockObjects(block_name) or []
    infos   = []
    for obj_id in all_ids:
        obj = sc.doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        if not isinstance(obj.Geometry, Rhino.Geometry.InstanceReferenceGeometry):
            continue
        oname = rs.ObjectName(obj_id) or ""
        bname = rs.BlockInstanceName(obj_id) or ""
        infos.append({
            "id":         obj_id,
            "obj_name":   oname,
            "block_name": bname,
        })
    # Ajout de pos_index après filtrage
    for i, info in enumerate(infos):
        info["pos_index"] = i
    return infos


def read_existing_keys(block_name, n_instances):
    """
    Lit les UserTexts sur les sous-instances filtrées.
    KEY_JOINT_PARENT est un index positionnel (int str) — indépendant des noms.
    Retourne une liste de dicts, un par instance filtrée.
    """
    if not rs.IsBlock(block_name):
        return []
    all_ids = rs.BlockObjects(block_name) or []
    # On refiltre dans le même ordre que get_block_instance_sub_infos
    filtered = []
    for obj_id in all_ids:
        obj = sc.doc.Objects.FindId(obj_id)
        if obj is None:
            continue
        if not isinstance(obj.Geometry, Rhino.Geometry.InstanceReferenceGeometry):
            continue
        filtered.append(obj_id)

    result = []
    for obj_id in filtered:
        jtype = rs.GetUserText(obj_id, KEY_JOINT_TYPE) or JOINT_FIXED
        # Parent stocké comme index positionnel (str d'un int)
        parent_raw = rs.GetUserText(obj_id, KEY_JOINT_PARENT) or ""
        try:
            parent_idx = int(parent_raw)
            if parent_idx < 0 or parent_idx >= n_instances:
                parent_idx = -1
        except (ValueError, TypeError):
            parent_idx = -1

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
            "parent_idx": parent_idx,   # int, -1 = aucun
            "min_a": lo_a, "max_a": hi_a,
            "min_t": lo_t, "max_t": hi_t,
        })
    return result


def collect_existing_instances(block_name):
    """Sauvegarde toutes les instances du bloc dans le document pour réinsertion."""
    instances = []
    all_objs  = rs.AllObjects() or []
    for obj_id in all_objs:
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
    Écrit les UserTexts (parent = index positionnel),
    reconstruit le bloc et réinsère les instances existantes.
    """
    obj_ids = [info["id"] for info in sub_infos]
    if len(obj_ids) != len(joint_data):
        return False

    existing = collect_existing_instances(block_name)

    for obj_id, data in zip(obj_ids, joint_data):
        rs.SetUserText(obj_id, KEY_JOINT_TYPE, data["type"])
        # Stockage de l'index positionnel (indépendant des noms)
        pidx = data["parent_idx"]
        rs.SetUserText(obj_id, KEY_JOINT_PARENT, str(pidx) if pidx >= 0 else "")

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

    # Reconstruction
    all_block_objs = rs.BlockObjects(block_name) or []
    rs.DeleteBlock(block_name)
    rs.AddBlock(all_block_objs, Rhino.Geometry.Point3d.Origin, block_name, False)

    # Réinsertion aux emplacements d'origine
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
    """
    Trie les indices 0..n-1 selon l'ordre topologique (parents avant enfants).
    data_list[i]['parent_idx'] = int index du parent, -1 si aucun.
    """
    children  = {i: [] for i in range(n)}
    in_degree = {i: 0  for i in range(n)}

    for i, data in enumerate(data_list):
        p = data.get("parent_idx", -1)
        if 0 <= p < n and p != i:
            children[p].append(i)
            in_degree[i] += 1

    queue = sorted([i for i in range(n) if in_degree[i] == 0])
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for child in sorted(children[node]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Cycle éventuel
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

        # État interne indexé par pos_index original
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

        # Widgets par index original
        self._type_drops   = [None] * self._n
        self._parent_drops = [None] * self._n
        self._min_spins    = [None] * self._n
        self._max_spins    = [None] * self._n
        self._unit_labels  = [None] * self._n
        self._idx_labels   = [None] * self._n
        self._row_panels   = [None] * self._n

        self._scroll = None
        self._build_ui()
        self._refresh_order()

    # ── Construction UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.Title       = "Liaisons cinématiques – {}".format(self._block_name)
        self.Padding     = ed.Padding(10)
        self.Resizable   = True
        self.MinimumSize = ed.Size(900, 400)

        outer = ef.DynamicLayout()
        outer.Spacing = ed.Size(0, 6)

        # En-têtes
        header = ef.TableLayout()
        header.Spacing = ed.Size(6, 0)
        header.Rows.Add(ef.TableRow(
            ef.TableCell(self._lbl("#",           True), False),
            ef.TableCell(self._lbl("Nom objet",   True), False),
            ef.TableCell(self._lbl("Nom bloc",    True), True),
            ef.TableCell(self._lbl("Liaison",     True), False),
            ef.TableCell(self._lbl("Parent (#)",  True), False),
            ef.TableCell(self._lbl("Min",         True), False),
            ef.TableCell(self._lbl("Max",         True), False),
            ef.TableCell(self._lbl("Unité",       True), False),
        ))
        outer.AddRow(header)

        # Lignes dans un ScrollArea
        self._rows_layout = ef.DynamicLayout()
        self._rows_layout.Spacing = ed.Size(0, 2)
        for i in range(self._n):
            panel = self._build_row(i)
            self._row_panels[i] = panel
            self._rows_layout.AddRow(panel)

        scroll = ef.Scrollable()
        scroll.Content             = self._rows_layout
        scroll.ExpandContentHeight = False
        scroll.Height              = min(40 * self._n + 20, 520)
        self._scroll = scroll
        outer.AddRow(scroll)

        # Boutons
        btn_ok     = ef.Button(Text="OK")
        btn_cancel = ef.Button(Text="Annuler")
        btn_ok.Click     += self._on_ok
        btn_cancel.Click += self._on_cancel

        btn_row = ef.TableLayout()
        btn_row.Spacing = ed.Size(6, 0)
        btn_row.Rows.Add(ef.TableRow(
            ef.TableCell(ef.Panel(), True),
            ef.TableCell(btn_cancel, False),
            ef.TableCell(btn_ok,     False),
        ))
        outer.AddRow(btn_row)

        self.Content       = outer
        self.DefaultButton = btn_ok
        self.AbortButton   = btn_cancel

    def _build_row(self, i):
        info = self._sub_infos[i]
        d    = self._data[i]

        # Label numéro (mis à jour par _refresh_order)
        idx_lbl = ef.Label(Text="")
        idx_lbl.Width       = 24
        self._idx_labels[i] = idx_lbl

        # Colonnes nom objet / nom bloc séparées
        lbl_oname = ef.Label(Text=info["obj_name"]   or "—")
        lbl_bname = ef.Label(Text=info["block_name"] or "—")
        lbl_oname.Width = 120
        lbl_bname.Width = 140

        # DropDown type
        drop = ef.DropDown()
        for t in [JOINT_FIXED, JOINT_SLIDER, JOINT_PIVOT]:
            drop.Items.Add(t)
        drop.SelectedKey = d["type"]
        drop.Width       = 80
        drop.Tag         = i
        drop.SelectedIndexChanged += self._on_type_changed
        self._type_drops[i] = drop

        # DropDown parent : affiche "#pos_index  obj_name (block_name)"
        pdrop = ef.DropDown()
        pdrop.Items.Add("— aucun —")
        for j, other in enumerate(self._sub_infos):
            label = "#{} {} ({})".format(
                j,
                other["obj_name"]   or "—",
                other["block_name"] or "—")
            pdrop.Items.Add(label)
        # Sélection initiale depuis parent_idx stocké
        pidx = d["parent_idx"]
        pdrop.SelectedIndex = (pidx + 1) if 0 <= pidx < self._n else 0
        pdrop.Width = 200
        pdrop.Tag   = i
        pdrop.SelectedIndexChanged += self._on_parent_changed
        self._parent_drops[i] = pdrop

        # Min / Max
        min_spin = ef.NumericStepper()
        max_spin = ef.NumericStepper()
        for sp in (min_spin, max_spin):
            sp.DecimalPlaces = 2
            sp.Increment     = 1.0
            sp.Width         = 80
        self._min_spins[i] = min_spin
        self._max_spins[i] = max_spin
        self._apply_limits_to_spinners(i)

        # Unité
        unit_lbl = ef.Label(Text=self._unit_for(d["type"]))
        unit_lbl.Width       = 24
        self._unit_labels[i] = unit_lbl

        self._set_row_enabled(i, d["type"])

        row_tl = ef.TableLayout()
        row_tl.Spacing = ed.Size(6, 0)
        row_tl.Rows.Add(ef.TableRow(
            ef.TableCell(idx_lbl,   False),
            ef.TableCell(lbl_oname, False),
            ef.TableCell(lbl_bname, True),
            ef.TableCell(drop,      False),
            ef.TableCell(pdrop,     False),
            ef.TableCell(min_spin,  False),
            ef.TableCell(max_spin,  False),
            ef.TableCell(unit_lbl,  False),
        ))

        panel = ef.Panel()
        panel.Content = row_tl
        panel.Tag     = i
        return panel

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _lbl(text, bold=False):
        lbl = ef.Label(Text=str(text))
        if bold:
            lbl.Font = ed.Font(lbl.Font.Family, lbl.Font.Size, ed.FontStyle.Bold)
        return lbl

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
        sidx = sender.SelectedIndex   # 0 = aucun, 1-based sinon
        self._data[i]["parent_idx"] = (sidx - 1) if sidx > 0 else -1
        self._refresh_order()

    def _on_ok(self, sender, e):
        for i in range(self._n):
            jtype = self._type_drops[i].SelectedKey or JOINT_FIXED
            sidx  = self._parent_drops[i].SelectedIndex
            self._data[i]["type"]       = jtype
            self._data[i]["parent_idx"] = (sidx - 1) if sidx > 0 else -1
            if jtype == JOINT_PIVOT:
                self._data[i]["min_a"] = self._min_spins[i].Value
                self._data[i]["max_a"] = self._max_spins[i].Value
            elif jtype == JOINT_SLIDER:
                self._data[i]["min_t"] = self._min_spins[i].Value
                self._data[i]["max_t"] = self._max_spins[i].Value

        errors = []
        for i in range(self._n):
            d = self._data[i]
            if d["type"] != JOINT_FIXED and d["parent_idx"] < 0:
                errors.append("Instance {} '{}' : parent requis pour liaison '{}'.".format(
                    i, self._sub_infos[i]["obj_name"] or self._sub_infos[i]["block_name"],
                    d["type"]))
            if d["type"] != JOINT_FIXED:
                lo = d["min_a"] if d["type"] == JOINT_PIVOT else d["min_t"]
                hi = d["max_a"] if d["type"] == JOINT_PIVOT else d["max_t"]
                if lo >= hi:
                    errors.append("Instance {} '{}' : Min doit être < Max.".format(
                        i, self._sub_infos[i]["obj_name"] or self._sub_infos[i]["block_name"]))
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

    existing_data = read_existing_keys(block_name, len(sub_infos))

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
            parent_str = " → #{}".format(pidx) if pidx >= 0 else ""
            if d["type"] == JOINT_PIVOT:
                limit_str = " [{:.1f}°…{:.1f}°]".format(d["min_a"], d["max_a"])
            elif d["type"] == JOINT_SLIDER:
                limit_str = " [{:.1f}…{:.1f} mm]".format(d["min_t"], d["max_t"])
            else:
                limit_str = ""
            print("  [{}] {} / {} : {}{}{}".format(
                i,
                sub_infos[i]["obj_name"]   or "—",
                sub_infos[i]["block_name"] or "—",
                d["type"], parent_str, limit_str))
    else:
        rs.MessageBox(
            "Erreur lors de la reconstruction du bloc '{}'.".format(block_name),
            0, "Erreur")


if __name__ == "__main__":
    main()
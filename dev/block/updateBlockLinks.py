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
KEY_JOINT_TYPE   = "JointType"    # "fixed" | "slider" | "pivot"
KEY_JOINT_PARENT = "JointParent"  # nom de l'instance parente
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


def get_block_sub_infos(block_name):
    """
    Retourne une liste de dicts par sous-instance :
      { 'id': guid, 'display': str, 'obj_name': str, 'block_name': str }
    'display' = "obj_name (block_name)" avec fallback si l'un est absent.
    """
    if not rs.IsBlock(block_name):
        return []
    obj_ids = rs.BlockObjects(block_name)
    if not obj_ids:
        return []
    infos = []
    for obj in obj_ids:
        oname = rs.ObjectName(obj) or ""
        bname = ""
        if rs.IsBlockInstance(obj):
            bname = rs.BlockInstanceName(obj) or ""
        if oname and bname and oname != bname:
            display = "{} ({})".format(oname, bname)
        elif oname:
            display = oname
        elif bname:
            display = "({})".format(bname)
        else:
            display = "(sans nom)"
        infos.append({
            "id":         obj,
            "display":    display,
            "obj_name":   oname,
            "block_name": bname,
        })
    return infos


def read_existing_keys(block_name):
    if not rs.IsBlock(block_name):
        return []
    obj_ids = rs.BlockObjects(block_name)
    if not obj_ids:
        return []
    result = []
    for obj in obj_ids:
        jtype  = rs.GetUserText(obj, KEY_JOINT_TYPE)   or JOINT_FIXED
        parent = rs.GetUserText(obj, KEY_JOINT_PARENT) or ""
        try:    lo_a = float(rs.GetUserText(obj, KEY_MIN_ANGLE) or DEFAULT_PIVOT_MIN)
        except: lo_a = DEFAULT_PIVOT_MIN
        try:    hi_a = float(rs.GetUserText(obj, KEY_MAX_ANGLE) or DEFAULT_PIVOT_MAX)
        except: hi_a = DEFAULT_PIVOT_MAX
        try:    lo_t = float(rs.GetUserText(obj, KEY_MIN_TRANS) or DEFAULT_SLIDER_MIN)
        except: lo_t = DEFAULT_SLIDER_MIN
        try:    hi_t = float(rs.GetUserText(obj, KEY_MAX_TRANS) or DEFAULT_SLIDER_MAX)
        except: hi_t = DEFAULT_SLIDER_MAX
        result.append({
            "type":   jtype,
            "parent": parent,
            "min_a":  lo_a, "max_a": hi_a,
            "min_t":  lo_t, "max_t": hi_t,
        })
    return result


def collect_existing_instances(block_name):
    """
    Collecte toutes les instances du bloc dans le document.
    Retourne une liste de (layer, xform_list, user_texts_dict) pour réinsertion.
    """
    instances = []
    all_objs = rs.AllObjects()
    if not all_objs:
        return instances
    for obj_id in all_objs:
        if not rs.IsBlockInstance(obj_id):
            continue
        if rs.BlockInstanceName(obj_id) != block_name:
            continue
        xf    = rs.BlockInstanceXform(obj_id)
        layer = rs.ObjectLayer(obj_id)
        # Récupère tous les UserTexts de l'instance elle-même
        keys  = rs.GetUserText(obj_id) or []
        utexts = {k: rs.GetUserText(obj_id, k) for k in keys}
        instances.append({
            "xform":  xf,
            "layer":  layer,
            "utexts": utexts,
        })
    return instances


def write_keys_and_rebuild(block_name, sub_infos, joint_data):
    """
    1. Écrit les UserTexts sur les objets de définition du bloc.
    2. Sauvegarde les instances existantes dans le document.
    3. Supprime et recrée le bloc.
    4. Réinsère les instances aux mêmes emplacements.
    """
    obj_ids = [info["id"] for info in sub_infos]
    if len(obj_ids) != len(joint_data):
        return False

    # Sauvegarde des instances avant destruction
    existing = collect_existing_instances(block_name)

    # Écriture des UserTexts sur les objets de définition
    for obj, data in zip(obj_ids, joint_data):
        rs.SetUserText(obj, KEY_JOINT_TYPE,   data["type"])
        rs.SetUserText(obj, KEY_JOINT_PARENT, data["parent"])
        if data["type"] == JOINT_PIVOT:
            rs.SetUserText(obj, KEY_MIN_ANGLE, str(data["min_a"]))
            rs.SetUserText(obj, KEY_MAX_ANGLE, str(data["max_a"]))
            rs.SetUserText(obj, KEY_MIN_TRANS, "")
            rs.SetUserText(obj, KEY_MAX_TRANS, "")
        elif data["type"] == JOINT_SLIDER:
            rs.SetUserText(obj, KEY_MIN_TRANS, str(data["min_t"]))
            rs.SetUserText(obj, KEY_MAX_TRANS, str(data["max_t"]))
            rs.SetUserText(obj, KEY_MIN_ANGLE, "")
            rs.SetUserText(obj, KEY_MAX_ANGLE, "")
        else:
            rs.SetUserText(obj, KEY_MIN_ANGLE, "")
            rs.SetUserText(obj, KEY_MAX_ANGLE, "")
            rs.SetUserText(obj, KEY_MIN_TRANS, "")
            rs.SetUserText(obj, KEY_MAX_TRANS, "")

    # Reconstruction du bloc
    origin = Rhino.Geometry.Point3d.Origin
    rs.DeleteBlock(block_name)
    rs.AddBlock(obj_ids, origin, block_name, False)

    # Réinsertion des instances aux emplacements d'origine
    for inst in existing:
        new_id = rs.InsertBlock(block_name, [0, 0, 0])
        if new_id is None:
            continue
        rs.TransformObject(new_id, inst["xform"])
        try:
            rs.ObjectLayer(new_id, inst["layer"])
        except Exception:
            pass
        for k, v in inst["utexts"].items():
            if v:
                rs.SetUserText(new_id, k, v)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# ORDONNANCEMENT TOPOLOGIQUE
# ─────────────────────────────────────────────────────────────────────────────

def topological_sort(display_names, data_list):
    """
    Trie les indices selon l'ordre topologique (parents avant enfants).
    Les nœuds sans parent (fixed ou parent vide) viennent en premier.
    En cas de cycle, les nœuds restants sont ajoutés à la fin.
    Retourne la liste des indices originaux dans le nouvel ordre.
    """
    n = len(display_names)
    # Résolution parent display_name → index original
    name_to_idx = {display_names[i]: i for i in range(n)}

    children = {i: [] for i in range(n)}
    in_degree = {i: 0 for i in range(n)}

    for i, data in enumerate(data_list):
        parent_name = data.get("parent", "")
        if parent_name and parent_name in name_to_idx:
            p = name_to_idx[parent_name]
            if p != i:
                children[p].append(i)
                in_degree[i] += 1

    # Kahn
    queue = [i for i in range(n) if in_degree[i] == 0]
    order = []
    while queue:
        queue.sort()   # stable : préserve l'ordre d'origine à égalité
        node = queue.pop(0)
        order.append(node)
        for child in children[node]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Cas cycle : ajoute les restants
    remaining = [i for i in range(n) if i not in order]
    order.extend(remaining)
    return order


# ─────────────────────────────────────────────────────────────────────────────
# BOÎTE DE DIALOGUE ETO
# ─────────────────────────────────────────────────────────────────────────────

class JointDefDialog(ef.Dialog):

    def __init__(self, block_name, sub_infos, existing_data):
        super(JointDefDialog, self).__init__()

        self._block_name = block_name
        self._sub_infos  = sub_infos          # liste de dicts {id, display, ...}
        self._n          = len(sub_infos)
        self.validated   = False

        # Noms d'affichage (pour la colonne Nom et la résolution parent)
        self._display_names = [info["display"] for info in sub_infos]

        # État interne
        self._data = []
        for i in range(self._n):
            if i < len(existing_data):
                self._data.append(dict(existing_data[i]))
            else:
                self._data.append({
                    "type":  JOINT_FIXED, "parent": "",
                    "min_a": DEFAULT_PIVOT_MIN,  "max_a": DEFAULT_PIVOT_MAX,
                    "min_t": DEFAULT_SLIDER_MIN, "max_t": DEFAULT_SLIDER_MAX,
                })

        # Ordre d'affichage courant (indices originaux)
        self._order = list(range(self._n))

        # Widgets indexés par index ORIGINAL
        self._type_drops   = [None] * self._n
        self._parent_drops = [None] * self._n
        self._min_spins    = [None] * self._n
        self._max_spins    = [None] * self._n
        self._unit_labels  = [None] * self._n
        self._row_panels   = [None] * self._n   # Panel encapsulant chaque ligne

        self._scroll = None   # ScrollArea
        self._build_ui()
        self._refresh_order()

    # ── Construction UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.Title     = "Liaisons cinématiques – {}".format(self._block_name)
        self.Padding   = ed.Padding(10)
        self.Resizable = True
        self.MinimumSize = ed.Size(820, 400)

        outer = ef.DynamicLayout()
        outer.Spacing = ed.Size(0, 6)

        # ── En-têtes ─────────────────────────────────────────────────────────
        header = ef.TableLayout()
        header.Spacing = ed.Size(6, 0)
        header.Rows.Add(ef.TableRow(
            ef.TableCell(self._lbl("#",          True), False),
            ef.TableCell(self._lbl("Instance",   True), True),
            ef.TableCell(self._lbl("Liaison",    True), False),
            ef.TableCell(self._lbl("Parent",     True), False),
            ef.TableCell(self._lbl("Min",        True), False),
            ef.TableCell(self._lbl("Max",        True), False),
            ef.TableCell(self._lbl("Unité",      True), False),
        ))
        outer.AddRow(header)

        # ── Zone scrollable ───────────────────────────────────────────────────
        self._rows_layout = ef.DynamicLayout()
        self._rows_layout.Spacing = ed.Size(0, 2)

        for i in range(self._n):
            panel = self._build_row(i)
            self._row_panels[i] = panel
            self._rows_layout.AddRow(panel)

        scroll = ef.Scrollable()
        scroll.Content         = self._rows_layout
        scroll.ExpandContentHeight = False
        scroll.Height          = min(40 * self._n + 20, 480)
        self._scroll = scroll
        outer.AddRow(scroll)

        # ── Boutons ───────────────────────────────────────────────────────────
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
        """Construit les widgets d'une ligne (index original i) dans un TableLayout."""
        d = self._data[i]

        # DropDown type
        drop = ef.DropDown()
        for t in [JOINT_FIXED, JOINT_SLIDER, JOINT_PIVOT]:
            drop.Items.Add(t)
        drop.SelectedKey = d["type"]
        drop.Width       = 80
        drop.Tag         = i
        drop.SelectedIndexChanged += self._on_type_changed
        self._type_drops[i] = drop

        # DropDown parent (liste des noms d'affichage + "— aucun —")
        pdrop = ef.DropDown()
        pdrop.Items.Add("— aucun —")
        for name in self._display_names:
            pdrop.Items.Add(name)
        # Sélection initiale
        if d["parent"] and d["parent"] in self._display_names:
            pdrop.SelectedIndex = self._display_names.index(d["parent"]) + 1
        else:
            pdrop.SelectedIndex = 0
        pdrop.Width = 160
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
        unit_lbl = self._lbl(self._unit_for(d["type"]))
        unit_lbl.Width = 24
        self._unit_labels[i] = unit_lbl

        self._set_row_enabled(i, d["type"])

        row_layout = ef.TableLayout()
        row_layout.Spacing = ed.Size(6, 0)
        # La colonne index sera remplie dynamiquement dans _refresh_order
        idx_lbl = ef.Label(Text="")
        idx_lbl.Width = 24
        idx_lbl.Tag   = i   # on le retrouve pour mettre à jour le numéro
        row_layout.Rows.Add(ef.TableRow(
            ef.TableCell(idx_lbl,  False),
            ef.TableCell(self._lbl(self._display_names[i]), True),
            ef.TableCell(drop,     False),
            ef.TableCell(pdrop,    False),
            ef.TableCell(min_spin, False),
            ef.TableCell(max_spin, False),
            ef.TableCell(unit_lbl, False),
        ))

        panel = ef.Panel()
        panel.Content = row_layout
        panel.Tag     = i
        return panel

    # ── Helpers UI ───────────────────────────────────────────────────────────

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
        d     = self._data[i]
        jtype = d["type"]
        ms, xs = self._min_spins[i], self._max_spins[i]
        if jtype == JOINT_PIVOT:
            for sp in (ms, xs):
                sp.MinValue = -720.0
                sp.MaxValue =  720.0
            ms.Value = d["min_a"]
            xs.Value = d["max_a"]
        elif jtype == JOINT_SLIDER:
            for sp in (ms, xs):
                sp.MinValue = -10000.0
                sp.MaxValue =  10000.0
            ms.Value = d["min_t"]
            xs.Value = d["max_t"]
        else:
            ms.Value = 0.0
            xs.Value = 0.0

    def _set_row_enabled(self, i, jtype):
        enabled = (jtype != JOINT_FIXED)
        self._parent_drops[i].Enabled = enabled
        self._min_spins[i].Enabled    = enabled
        self._max_spins[i].Enabled    = enabled

    # ── Ordonnancement ───────────────────────────────────────────────────────

    def _refresh_order(self):
        """
        Recalcule l'ordre topologique et réorganise les panels dans le layout.
        Met à jour les numéros de position affichés.
        """
        self._order = topological_sort(self._display_names, self._data)

        # Rhino/Eto ne permet pas de réordonner les enfants d'un DynamicLayout
        # après création. On masque/réaffiche en jouant sur Visible dans l'ordre.
        # Astuce : on recrée le contenu du scroll.
        new_layout = ef.DynamicLayout()
        new_layout.Spacing = ed.Size(0, 2)
        for pos, orig_idx in enumerate(self._order):
            panel = self._row_panels[orig_idx]
            # Mise à jour du label de numéro (premier contrôle de la TableRow)
            tl = panel.Content
            if tl and hasattr(tl, "Rows") and len(tl.Rows) > 0:
                row = tl.Rows[0]
                if row and len(row.Cells) > 0:
                    cell = row.Cells[0]
                    if cell and cell.Control:
                        cell.Control.Text = str(pos + 1)
            new_layout.AddRow(panel)

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
        i   = sender.Tag
        idx = sender.SelectedIndex
        self._data[i]["parent"] = self._display_names[idx - 1] if idx > 0 else ""
        self._refresh_order()

    def _on_ok(self, sender, e):
        # Collecte finale
        for i in range(self._n):
            jtype = self._type_drops[i].SelectedKey or JOINT_FIXED
            pidx  = self._parent_drops[i].SelectedIndex
            self._data[i]["type"]   = jtype
            self._data[i]["parent"] = self._display_names[pidx - 1] if pidx > 0 else ""
            if jtype == JOINT_PIVOT:
                self._data[i]["min_a"] = self._min_spins[i].Value
                self._data[i]["max_a"] = self._max_spins[i].Value
            elif jtype == JOINT_SLIDER:
                self._data[i]["min_t"] = self._min_spins[i].Value
                self._data[i]["max_t"] = self._max_spins[i].Value

        # Validation
        errors = []
        for i in range(self._n):
            d = self._data[i]
            if d["type"] != JOINT_FIXED and not d["parent"]:
                errors.append("Instance '{}' : parent requis pour liaison '{}'.".format(
                    self._display_names[i], d["type"]))
            if d["type"] != JOINT_FIXED:
                lo = d["min_a"] if d["type"] == JOINT_PIVOT else d["min_t"]
                hi = d["max_a"] if d["type"] == JOINT_PIVOT else d["max_t"]
                if lo >= hi:
                    errors.append("Instance '{}' : Min doit être < Max.".format(
                        self._display_names[i]))
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
    # 1. Sélection ou saisie du bloc
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

    # 2. Lecture
    sub_infos     = get_block_sub_infos(block_name)
    if not sub_infos:
        rs.MessageBox(
            "Le bloc '{}' ne contient aucune instance.".format(block_name),
            0, "Erreur")
        return
    existing_data = read_existing_keys(block_name)

    # 3. Dialogue
    dlg = JointDefDialog(block_name, sub_infos, existing_data)
    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    if not dlg.validated:
        print("Annulé – aucune modification.")
        return

    # 4. Écriture + reconstruction + réinsertion
    ok = write_keys_and_rebuild(block_name, sub_infos, dlg.joint_data)
    if ok:
        sc.doc.Views.Redraw()
        print("Bloc '{}' mis à jour.".format(block_name))
        for i, d in enumerate(dlg.joint_data):
            parent_str = " → '{}'".format(d["parent"]) if d["parent"] else ""
            if d["type"] == JOINT_PIVOT:
                limit_str = " [{:.1f}°…{:.1f}°]".format(d["min_a"], d["max_a"])
            elif d["type"] == JOINT_SLIDER:
                limit_str = " [{:.1f}…{:.1f} mm]".format(d["min_t"], d["max_t"])
            else:
                limit_str = ""
            print("  [{}] {} : {}{}{}".format(
                i + 1, sub_infos[i]["display"], d["type"], parent_str, limit_str))
    else:
        rs.MessageBox(
            "Erreur lors de la reconstruction du bloc '{}'.".format(block_name),
            0, "Erreur")


if __name__ == "__main__":
    main()
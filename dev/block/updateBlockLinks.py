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
    """
    Si raw_name contient '#', retourne la partie avant '#'.
    Sinon retourne raw_name tel quel.
    """
    if "#" in raw_name:
        return raw_name.split("#", 1)[0]
    return raw_name


def get_block_instance_names(block_name):
    """
    Retourne la liste ordonnée des noms des sous-instances d'un bloc.
    """
    if not rs.IsBlock(block_name):
        return []
    objects = rs.BlockObjects(block_name)
    if not objects:
        return []
    names = []
    for obj in objects:
        name = rs.ObjectName(obj)
        if not name:
            name = "(sans nom)"
        names.append(name)
    return names


def get_block_instance_ids(block_name):
    """
    Retourne la liste des IDs des sous-instances d'un bloc.
    """
    if not rs.IsBlock(block_name):
        return []
    return rs.BlockObjects(block_name) or []


def read_existing_keys(block_name):
    """
    Lit les KEY_JOINT_TYPE, KEY_JOINT_PARENT et limites
    sur chaque sous-instance du bloc.
    Retourne une liste de dicts, un par sous-instance, dans l'ordre.
    """
    obj_ids = get_block_instance_ids(block_name)
    result  = []
    for obj in obj_ids:
        jtype  = rs.GetUserText(obj, KEY_JOINT_TYPE)   or JOINT_FIXED
        parent = rs.GetUserText(obj, KEY_JOINT_PARENT) or ""
        try:
            lo_a = float(rs.GetUserText(obj, KEY_MIN_ANGLE) or DEFAULT_PIVOT_MIN)
        except (ValueError, TypeError):
            lo_a = DEFAULT_PIVOT_MIN
        try:
            hi_a = float(rs.GetUserText(obj, KEY_MAX_ANGLE) or DEFAULT_PIVOT_MAX)
        except (ValueError, TypeError):
            hi_a = DEFAULT_PIVOT_MAX
        try:
            lo_t = float(rs.GetUserText(obj, KEY_MIN_TRANS) or DEFAULT_SLIDER_MIN)
        except (ValueError, TypeError):
            lo_t = DEFAULT_SLIDER_MIN
        try:
            hi_t = float(rs.GetUserText(obj, KEY_MAX_TRANS) or DEFAULT_SLIDER_MAX)
        except (ValueError, TypeError):
            hi_t = DEFAULT_SLIDER_MAX
        result.append({
            "type":    jtype,
            "parent":  parent,
            "min_a":   lo_a,
            "max_a":   hi_a,
            "min_t":   lo_t,
            "max_t":   hi_t,
        })
    return result


def write_keys_to_block(block_name, instance_names, joint_data):
    """
    Réécrit les UserTexts sur chaque sous-instance du bloc,
    puis reconstruit le bloc (supprime + recrée avec les objets modifiés).
    joint_data : liste de dicts dans le même ordre que instance_names.
    """
    obj_ids = get_block_instance_ids(block_name)
    if len(obj_ids) != len(joint_data):
        return False

    # Écriture des UserTexts sur les objets de définition du bloc
    for obj, data in zip(obj_ids, joint_data):
        rs.SetUserText(obj, KEY_JOINT_TYPE,   data["type"])
        rs.SetUserText(obj, KEY_JOINT_PARENT, data["parent"])
        if data["type"] == JOINT_PIVOT:
            rs.SetUserText(obj, KEY_MIN_ANGLE, str(data["min_a"]))
            rs.SetUserText(obj, KEY_MAX_ANGLE, str(data["max_a"]))
            # Nettoyage des clés de translation si on change de type
            rs.SetUserText(obj, KEY_MIN_TRANS, "")
            rs.SetUserText(obj, KEY_MAX_TRANS, "")
        elif data["type"] == JOINT_SLIDER:
            rs.SetUserText(obj, KEY_MIN_TRANS, str(data["min_t"]))
            rs.SetUserText(obj, KEY_MAX_TRANS, str(data["max_t"]))
            rs.SetUserText(obj, KEY_MIN_ANGLE, "")
            rs.SetUserText(obj, KEY_MAX_ANGLE, "")
        else:
            # fixed : nettoyage
            rs.SetUserText(obj, KEY_MIN_ANGLE, "")
            rs.SetUserText(obj, KEY_MAX_ANGLE, "")
            rs.SetUserText(obj, KEY_MIN_TRANS, "")
            rs.SetUserText(obj, KEY_MAX_TRANS, "")

    # Reconstruction du bloc : capture point d'origine, supprime, recrée
    origin = Rhino.Geometry.Point3d.Origin
    rs.DeleteBlock(block_name)
    rs.AddBlock(obj_ids, origin, block_name, False)

    return True


# ─────────────────────────────────────────────────────────────────────────────
# BOÎTE DE DIALOGUE ETO
# ─────────────────────────────────────────────────────────────────────────────

class JointDefDialog(ef.Dialog):
    """
    Interface de définition des liaisons cinématiques entre sous-instances.

    Colonnes :
      #  |  Nom instance  |  Type liaison  |  Parent (#)  |  Min  |  Max  |  Unité
    """

    def __init__(self, block_name, instance_names, existing_data):
        super(JointDefDialog, self).__init__()

        self._block_name      = block_name
        self._instance_names  = instance_names
        self._n               = len(instance_names)
        self.validated        = False

        # État interne : liste de dicts
        self._data = []
        for i in range(self._n):
            if i < len(existing_data):
                self._data.append(dict(existing_data[i]))
            else:
                self._data.append({
                    "type":  JOINT_FIXED,
                    "parent": "",
                    "min_a": DEFAULT_PIVOT_MIN,
                    "max_a": DEFAULT_PIVOT_MAX,
                    "min_t": DEFAULT_SLIDER_MIN,
                    "max_t": DEFAULT_SLIDER_MAX,
                })

        # Widgets dynamiques par ligne
        self._type_drops  = []   # DropDown
        self._parent_spins = []  # NumericStepper (index 1-based, 0 = aucun)
        self._min_spins   = []   # NumericStepper
        self._max_spins   = []   # NumericStepper
        self._unit_labels = []   # Label

        self._build_ui()

    # ── Construction UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.Title     = "Liaisons cinématiques – {}".format(self._block_name)
        self.Padding   = ed.Padding(10)
        self.Resizable = True

        layout = ef.TableLayout()
        layout.Spacing = ed.Size(6, 4)

        # En-têtes
        layout.Rows.Add(ef.TableRow(
            ef.TableCell(self._lbl("#",         True)),
            ef.TableCell(self._lbl("Instance",  True)),
            ef.TableCell(self._lbl("Liaison",   True)),
            ef.TableCell(self._lbl("Parent (#)", True)),
            ef.TableCell(self._lbl("Min",       True)),
            ef.TableCell(self._lbl("Max",       True)),
            ef.TableCell(self._lbl("Unité",     True)),
        ))

        for i in range(self._n):
            d = self._data[i]

            # Numéro + nom
            lbl_idx  = self._lbl(str(i + 1))
            lbl_name = self._lbl(self._instance_names[i])

            # DropDown type de liaison
            drop = ef.DropDown()
            for t in [JOINT_FIXED, JOINT_SLIDER, JOINT_PIVOT]:
                drop.Items.Add(t)
            drop.SelectedKey = d["type"]
            drop.Tag         = i
            drop.SelectedIndexChanged += self._on_type_changed
            self._type_drops.append(drop)

            # NumericStepper parent (0 = aucun, sinon numéro 1-based)
            parent_spin = ef.NumericStepper()
            parent_spin.MinValue      = 0
            parent_spin.MaxValue      = self._n
            parent_spin.DecimalPlaces = 0
            parent_spin.Increment     = 1
            parent_spin.Width         = 60
            parent_spin.Tag           = i
            # Résolution du parent stocké (nom → index)
            parent_spin.Value = self._name_to_index(d["parent"])
            self._parent_spins.append(parent_spin)

            # Min / Max
            min_spin = ef.NumericStepper()
            max_spin = ef.NumericStepper()
            for sp in (min_spin, max_spin):
                sp.DecimalPlaces = 2
                sp.Increment     = 1.0
                sp.Width         = 80

            self._apply_limits_to_spinners(i, min_spin, max_spin)
            min_spin.Tag = i
            max_spin.Tag = i
            self._min_spins.append(min_spin)
            self._max_spins.append(max_spin)

            # Label unité
            unit_lbl = self._lbl(self._unit_for(d["type"]))
            self._unit_labels.append(unit_lbl)

            # Désactivation si fixed
            self._set_row_enabled(i, d["type"])

            layout.Rows.Add(ef.TableRow(
                ef.TableCell(lbl_idx),
                ef.TableCell(lbl_name),
                ef.TableCell(drop),
                ef.TableCell(parent_spin),
                ef.TableCell(min_spin),
                ef.TableCell(max_spin),
                ef.TableCell(unit_lbl),
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

    # ── Helpers UI ───────────────────────────────────────────────────────────

    @staticmethod
    def _lbl(text, bold=False):
        lbl = ef.Label(Text=str(text))
        if bold:
            lbl.Font = ed.Font(lbl.Font.Family, lbl.Font.Size, ed.FontStyle.Bold)
        return lbl

    @staticmethod
    def _unit_for(jtype):
        if jtype == JOINT_PIVOT:
            return "°"
        if jtype == JOINT_SLIDER:
            return "mm"
        return ""

    def _name_to_index(self, name):
        """Convertit un nom d'instance en index 1-based (0 si absent)."""
        if not name:
            return 0
        try:
            return self._instance_names.index(name) + 1
        except ValueError:
            return 0

    def _index_to_name(self, index):
        """Convertit un index 1-based en nom d'instance ("" si 0)."""
        idx = int(index)
        if idx <= 0 or idx > self._n:
            return ""
        return self._instance_names[idx - 1]

    def _apply_limits_to_spinners(self, i, min_spin, max_spin):
        """Initialise Min/Max des spinners selon le type de liaison."""
        d     = self._data[i]
        jtype = d["type"]
        if jtype == JOINT_PIVOT:
            min_spin.MinValue = -720.0
            min_spin.MaxValue =  720.0
            max_spin.MinValue = -720.0
            max_spin.MaxValue =  720.0
            min_spin.Value    = d["min_a"]
            max_spin.Value    = d["max_a"]
        elif jtype == JOINT_SLIDER:
            min_spin.MinValue = -10000.0
            min_spin.MaxValue =  10000.0
            max_spin.MinValue = -10000.0
            max_spin.MaxValue =  10000.0
            min_spin.Value    = d["min_t"]
            max_spin.Value    = d["max_t"]
        else:
            min_spin.Value = 0.0
            max_spin.Value = 0.0

    def _set_row_enabled(self, i, jtype):
        """Active/désactive parent, min, max selon le type."""
        enabled = (jtype != JOINT_FIXED)
        self._parent_spins[i].Enabled = enabled
        self._min_spins[i].Enabled    = enabled
        self._max_spins[i].Enabled    = enabled

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_type_changed(self, sender, e):
        i     = sender.Tag
        jtype = sender.SelectedKey or JOINT_FIXED
        self._data[i]["type"] = jtype

        # Réinitialise min/max aux valeurs par défaut si changement de type
        if jtype == JOINT_PIVOT:
            self._data[i]["min_a"] = DEFAULT_PIVOT_MIN
            self._data[i]["max_a"] = DEFAULT_PIVOT_MAX
        elif jtype == JOINT_SLIDER:
            self._data[i]["min_t"] = DEFAULT_SLIDER_MIN
            self._data[i]["max_t"] = DEFAULT_SLIDER_MAX

        self._apply_limits_to_spinners(i, self._min_spins[i], self._max_spins[i])
        self._unit_labels[i].Text = self._unit_for(jtype)
        self._set_row_enabled(i, jtype)

    def _on_ok(self, sender, e):
        # Collecte des valeurs finales depuis les widgets
        for i in range(self._n):
            jtype = self._type_drops[i].SelectedKey or JOINT_FIXED
            self._data[i]["type"]   = jtype
            self._data[i]["parent"] = self._index_to_name(self._parent_spins[i].Value)
            if jtype == JOINT_PIVOT:
                self._data[i]["min_a"] = self._min_spins[i].Value
                self._data[i]["max_a"] = self._max_spins[i].Value
            elif jtype == JOINT_SLIDER:
                self._data[i]["min_t"] = self._min_spins[i].Value
                self._data[i]["max_t"] = self._max_spins[i].Value

        # Validation : une liaison non-fixe doit avoir un parent valide
        errors = []
        for i in range(self._n):
            d = self._data[i]
            if d["type"] != JOINT_FIXED and not d["parent"]:
                errors.append("Instance {} ({}) : parent requis pour liaison '{}'.".format(
                    i + 1, self._instance_names[i], d["type"]))
            if d["type"] != JOINT_FIXED:
                lo = d["min_a"] if d["type"] == JOINT_PIVOT else d["min_t"]
                hi = d["max_a"] if d["type"] == JOINT_PIVOT else d["max_t"]
                if lo >= hi:
                    errors.append("Instance {} ({}) : Min doit être < Max.".format(
                        i + 1, self._instance_names[i]))

        if errors:
            rs.MessageBox("\n".join(errors), 0, "Erreurs de validation")
            return

        self.validated = True
        self.Close()

    def _on_cancel(self, sender, e):
        self.validated = False
        self.Close()

    # ── Accesseur ────────────────────────────────────────────────────────────

    @property
    def joint_data(self):
        return [dict(d) for d in self._data]


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def updateBlockLinks():
    # 1. Sélection ou saisie du bloc
    presel = [obj.Id for obj in sc.doc.Objects if obj.IsSelected(False) > 0]

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

    # 2. Résolution du nom de bloc (suppression du suffixe #i)
    block_name = resolve_block_name(raw_name.strip())

    if not rs.IsBlock(block_name):
        rs.MessageBox("Le bloc '{}' n'existe pas.".format(block_name), 0, "Erreur")
        return

    # 3. Lecture des sous-instances et des clés existantes
    instance_names = get_block_instance_names(block_name)
    if not instance_names:
        rs.MessageBox(
            "Le bloc '{}' ne contient aucune instance.".format(block_name),
            0, "Erreur")
        return

    existing_data = read_existing_keys(block_name)

    # 4. Affichage du dialogue
    dlg = JointDefDialog(block_name, instance_names, existing_data)
    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    if not dlg.validated:
        print("Annulé – aucune modification.")
        return

    # 5. Écriture des UserTexts et reconstruction du bloc
    ok = write_keys_to_block(block_name, instance_names, dlg.joint_data)
    if ok:
        sc.doc.Views.Redraw()
        print("Bloc '{}' mis à jour avec {} liaisons.".format(
            block_name, len(instance_names)))
        for i, d in enumerate(dlg.joint_data):
            parent_str = " → parent '{}'".format(d["parent"]) if d["parent"] else ""
            if d["type"] == JOINT_PIVOT:
                limit_str = " [{:.1f}° … {:.1f}°]".format(d["min_a"], d["max_a"])
            elif d["type"] == JOINT_SLIDER:
                limit_str = " [{:.1f} … {:.1f} mm]".format(d["min_t"], d["max_t"])
            else:
                limit_str = ""
            print("  [{}] {} : {}{}{}".format(
                i + 1, instance_names[i], d["type"], parent_str, limit_str))
    else:
        rs.MessageBox(
            "Erreur lors de la réécriture du bloc '{}'.".format(block_name),
            0, "Erreur")


if __name__ == "__main__":
    updateBlockLinks()

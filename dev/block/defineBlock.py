# -*- coding: utf-8 -*-
"""
defineBlock.py
--------------
Crée ou écrase une définition de bloc à partir d'une sélection d'objets,
en s'appuyant sur un bloc source comme origine (ou sur le World).

Flux :
  1. Sélection des objets cibles.
  2. Choix de l'origine : un bloc existant OU le World (Entrée).
  3. Lecture du nom racine depuis les UserText "BlockNameLevel_*" du premier
     objet sélectionné (fallback → "NewBlock").
  4. Confirmation / saisie du nom final (rs.GetString).
  5. Si le nom existe déjà → confirmation d'écrasement (rs.GetString + ModifyGeometry).
  6. Insertion de la nouvelle instance à l'origine choisie.
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino


# ──────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────────────────────────────────────

def _get_root_name_from_usertext(obj_ids):
    """
    Parcourt les UserText 'BlockNameLevel_N' de chaque objet et retourne
    le nom associé au niveau le plus bas (racine = niveau 0 ou minimum trouvé).
    Retourne None si aucun UserText pertinent n'est trouvé.
    """
    best_name  = None
    best_level = None

    for obj_id in obj_ids:
        keys = rs.GetUserText(obj_id)
        if not keys:
            continue
        for k in keys:
            if not k.startswith("BlockNameLevel_"):
                continue
            try:
                lvl = int(k.split("_")[-1])
            except ValueError:
                continue
            val = rs.GetUserText(obj_id, k)
            if not val:
                continue
            if best_level is None or lvl < best_level:
                best_level = lvl
                name = val.split("#")[0] if "#" in val else val
                best_name = name

    return best_name


def _clean_block_name(name):
    """Supprime les suffixes automatiques (_base, _01…_99)."""
    if not name:
        return name
    if name.lower().endswith("_base"):
        name = name[:-5]
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit():
        name = name[:-3]
    return name


def _xform_from_origin_block(origin_id):
    """Retourne le Xform du bloc origine, ou XformIdentity si None/invalide."""
    if origin_id and rs.IsBlockInstance(origin_id):
        xf = rs.BlockInstanceXform(origin_id)
        if xf is not None:
            return xf
    return rs.XformIdentity()


# ──────────────────────────────────────────────────────────────────────────────
# Fonction principale
# ──────────────────────────────────────────────────────────────────────────────

def defineBlock():

    # ── 1. Sélection des objets ────────────────────────────────────────────────
    obj_ids = rs.GetObjects(
        "Sélectionner les objets du bloc",
        preselect=True
    )
    if not obj_ids:
        return

    # ── 2. Origine : bloc source ou World ──────────────────────────────────────
    origin_id    = rs.GetObject(
        "Choisir un bloc comme origine (Entrée = Origine Mondiale)",
        rs.filter.instance
    )
    origin_xform = _xform_from_origin_block(origin_id)

    # ── 3. Détermination du nom racine ─────────────────────────────────────────
    raw_name  = _get_root_name_from_usertext(obj_ids)
    root_name = _clean_block_name(raw_name) if raw_name else "NewBlock"

    # ── 4. Confirmation / saisie du nom (rs.GetString) ─────────────────────────
    final_name = rs.GetString("Nom du bloc", root_name)
    if not final_name:
        print("Opération annulée.")
        return
    final_name = final_name.strip()
    if not final_name:
        print("Nom invalide. Opération annulée.")
        return

    # ── 5. Gestion de l'écrasement (rs.GetString) ──────────────────────────────
    overwrite = False
    if rs.IsBlock(final_name):
        answer = rs.GetString(
            "Le bloc '{}' existe déjà. Ecraser ?".format(final_name),
            "Oui",
            ["Oui", "Non"]
        )
        if answer is None or answer.lower() != "oui":
            print("Opération annulée : le bloc '{}' n'a pas été modifié.".format(final_name))
            return
        overwrite = True

    # ── 6. Construction de la géométrie dans le repère local ───────────────────
    rs.EnableRedraw(False)

    inv_origin = rs.XformInverse(origin_xform)
    if inv_origin is None:
        print("Erreur : impossible d'inverser la transformation d'origine.")
        rs.EnableRedraw(True)
        return

    # Copier et ramener au repère local (origine = [0,0,0])
    local_copies = []
    for obj_id in obj_ids:
        cp = rs.CopyObject(obj_id)
        if cp:
            rs.TransformObject(cp, inv_origin)
            local_copies.append(cp)

    if not local_copies:
        print("Erreur : aucun objet copié.")
        rs.EnableRedraw(True)
        return

    # ── 7. Création / écrasement de la définition ──────────────────────────────
    if overwrite:
        # Même technique que rebuild_reciproque :
        # on récupère les objets RhinoCommon directement (sans DuplicateShallow)
        # et on appelle ModifyGeometry pour mettre à jour toutes les instances.
        idef = sc.doc.InstanceDefinitions.Find(final_name, True)
        if idef is None:
            print("Erreur : définition '{}' introuvable.".format(final_name))
            rs.DeleteObjects(local_copies)
            rs.EnableRedraw(True)
            return

        geo_list  = []
        attr_list = []
        for guid in local_copies:
            rh_obj = sc.doc.Objects.Find(guid)
            if rh_obj:
                geo_list.append(rh_obj.Geometry)
                attr_list.append(rh_obj.Attributes)

        success = sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geo_list, attr_list)
        rs.DeleteObjects(local_copies)

        if not success:
            print("Erreur : échec de la mise à jour de la définition '{}'.".format(final_name))
            rs.EnableRedraw(True)
            return
        print("Définition '{}' mise à jour.".format(final_name))

    else:
        result = rs.AddBlock(local_copies, [0, 0, 0], final_name, delete_input=True)
        if not result:
            rs.DeleteObjects([c for c in local_copies if rs.IsObject(c)])
            print("Erreur : impossible de créer le bloc '{}'.".format(final_name))
            rs.EnableRedraw(True)
            return
        print("Bloc '{}' créé.".format(final_name))

    # ── 8. Insertion de l'instance à l'origine choisie ────────────────────────
    new_inst = rs.InsertBlock(final_name, [0, 0, 0])
    if new_inst:
        rs.TransformObject(new_inst, origin_xform)
        rs.SelectObject(new_inst)

    rs.EnableRedraw(True)
    print("defineBlock terminé : bloc '{}' inséré à l'origine définie.".format(final_name))


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    defineBlock()
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
  4. Confirmation / saisie du nom final par l'utilisateur.
  5. Si le nom existe déjà → confirmation d'écrasement (ModifyGeometry).
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
    best_name = None
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
            # On veut le niveau le plus BAS (racine de la hiérarchie)
            if best_level is None or lvl < best_level:
                best_level = lvl
                # Nettoyer le suffixe "#N" éventuel
                name = val.split("#")[0] if "#" in val else val
                best_name = name

    return best_name


def _clean_block_name(name):
    """
    Supprime les suffixes courants générés automatiquement
    (_base, _01 … _99) pour retrouver le nom de base propre.
    """
    if not name:
        return name
    # Supprimer _base (insensible à la casse)
    if name.lower().endswith("_base"):
        name = name[:-5]
    # Supprimer _XX où XX = deux chiffres
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit():
        name = name[:-3]
    return name


def _xform_from_origin_block(origin_id):
    """
    Retourne la transformation (Xform) portée par le bloc origine sélectionné.
    Si origin_id est None ou invalide → XformIdentity (World).
    """
    if origin_id and rs.IsBlockInstance(origin_id):
        xf = rs.BlockInstanceXform(origin_id)
        if xf is not None:
            return xf
    return rs.XformIdentity()


def _overwrite_block_def(block_name, geo_guids):
    """
    Écrase la définition existante 'block_name' avec la nouvelle géométrie
    (liste de GUIDs Rhino). Utilise ModifyGeometry (RhinoCommon).
    Retourne True en cas de succès, False sinon.
    """
    idef = sc.doc.InstanceDefinitions.Find(block_name, True)
    if idef is None:
        return False

    geo_list  = []
    attr_list = []
    for guid in geo_guids:
        rh_obj = sc.doc.Objects.Find(guid)
        if rh_obj:
            geo_list.append(rh_obj.Geometry.DuplicateShallow())
            attr_list.append(rh_obj.Attributes.Duplicate())

    if not geo_list:
        return False

    return sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geo_list, attr_list)


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
    origin_id = rs.GetObject(
        "Choisir un bloc comme origine (Entrée = Origine Mondiale)",
        rs.filter.instance
    )
    # origin_id peut être None (Entrée) ou un GUID de bloc
    origin_xform = _xform_from_origin_block(origin_id)

    # ── 3. Détermination du nom racine ─────────────────────────────────────────
    raw_name   = _get_root_name_from_usertext(obj_ids)
    root_name  = _clean_block_name(raw_name) if raw_name else "NewBlock"

    # ── 4. Confirmation / saisie du nom final ──────────────────────────────────
    final_name = rs.StringBox(
        "Nom du bloc :",
        root_name,
        "Définir le bloc"
    )
    if not final_name:
        print("Opération annulée.")
        return
    final_name = final_name.strip()
    if not final_name:
        print("Nom invalide. Opération annulée.")
        return

    # ── 5. Gestion de l'écrasement ─────────────────────────────────────────────
    block_exists = rs.IsBlock(final_name)
    overwrite    = False

    if block_exists:
        answer = rs.MessageBox(
            "Le bloc '{}' existe déjà.\n\nVoulez-vous l'écraser ?".format(final_name),
            4 | 32,          # 4 = Yes/No, 32 = icône question
            "Bloc existant"
        )
        # 6 = Yes, 7 = No
        if answer != 6:
            print("Opération annulée : le bloc '{}' n'a pas été modifié.".format(final_name))
            return
        overwrite = True

    # ── 6. Construction de la géométrie dans le repère local du bloc ───────────
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
        success = _overwrite_block_def(final_name, local_copies)
        rs.DeleteObjects(local_copies)
        if not success:
            print("Erreur : échec de la mise à jour de la définition '{}'.".format(final_name))
            rs.EnableRedraw(True)
            return
        print("Définition '{}' mise à jour.".format(final_name))
    else:
        # AddBlock supprime les copies et crée la définition
        result = rs.AddBlock(local_copies, [0, 0, 0], final_name, delete_input=True)
        if not result:
            # Nettoyage de sécurité si AddBlock a échoué
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
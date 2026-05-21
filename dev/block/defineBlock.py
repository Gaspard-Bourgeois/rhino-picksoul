# -*- coding: utf-8 -*-
"""
defineBlock.py
--------------
Crée ou écrase une définition de bloc à partir d'une sélection d'objets,
en s'appuyant sur un bloc source ou un point comme origine (ou sur le World).

Flux :
  1. Sélection des objets cibles.
  2. Choix de l'origine : un bloc existant, un point spécifique (via l'option) 
     OU le World (Entrée).
  3. Lecture du nom racine depuis les UserText "BlockNameLevel_*" des objets
     sélectionnés (fallback → "NewBlock").
  4. Confirmation / saisie du nom final (rs.GetString).
  5. Si le nom existe déjà → confirmation d'écrasement (rs.GetString).
  6. Gestion des conflits d'auto-référence (renommage si une instance sélectionnée porte le même nom).
  7. Insertion de la nouvelle instance à l'origine choisie.
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
    le nom associé au niveau le plus bas (racine = minimum trouvé).
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


def _find_available_index_name(base_name):
    """Trouve un nom disponible sous la forme base_name#i."""
    i = 1
    while True:
        candidate = "{}#{}".format(base_name, i)
        if not rs.IsBlock(candidate):
            return candidate
        i += 1


def _get_origin_with_option():
    """
    Demande à l'utilisateur de choisir un bloc origine.
    - Clic sur un bloc -> utilise le bloc.
    - Clic sur l'option "ChoisirPoint" -> demande un point précis.
    - Touche Entrée -> utilise l'origine mondiale (WorldXY).
    Retourne : (Rhino.Geom.Transform, succes_bool)
    """
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Choisir un bloc comme origine (Entrée = Origine Mondiale)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.InstanceReference  # Filtre uniquement les blocs
    go.AcceptNothing(True)
    go.DisablePreSelect()
    
    # Ajout de l'option cliquable en ligne de commande
    go.AddOption("ChoisirPoint")
    
    while True:
        get_rc = go.Get()
        
        # Cas 1 : L'utilisateur a cliqué sur un bloc de référence
        if get_rc == Rhino.Input.GetResult.Object:
            obj_ref = go.Object(0)
            origin_id = obj_ref.ObjectId
            go.Dispose()
            xf = rs.BlockInstanceXform(origin_id)
            if xf is not None:
                return xf, True
            return rs.XformIdentity(), True
            
        # Cas 2 : L'utilisateur a cliqué explicitement sur l'option "ChoisirPoint"
        elif get_rc == Rhino.Input.GetResult.Option:
            go.Dispose()
            pt = rs.GetPoint("Sélectionner le point d'origine")
            if pt:
                # Crée une matrice de translation pure à partir du point
                return rs.XformTranslation(pt), True
            else:
                return None, False
                
        # Cas 3 : L'utilisateur a pressé Entrée (sans clic sur l'option) -> Origine Mondiale
        elif get_rc == Rhino.Input.GetResult.Nothing:
            go.Dispose()
            return rs.XformIdentity(), True
            
        # Annulation (Echap, etc.)
        else:
            go.Dispose()
            return None, False


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

    # ── 2. Origine : bloc source, point personnalisé ou World ──────────────────
    origin_xform, success = _get_origin_with_option()
    if not success:
        print("Opération annulée.")
        return

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

    inv_xform = rs.XformInverse(origin_xform)
    if inv_xform is None:
        print("Erreur : impossible d'inverser la transformation d'origine.")
        rs.EnableRedraw(True)
        return

    copied_geos = []
    
    def is_block_defined_in_block_child(_obj_ids, _final_name):
        # Correction de l'auto-référence : On inspecte les objets sélectionnés AVANT la duplication
        for obj_id in _obj_ids:
            if rs.IsBlockInstance(obj_id):
                current_block_name = rs.BlockInstanceName(obj_id)
                # Si le bloc sélectionné porte le même nom que le bloc que l'on veut créer/écraser
                if current_block_name == _final_name:
                    new_block_name = _find_available_index_name(_final_name)
                    # Renommer la définition existante pour casser l'auto-référence
                    rs.RenameBlock(current_block_name, new_block_name)
                    print("⚠️ Conflit d'auto-référence évité : L'instance de bloc sélectionnée '{}' a été renommée en '{}'.".format(_final_name, new_block_name))
                    return True
                else:
                    definition_objects = rs.BlockObjects(current_block_name)
                    if is_block_defined_in_block_child(definition_objects, _final_name):
                        return True
        return False
                    
    overwrite = not is_block_defined_in_block_child(obj_ids, final_name)
    
    for obj_id in obj_ids:
        # Copie et transformation de l'objet
        cp = rs.CopyObject(obj_id)
        if cp:
            rs.TransformObject(cp, inv_xform)
            copied_geos.append(cp)

    if not copied_geos:
        print("Erreur : aucun objet copié.")
        rs.EnableRedraw(True)
        return

    # ── 7. Création / écrasement de la définition ──────────────────────────────
    if overwrite:
        idef = sc.doc.InstanceDefinitions.Find(final_name)
        if idef:
            geo_list  = []
            attr_list = []
            for guid in copied_geos:
                rh_obj = sc.doc.Objects.Find(guid)
                if rh_obj:
                    # Duplication de la géométrie et des attributs
                    geo_list.append(rh_obj.Geometry.DuplicateShallow())
                    attr_list.append(rh_obj.Attributes.Duplicate())
            
            sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geo_list, attr_list)
        rs.DeleteObjects(copied_geos)
        print("Définition '{}' mise à jour.".format(final_name))

    else:
        rs.AddBlock(copied_geos, [0, 0, 0], final_name, delete_input=False)
        rs.DeleteObjects(copied_geos)
        print("Bloc '{}' créé.".format(final_name))

    # ── 8. Insertion de l'instance à l'origine choisie ────────────────────────
    new_inst = rs.InsertBlock(final_name, [0, 0, 0])
    if new_inst:
        rs.TransformObject(new_inst, origin_xform)
        rs.DeleteObjects(obj_ids)
        rs.SelectObject(new_inst)

    rs.EnableRedraw(True)
    print("defineBlock terminé : bloc '{}' inséré à l'origine définie.".format(final_name))


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    defineBlock()

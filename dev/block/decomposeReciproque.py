# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import uuid

def _get_highest_level(obj_ids):
    """Trouve le niveau X le plus élevé dans les clés 'BlockNameLevel_X'."""
    max_level = -1
    for obj in obj_ids:
        keys = rs.GetUserText(obj)
        if keys:
            for k in keys:
                if k.startswith("BlockNameLevel_"):
                    try:
                        lvl = int(k.split("_")[-1])
                        if lvl > max_level: max_level = lvl
                    except: list
    return max_level

def _update_or_create_block(block_name, geometries, xform_to_local):
    """Crée ou met à jour la définition du bloc en utilisant RhinoCommon."""
    parent_def = sc.doc.InstanceDefinitions.Find(block_name, False)
    
    new_geoms = []
    new_attrs = []
    
    for g_id in geometries:
        obj_rhino = rs.coercerhinoobject(g_id)
        if not obj_rhino: continue
        
        # On duplique et on transforme vers l'origine du bloc (0,0,0)
        geom = obj_rhino.Geometry.Duplicate()
        geom.Transform(xform_to_local)
        attr = obj_rhino.Attributes.Duplicate()
        
        # On retire la clé du niveau actuel pour les objets à l'intérieur du bloc
        # pour éviter les conflits lors d'une future décomposition
        new_geoms.append(geom)
        new_attrs.append(attr)

    if not new_geoms: return False

    if parent_def:
        # Mise à jour
        return sc.doc.InstanceDefinitions.ModifyGeometry(parent_def.Index, new_geoms, new_attrs)
    else:
        # Création (le point de base est 0,0,0 car on a déjà transformé la géométrie)
        return sc.doc.InstanceDefinitions.Add(block_name, "", Rhino.Geometry.Point3d.Origin, new_geoms, new_attrs)

def rebuild_from_deconstruction():
    # 1. Sélection des objets
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    # 2. Identifier le niveau de reconstruction (le plus haut)
    level = _get_highest_level(initial_objs)
    if level == -1:
        print("Aucune information de déconstruction trouvée sur ces objets.")
        return

    level_key = "BlockNameLevel_{}".format(level)
    
    # 3. Grouper les objets par leur identifiant de bloc (Nom#Index)
    groups = {}
    for obj in initial_objs:
        val = rs.GetUserText(obj, level_key)
        if val:
            if val not in groups: groups[val] = []
            groups[val].append(obj)

    rs.EnableRedraw(False)

    for group_val, items in groups.items():
        block_name = group_val.split("#")[0]
        
        # Trouver le bloc "Pose" dans ce groupe
        pose_obj = None
        other_geoms = []
        for item in items:
            if rs.IsBlockInstance(item) and rs.BlockInstanceName(item) == "Pose":
                pose_obj = item
            else:
                other_geoms.append(item)
        
        if not pose_obj:
            print("Avertissement : Bloc 'Pose' manquant pour {}. Reconstruction impossible.".format(group_val))
            continue

        # 4. Calculer la transformation
        # M = Matrice de l'instance "Pose" (Position/Orientation actuelle)
        # On veut l'inverse pour ramener les objets vers le 0,0,0 du bloc
        pose_xform = rs.BlockInstanceXform(pose_obj)
        success_inv, inv_xform = pose_xform.TryGetInverse()
        
        if not success_inv:
            print("Erreur de calcul de matrice pour {}.".format(block_name))
            continue

        # 5. Créer/Modifier la définition
        # On retire les UserTexts du niveau actuel sur les objets composants
        for item in other_geoms:
            rs.SetUserText(item, level_key, "")

        if _update_or_create_block(block_name, other_geoms, inv_xform):
            # 6. Insérer l'instance et nettoyer
            new_inst = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(new_inst, pose_xform)
            
            # Transférer les UserTexts des niveaux inférieurs au nouveau bloc instance
            for item in items:
                keys = rs.GetUserText(item)
                if keys:
                    for k in keys:
                        # On ne garde que les niveaux inférieurs (ex: si on reconstruit le niveau 2, on garde 0 et 1)
                        if k.startswith("BlockNameLevel_"):
                            try:
                                k_lvl = int(k.split("_")[-1])
                                if k_lvl < level:
                                    rs.SetUserText(new_inst, k, rs.GetUserText(item, k))
                            except: pass
            
            # Supprimer les anciens objets et la Pose
            rs.DeleteObjects(items)
            rs.SelectObject(new_inst)
            print("Reconstruit : {} (Niveau {})".format(block_name, level))
        else:
            print("Erreur lors de la mise à jour de la définition : {}".format(block_name))

    rs.EnableRedraw(True)

if __name__ == "__main__":
    rebuild_from_deconstruction()

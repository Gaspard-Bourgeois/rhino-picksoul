# -*- coding: utf-8 -*-
import rhscriptsyntax as rs

def get_hierarchy_map(obj_ids):
    """
    Classe les objets par signature d'instance (block_name#Y) 
    pour le niveau hiérarchique le plus élevé (X max) de chaque objet.
    """
    mapping = {}
    for obj in obj_ids:
        keys = rs.GetUserText(obj)
        max_lvl = -1
        signature = "Root" # Pour les objets sans UserText

        if keys:
            for k in keys:
                if k.startswith("BlockNameLevel_"):
                    try:
                        lvl = int(k.split("_")[-1])
                        if lvl > max_lvl:
                            max_lvl = lvl
                            signature = rs.GetUserText(obj, k)
                    except: continue
        
        if signature not in mapping:
            mapping[signature] = {"level": max_lvl, "objects": [], "pose": None}
        
        # Identification de l'objet Pose (trièdre)
        if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
            mapping[signature]["pose"] = obj
        else:
            mapping[signature]["objects"].append(obj)
            
    return mapping

def clean_name(signature):
    """Retire l'indice #Y et les suffixes de copie pour obtenir le nom du bloc."""
    if "#" in signature:
        name = signature.split("#")[0]
    else:
        name = signature
    
    # Nettoyage des suffixes classiques
    if name.lower().endswith("_base"): name = name[:-5]
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit():
        name = name[:-3]
    return name

def rebuild_reciproque():
    rs.EnableRedraw(False)
    
    # 1. Sélection
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    # --- TODO: CLASSEMENT ET VÉRIFICATION DES ORIGINES ---
    hierarchy_map = get_hierarchy_map(initial_objs)
    
    # Recherche des niveaux manquant d'une "Pose"
    missing_pose_levels = {}
    for sig, data in hierarchy_map.items():
        if sig == "Root": continue
        if data["pose"] is None:
            lvl = data["level"]
            if lvl not in missing_pose_levels: missing_pose_levels[lvl] = []
            missing_pose_levels[lvl].extend(data["objects"])

    # TODO: Si des origines manquent, on sélectionne le niveau le plus bas et on arrête
    if missing_pose_levels:
        lowest_lvl = max(missing_pose_levels.keys())
        rs.UnselectAllObjects()
        rs.SelectObjects(missing_pose_levels[lowest_lvl])
        rs.EnableRedraw(True)
        print("Origine(s) manquante(s) au niveau {}. Sélectionnez les objets pour définir l'origine.".format(lowest_lvl))
        return

    # --- TODO: RECONSTRUCTION RÉCURSIVE (Boucle par niveau) ---
    # On traite les niveaux du plus grand (plus profond) vers le plus petit (racine)
    unique_levels = sorted([d["level"] for sig, d in hierarchy_map.items() if sig != "Root"], reverse=True)
    
    # On ajoute Root à la fin si nécessaire
    if "Root" in hierarchy_map:
        unique_levels.append(-1)

    current_selection = list(initial_objs)

    for current_lvl in unique_levels:
        # On recalcule la map à chaque niveau car les objets changent (deviennent des blocs)
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl or sig == "Root":
                continue
            
            pose_obj = data["pose"]
            geometries = data["objects"]
            if not pose_obj or not geometries: continue

            target_name = clean_name(sig)
            xform = rs.BlockInstanceXform(pose_obj)
            inv_xform = rs.XformInverse(xform)

            # Préparation des géométries pour le bloc
            copied_geos = []
            for g in geometries:
                cp = rs.CopyObject(g)
                rs.TransformObject(cp, inv_xform)
                copied_geos.append(cp)

            # Création/Mise à jour du bloc
            rs.AddBlock(copied_geos, [0,0,0], target_name, delete_input=True)
            
            # Insertion de la nouvelle instance
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # TODO: Transmission des UserTexts parents à la nouvelle instance
            # (On retire le niveau actuel pour que l'objet remonte d'un cran)
            all_user_texts = rs.GetUserText(geometries[0])
            if all_user_texts:
                for k in all_user_texts:
                    if k == "BlockNameLevel_{}".format(current_lvl): continue
                    rs.SetUserText(new_inst, k, rs.GetUserText(geometries[0], k))

            # Nettoyage de l'ancien niveau
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            
            # Mise à jour de la sélection pour le prochain niveau
            current_selection = [obj for obj in current_selection if obj not in geometries and obj != pose_obj]
            current_selection.append(new_inst)

    rs.EnableRedraw(True)
    print("Reconstruction hiérarchique terminée.")

if __name__ == "__main__":
    rebuild_reciproque()

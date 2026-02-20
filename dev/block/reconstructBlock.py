# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def get_bbox_center(obj_id):
    """Calcule le centre d'une BoundingBox pour l'origine manuelle."""
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return [0,0,0]
    pt_min = bbox[0]
    pt_max = bbox[6]
    return [(pt_min[i] + pt_max[i]) / 2.0 for i in range(3)]

def ensure_pose_block():
    """S'assure que la définition du bloc 'Pose' existe dans le document."""
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        p1 = [0,0,0]
        l1 = rs.AddLine(p1, [1,0,0]); rs.ObjectColor(l1, [255,0,0])
        l2 = rs.AddLine(p1, [0,1,0]); rs.ObjectColor(l2, [0,255,0])
        l3 = rs.AddLine(p1, [0,0,1]); rs.ObjectColor(l3, [0,0,255])
        rs.AddBlock([l1, l2, l3], p1, "Pose", True)
        rs.EnableRedraw(True)
    return "Pose"

def get_hierarchy_map(obj_ids):
    """Classe les objets par signature d'instance (block_name#Y)."""
    mapping = {}
    for obj in obj_ids:
        if not rs.IsObject(obj): continue
        keys = rs.GetUserText(obj)
        max_lvl = -1
        signature = "Root"
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
        
        if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
            mapping[signature]["pose"] = obj
        else:
            mapping[signature]["objects"].append(obj)
    return mapping

def clean_name(signature):
    """Nettoie le nom du bloc (enlève l'indice et les suffixes)."""
    name = signature.split("#")[0] if "#" in signature else signature
    if name.lower().endswith("_base"): name = name[:-5]
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit(): name = name[:-3]
    return name

def rebuild_reciproque():
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    
    current_selection = list(initial_objs)
    hierarchy_map = get_hierarchy_map(current_selection)
    
    # --- VÉRIFICATION ET REDÉFINITION DE L'ORIGINE ---
    missing_pose_sigs = [sig for sig, d in hierarchy_map.items() if sig != "Root" and d["pose"] is None]
    
    if missing_pose_sigs:
        levels_missing = [hierarchy_map[sig]["level"] for sig in missing_pose_sigs]
        if len(set(levels_missing)) > 1:
            lowest_lvl = max(levels_missing)
            objs_to_fix = [o for sig in missing_pose_sigs if hierarchy_map[sig]["level"] == lowest_lvl for o in hierarchy_map[sig]["objects"]]
            rs.UnselectAllObjects()
            rs.SelectObjects(objs_to_fix)
            rs.EnableRedraw(True)
            print("Plusieurs niveaux manquent d'origine. Sélectionnez l'origine pour le niveau {}.".format(lowest_lvl))
            return
        
        rs.EnableRedraw(True)
        for sig in missing_pose_sigs:
            ref_id = rs.GetObject("Origine manquante pour {}. Sélectionnez une référence (ou Entrée pour Monde)".format(sig))
            xform = rs.BlockInstanceXform(ref_id) if rs.IsBlockInstance(ref_id) else rs.XformTranslation(get_bbox_center(ref_id)) if ref_id else rs.XformIdentity()
            
            # Ajouter les UserText à la pose pour la récursion ---
            temp_pose = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(temp_pose, xform)
            
            ref_obj = hierarchy_map[sig]["objects"][0]
            keys = rs.GetUserText(ref_obj)
            for k in keys:
                if k.startswith("BlockNameLevel_"):
                    rs.SetUserText(temp_pose, k, rs.GetUserText(ref_obj, k))
            
            current_selection.append(temp_pose)
        rs.EnableRedraw(False)

    # --- RECONSTRUCTION RÉCURSIVE ---
    hierarchy_map = get_hierarchy_map(current_selection)
    unique_levels = sorted([d["level"] for sig, d in hierarchy_map.items() if sig != "Root"], reverse=True)
    if "Root" in hierarchy_map: unique_levels.append(-1)

    for current_lvl in unique_levels:
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl or sig == "Root": continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            original_name = clean_name(sig)
            target_name = original_name
            xform = rs.BlockInstanceXform(pose_obj)

            # Gestion du renommage
            if rs.IsBlock(target_name):
                #TODO : insérer temporairement l'instance de bloc qui pourrait être écrasé aux coordonnée xform
                #TODO : selectionner les objets du niveau hiérarchique qui seront utilisé remplacer l'instance avant de poser la question
                rs.EnableRedraw(True)
                res = rs.GetString("Le bloc '{}' existe déjà".format(target_name), "Ecraser", ["Ecraser", "Renommer", "Annuler"])
                rs.EnableRedraw(False)
                #TODO : supprimer l'instance temporaire
                
                if res == "Renommer":
                    target_name = rs.StringBox("Nouveau nom :", target_name, "Renommer le bloc")
                    if not target_name: continue
                    
                    # Mettre à jour les sigs dans current_selection ---
                    old_prefix = original_name + "#"
                    new_prefix = target_name + "#"
                    for obj in current_selection:
                        obj_keys = rs.GetUserText(obj)
                        for ok in obj_keys:
                            if ok.startswith("BlockNameLevel_"):
                                val = rs.GetUserText(obj, ok)
                                if val.startswith(old_prefix):
                                    rs.SetUserText(obj, ok, val.replace(old_prefix, new_prefix))
                elif res == "Annuler" or not res: continue

            # Reconstruction
            inv_xform = rs.XformInverse(xform)
            copied_geos = []
            for g in geometries:
                cp = rs.CopyObject(g)
                rs.TransformObject(cp, inv_xform)
                # Nettoyage UserText interne
                for k in rs.GetUserText(cp):
                    if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, None)
                copied_geos.append(cp)

            rs.AddBlock(copied_geos, [0,0,0], target_name, delete_input=True)
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # Transmission UserText parent
            parent_keys = rs.GetUserText(geometries[0])
            if parent_keys:
                for k in parent_keys:
                    if k != "BlockNameLevel_{}".format(current_lvl):
                        rs.SetUserText(new_inst, k, rs.GetUserText(geometries[0], k))

            # Nettoyage
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            current_selection = [obj for obj in current_selection if obj not in geometries and obj != pose_obj]
            current_selection.append(new_inst)

    rs.EnableRedraw(True)
    if current_selection: rs.SelectObjects(current_selection)
    print("Reconstruction terminée.")

if __name__ == "__main__":
    rebuild_reciproque()

# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import uuid

def get_bbox_center(obj_id):
    """Calcule le centre d'une BoundingBox pour l'origine manuelle."""
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return [0,0,0]
    pt_min = bbox[0]
    pt_max = bbox[6]
    return [(pt_min[i] + pt_max[i]) / 2.0 for i in range(3)]

def ensure_pose_block():
    """S'assure que la définition du bloc 'Pose' existe."""
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
    
    # --- VÉRIFICATION ORIGINES ---
    h_map = get_hierarchy_map(current_selection)
    missing = [sig for sig, d in h_map.items() if sig != "Root" and d["pose"] is None]
    
    if missing:
        levels = [h_map[sig]["level"] for sig in missing]
        low_lvl = max(levels)
        objs_to_fix = [o for sig in missing if h_map[sig]["level"] == low_lvl for o in h_map[sig]["objects"]]
        if set(current_selection) != set(objs_to_fix):
            rs.UnselectAllObjects()
            rs.SelectObjects(objs_to_fix)
            rs.EnableRedraw(True)
            print("Origine manquante au niveau {}.".format(low_lvl))
            return
        
        rs.EnableRedraw(True)
        for sig in missing:
            ref_id = rs.GetObject("Origine pour {}. (Entrée = Monde)".format(sig))
            xform = rs.BlockInstanceXform(ref_id) if rs.IsBlockInstance(ref_id) else rs.XformTranslation(get_bbox_center(ref_id)) if ref_id else rs.XformIdentity()
            temp_pose = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(temp_pose, xform)
            ref_obj = h_map[sig]["objects"][0]
            for k in rs.GetUserText(ref_obj):
                if k.startswith("BlockNameLevel_"): rs.SetUserText(temp_pose, k, rs.GetUserText(ref_obj, k))
            current_selection.append(temp_pose)
        rs.EnableRedraw(False)

    # --- RECONSTRUCTION ---
    h_map = get_hierarchy_map(current_selection)
    unique_levels = sorted([d["level"] for sig, d in h_map.items() if sig != "Root"], reverse=True)

    for current_lvl in unique_levels:
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl or sig == "Root": continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            original_name = clean_name(sig)
            target_name = original_name
            xform = rs.BlockInstanceXform(pose_obj)
            
            skip_reconstruction = False
            user_action = "Ecraser"

            # --- BOUCLE DE VALIDATION DU NOM ---
            while rs.IsBlock(target_name):
                rs.UnselectAllObjects()
                rs.SelectObjects(geometries)
                rs.SelectObject(pose_obj)
                
                # Visualisation du bloc conflictuel
                temp_compare = rs.InsertBlock(target_name, [0,0,0])
                rs.TransformObject(temp_compare, xform)
                rs.ObjectColor(temp_compare, [150, 150, 150]) # Gris
                
                rs.EnableRedraw(True)
                msg = "Le bloc '{}' existe déjà. Souhaitez-vous l'écraser ?".format(target_name)
                user_action = rs.GetString(msg, "Ecraser", ["Ecraser", "Renommer", "Conserver", "Annuler"])
                rs.EnableRedraw(False)
                rs.DeleteObject(temp_compare)
                
                if user_action == "Ecraser":
                    rs.RenameBlock(target_name, "temp_" + str(uuid.uuid4())[:8])
                    break # On sort de la boucle, le nom est libre
                elif user_action == "Renommer":
                    new_name = rs.StringBox("Nouveau nom :", target_name, "Renommer le bloc")
                    if not new_name:
                        user_action = "Annuler"
                        break
                    target_name = new_name
                    # La boucle continue pour vérifier si le NOUVEAU nom existe aussi
                elif user_action == "Conserver":
                    skip_reconstruction = True
                    break
                else: # Annuler ou Echap
                    user_action = "Annuler"
                    break
            
            if user_action == "Annuler": continue

            # --- MISE À JOUR DES SIGNATURES (si le nom a changé) ---
            if target_name != original_name:
                old_prefix = original_name + "#"
                new_prefix = target_name + "#"
                for obj in current_selection:
                    keys = rs.GetUserText(obj)
                    if keys:
                        for k in keys:
                            if k.startswith("BlockNameLevel_"):
                                val = rs.GetUserText(obj, k)
                                if val and val.startswith(old_prefix):
                                    rs.SetUserText(obj, k, val.replace(old_prefix, new_prefix))

            # --- RECONSTRUCTION GÉOMÉTRIQUE ---
            if not skip_reconstruction:
                inv_xform = rs.XformInverse(xform)
                copied_geos = []
                for g in geometries:
                    cp = rs.CopyObject(g)
                    rs.TransformObject(cp, inv_xform)
                    keys = rs.GetUserText(cp)
                    if keys:
                        for k in keys:
                            if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, None)
                    copied_geos.append(cp)
                
                rs.AddBlock(copied_geos, [0,0,0], target_name, delete_input=True)

            # Insertion nouvelle instance
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # Transmission UserText parent
            sample_obj = geometries[0]
            all_keys = rs.GetUserText(sample_obj)
            if all_keys:
                for k in all_keys:
                    if k.startswith("BlockNameLevel_"):
                        lvl_idx = int(k.split("_")[-1])
                        if lvl_idx < current_lvl:
                            rs.SetUserText(new_inst, k, rs.GetUserText(sample_obj, k))

            # Nettoyage
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            
            current_selection = [obj for obj in current_selection if obj not in geometries and obj != pose_obj]
            current_selection.append(new_inst)

    rs.EnableRedraw(True)
    if current_selection: rs.SelectObjects(current_selection)
    print("Terminé.")

if __name__ == "__main__":
    rebuild_reciproque()

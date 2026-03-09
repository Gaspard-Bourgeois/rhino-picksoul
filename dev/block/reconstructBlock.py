# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

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
    """
    Analyse les objets et les groupe par leur signature de bloc.
    Si aucun UserText n'est présent, les objets sont groupés sous 'NewBlock_0'.
    """
    mapping = {}
    for obj in obj_ids:
        if not rs.IsObject(obj): continue
        
        keys = rs.GetUserText(obj)
        max_lvl = 0 # Niveau par défaut pour les objets sans UserText
        signature = "NewBlock_0"
        
        has_block_info = False
        if keys:
            for k in keys:
                if k.startswith("BlockNameLevel_"):
                    try:
                        lvl = int(k.split("_")[-1])
                        if lvl >= 0:
                            max_lvl = lvl
                            signature = rs.GetUserText(obj, k)
                            has_block_info = True
                    except: continue
        
        if signature not in mapping:
            mapping[signature] = {"level": max_lvl, "objects": [], "pose": None}
        
        # Identification du bloc de pose
        if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
            mapping[signature]["pose"] = obj
        else:
            mapping[signature]["objects"].append(obj)
            
    return mapping

def clean_name(signature):
    """Nettoie le nom pour la création du bloc."""
    if signature == "NewBlock_0": return "NouveauBloc"
    name = signature.split("#")[0] if "#" in signature else signature
    if name.lower().endswith("_base"): name = name[:-5]
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit(): name = name[:-3]
    return name

def rebuild_reciproque():
    initial_objs = rs.GetObjects("Sélectionnez les objets (UserText ou simples)", preselect=True)
    if not initial_objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    current_selection = list(initial_objs)
    
    # --- PHASE 1 : VÉRIFICATION ET AJOUT DES ORIGINES ---
    h_map = get_hierarchy_map(current_selection)
    # On cherche les groupes qui n'ont pas de bloc "Pose" (sauf le Root s'il existait)
    missing = [sig for sig, d in h_map.items() if d["pose"] is None and d["objects"]]
    
    if missing:
        rs.EnableRedraw(True)
        for sig in missing:
            # Pour chaque groupe sans origine, on demande à l'utilisateur
            label = "objets simples" if sig == "NewBlock_0" else sig
            print("Définition de l'origine pour : {}".format(label))
            
            # Sélection de l'origine (Point, Objet pour centre BBox, ou Instance existante)
            ref_id = rs.GetObject("Sélectionnez l'objet de référence pour l'origine de '{}' (Entrée = [0,0,0])".format(label))
            
            if rs.IsBlockInstance(ref_id):
                xform = rs.BlockInstanceXform(ref_id)
            elif ref_id:
                xform = rs.XformTranslation(get_bbox_center(ref_id))
            else:
                xform = rs.XformIdentity()
            
            # Création et marquage de la Pose
            temp_pose = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(temp_pose, xform)
            
            # Si l'objet avait une signature, on l'applique à la pose pour le lien
            if sig != "NewBlock_0":
                ref_obj = h_map[sig]["objects"][0]
                for k in rs.GetUserText(ref_obj):
                    if k.startswith("BlockNameLevel_"):
                        rs.SetUserText(temp_pose, k, rs.GetUserText(ref_obj, k))
            else:
                # Pour les nouveaux objets, on leur donne une signature temporaire commune
                for o in h_map[sig]["objects"]:
                    rs.SetUserText(o, "BlockNameLevel_0", "NewBlock_0")
                rs.SetUserText(temp_pose, "BlockNameLevel_0", "NewBlock_0")
                
            current_selection.append(temp_pose)
        rs.EnableRedraw(False)

    # --- PHASE 2 : RECONSTRUCTION HIÉRARCHIQUE ---
    # On rafraîchit la map après l'ajout des poses
    h_map = get_hierarchy_map(current_selection)
    unique_levels = sorted(list(set([d["level"] for d in h_map.values()])), reverse=True)

    for current_lvl in unique_levels:
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl: continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            original_name = clean_name(sig)
            target_name = original_name
            xform = rs.BlockInstanceXform(pose_obj)
            
            user_action = "Ecraser"
            overwrite_block = False
            skip_reconstruction = False

            # Vérification de l'existence du bloc
            while rs.IsBlock(target_name):
                rs.UnselectAllObjects()
                rs.SelectObjects(geometries)
                rs.SelectObject(pose_obj)
                
                rs.EnableRedraw(True)
                user_action = rs.GetString("Le bloc '{}' existe déjà.".format(target_name), 
                                         "Ecraser", ["Ecraser", "Renommer", "Conserver", "Annuler"])
                rs.EnableRedraw(False)
                
                if user_action == "Ecraser":
                    overwrite_block = True
                    break 
                elif user_action == "Renommer":
                    target_name = rs.StringBox("Nouveau nom :", target_name, "Renommer le bloc")
                    if not target_name: user_action = "Annuler"; break
                elif user_action == "Conserver":
                    skip_reconstruction = True
                    break
                else:
                    user_action = "Annuler"
                    break
            
            if user_action == "Annuler": continue

            # Reconstruction
            if not skip_reconstruction:
                inv_xform = rs.XformInverse(xform)
                copied_geos = []
                for g in geometries:
                    cp = rs.CopyObject(g)
                    rs.TransformObject(cp, inv_xform)
                    # Nettoyage UserText sur le contenu du bloc
                    keys = rs.GetUserText(cp)
                    if keys:
                        for k in keys:
                            if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, "")
                    copied_geos.append(cp)
                
                if overwrite_block:
                    idef = sc.doc.InstanceDefinitions.Find(target_name)
                    geo_list = [sc.doc.Objects.Find(g).Geometry for g in copied_geos]
                    attr_list = [sc.doc.Objects.Find(g).Attributes for g in copied_geos]
                    sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geo_list, attr_list)
                    rs.DeleteObjects(copied_geos)
                else:
                    rs.AddBlock(copied_geos, [0,0,0], target_name, delete_input=True)

            # Insertion de la nouvelle instance
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # Transmission des niveaux parents (UserText)
            sample_obj = geometries[0]
            all_keys = rs.GetUserText(sample_obj)
            if all_keys:
                for k in all_keys:
                    if k.startswith("BlockNameLevel_"):
                        try:
                            lvl_idx = int(k.split("_")[-1])
                            if lvl_idx < current_lvl:
                                rs.SetUserText(new_inst, k, rs.GetUserText(sample_obj, k))
                        except: pass

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

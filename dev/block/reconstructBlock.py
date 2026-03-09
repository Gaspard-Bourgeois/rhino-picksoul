# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def get_bbox_center(obj_ids):
    bbox = rs.BoundingBox(obj_ids)
    if not bbox: return [0,0,0]
    return [(bbox[0][i] + bbox[6][i]) / 2.0 for i in range(3)]

def get_free_indexed_name():
    i = 1
    while True:
        name = "new_bloc_{:02d}".format(i)
        if not rs.IsBlock(name): return name
        i += 1

def ensure_pose_block():
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
        signature = None
        if keys:
            for k in keys:
                if k.startswith("BlockNameLevel_"):
                    try:
                        lvl = int(k.split("_")[-1])
                        if lvl > max_lvl:
                            max_lvl = lvl
                            signature = rs.GetUserText(obj, k)
                    except: continue
        
        if signature:
            if signature not in mapping:
                mapping[signature] = {"level": max_lvl, "objects": [], "pose": None}
            if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
                mapping[signature]["pose"] = obj
            else:
                mapping[signature]["objects"].append(obj)
    return mapping

def rebuild_reciproque():
    initial_objs = rs.GetObjects("Sélectionnez les objets", preselect=True)
    if not initial_objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    current_selection = list(initial_objs)
    
    # --- 1. TRAITEMENT DES OBJETS SIMPLES (AVANT LA BOUCLE) ---
    simple_objs = []
    for o in current_selection:
        keys = rs.GetUserText(o)
        is_hier = any(k.startswith("BlockNameLevel_") for k in keys) if keys else False
        if not is_hier and not (rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose"):
            simple_objs.append(o)
            
    if simple_objs:
        temp_name = get_free_indexed_name()
        center = get_bbox_center(simple_objs)
        # Création d'un bloc temporaire "muet"
        temp_geos = [rs.CopyObject(o) for o in simple_objs]
        xform_to_zero = rs.XformTranslation(rs.PointScale(center, -1))
        rs.TransformObjects(temp_geos, xform_to_zero)
        rs.AddBlock(temp_geos, [0,0,0], temp_name, delete_input=True)
        # On remplace les objets simples par l'instance + pose dans la sélection
        new_inst = rs.InsertBlock(temp_name, center)
        new_pose = rs.InsertBlock("Pose", center)
        rs.SetUserText(new_inst, "BlockNameLevel_0", temp_name)
        rs.SetUserText(new_pose, "BlockNameLevel_0", temp_name)
        
        for o in simple_objs: 
            if o in current_selection: current_selection.remove(o)
        rs.DeleteObjects(simple_objs)
        current_selection.extend([new_inst, new_pose])

    # --- 2. BOUCLE PRINCIPALE DE RECONSTRUCTION ---
    h_map = get_hierarchy_map(current_selection)
    unique_levels = sorted(list(set(d["level"] for d in h_map.values())), reverse=True)

    for current_lvl in unique_levels:
        # On rafraîchit la map à chaque niveau
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl: continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            original_sig = sig
            target_name = sig.split("#")[0] if "#" in sig else sig
            is_new_bloc = "new_bloc_" in sig
            
            # --- INTERFACE ---
            rs.UnselectAllObjects()
            rs.SelectObjects(geometries)
            rs.SelectObject(pose_obj)
            rs.EnableRedraw(True)
            
            if is_new_bloc:
                # Si c'est un nouveau bloc, on demande nom et origine comme s'il n'en avait pas
                target_name = rs.StringBox("Nom du nouveau bloc :", target_name)
                if not target_name: return
                
                ref_origin = rs.GetObject("Désignez l'origine (Point, Objet ou Entrée pour centre)", preselect=False)
                if ref_origin:
                    new_pos = get_bbox_center([ref_origin])
                    rs.MoveObject(pose_obj, new_pos - rs.BlockInstanceInsertPoint(pose_obj))
                else:
                    pt = rs.GetPoint("Ou cliquez un point (Entrée = centre actuel)")
                    if pt: rs.MoveObject(pose_obj, pt - rs.BlockInstanceInsertPoint(pose_obj))
                action = "Ecraser"
            else:
                action = rs.GetString("Bloc '{}' :".format(target_name), "Ecraser", ["Ecraser", "Renommer", "Conserver", "Annuler"])
                if action == "Renommer":
                    target_name = rs.StringBox("Nouveau nom :", target_name)
                elif action == "Conserver": continue
                elif action != "Ecraser": return

            rs.EnableRedraw(False)

            # Mise à jour des UserText si le nom a changé (pour ne pas casser les niveaux supérieurs)
            if target_name != original_sig:
                for o in current_selection:
                    for k in (rs.GetUserText(o) or []):
                        if k.startswith("BlockNameLevel_") and rs.GetUserText(o, k) == original_sig:
                            rs.SetUserText(o, k, target_name)

            # --- RECONSTRUCTION ---
            xform = rs.BlockInstanceXform(pose_obj)
            inv_xform = rs.XformInverse(xform)
            
            temp_geos = []
            for g in geometries:
                cp = rs.CopyObject(g)
                rs.TransformObject(cp, inv_xform)
                # Nettoyage des niveaux internes
                for k in (rs.GetUserText(cp) or []):
                    if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, "")
                temp_geos.append(cp)

            if rs.IsBlock(target_name):
                idef = sc.doc.InstanceDefinitions.Find(target_name)
                geos = [sc.doc.Objects.Find(g).Geometry for g in temp_geos]
                attrs = [sc.doc.Objects.Find(g).Attributes for g in temp_geos]
                sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geos, attrs)
                rs.DeleteObjects(temp_geos)
            else:
                rs.AddBlock(temp_geos, [0,0,0], target_name, delete_input=True)

            final_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(final_inst, xform)
            
            # Transmission des UserText vers le haut
            sample = geometries[0]
            for k in (rs.GetUserText(sample) or []):
                if k.startswith("BlockNameLevel_"):
                    if int(k.split("_")[-1]) < current_lvl:
                        rs.SetUserText(final_inst, k, rs.GetUserText(sample, k))

            # Nettoyage
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            current_selection = [o for o in current_selection if o not in geometries and o != pose_obj]
            current_selection.append(final_inst)

    rs.EnableRedraw(True)
    if current_selection: rs.SelectObjects(current_selection)
    print("Terminé.")

if __name__ == "__main__":
    rebuild_reciproque()

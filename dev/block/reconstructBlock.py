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
    simple_objects = []

    for obj in obj_ids:
        if not rs.IsObject(obj): continue
        keys = rs.GetUserText(obj)
        signature = None
        max_lvl = -1

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
        else:
            if not (rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose"):
                simple_objects.append(obj)

    # Si objets simples, on leur assigne un nom et on les ajoute au mapping
    if simple_objects:
        temp_name = get_free_indexed_name()
        mapping[temp_name] = {"level": 0, "objects": simple_objects, "pose": None}
        # On marque les objets pour que le script les reconnaisse au cycle suivant
        for o in simple_objects:
            rs.SetUserText(o, "BlockNameLevel_0", temp_name)
    
    return mapping

def rebuild_reciproque():
    initial_objs = rs.GetObjects("Sélectionnez les objets", preselect=True)
    if not initial_objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    
    # 1. Identifier et marquer les objets simples
    h_map = get_hierarchy_map(initial_objs)
    current_selection = list(initial_objs)

    # 2. Créer les poses manquantes (notamment pour les nouveaux blocs)
    for sig, data in h_map.items():
        if data["pose"] is None:
            center = get_bbox_center(data["objects"])
            temp_pose = rs.InsertBlock("Pose", center)
            rs.SetUserText(temp_pose, "BlockNameLevel_{}".format(data["level"]), sig)
            current_selection.append(temp_pose)

    # 3. Boucle de reconstruction par niveau
    # On rafraîchit la map pour inclure les nouvelles poses
    h_map = get_hierarchy_map(current_selection)
    unique_levels = sorted(list(set(d["level"] for d in h_map.values())), reverse=True)

    for current_lvl in unique_levels:
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl: continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            # DETERMINATION DU NOM
            is_new = "new_bloc_" in sig
            target_name = sig.split("#")[0] if "#" in sig else sig
            xform = rs.BlockInstanceXform(pose_obj)
            
            # FORCE LE RENOMMAGE SI OBJET SIMPLE
            rs.UnselectAllObjects()
            rs.SelectObjects(geometries)
            rs.SelectObject(pose_obj)
            rs.EnableRedraw(True)

            if is_new:
                target_name = rs.StringBox("Nom pour le nouveau bloc :", target_name, "Nouveau Bloc Détecté")
                if not target_name: return
                action = "Creer"
            else:
                action = rs.GetString("Bloc '{}' :".format(target_name), "Ecraser", ["Ecraser", "Renommer", "Conserver", "Annuler"])
            
            rs.EnableRedraw(False)

            if action == "Annuler" or not action: return
            if action == "Renommer":
                target_name = rs.StringBox("Nouveau nom :", target_name)
                if not target_name: return
            
            # CREATION DU BLOC
            inv_xform = rs.XformInverse(xform)
            temp_geos = []
            for g in geometries:
                cp = rs.CopyObject(g)
                rs.TransformObject(cp, inv_xform)
                # Nettoyage métadonnées internes
                for k in (rs.GetUserText(cp) or []):
                    if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, "")
                temp_geos.append(cp)

            if rs.IsBlock(target_name) and action == "Ecraser":
                idef = sc.doc.InstanceDefinitions.Find(target_name)
                geos = [sc.doc.Objects.Find(g).Geometry for g in temp_geos]
                attrs = [sc.doc.Objects.Find(g).Attributes for g in temp_geos]
                sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geos, attrs)
                rs.DeleteObjects(temp_geos)
            else:
                # Si le bloc existe et qu'on ne l'écrase pas, AddBlock échouera proprement ou créera une copie
                rs.AddBlock(temp_geos, [0,0,0], target_name, delete_input=True)

            # Insertion instance et mise à jour sélection
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # Transmission des UserText vers le haut (pour les parents)
            for k in (rs.GetUserText(geometries[0]) or []):
                if k.startswith("BlockNameLevel_"):
                    lvl_val = int(k.split("_")[-1])
                    if lvl_val < current_lvl:
                        rs.SetUserText(new_inst, k, rs.GetUserText(geometries[0], k))

            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            current_selection = [o for o in current_selection if o not in geometries and o != pose_obj]
            current_selection.append(new_inst)

    rs.EnableRedraw(True)
    print("Terminé.")

if __name__ == "__main__":
    rebuild_reciproque()

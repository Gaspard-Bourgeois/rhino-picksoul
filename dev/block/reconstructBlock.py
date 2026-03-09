# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def get_bbox_center(obj_ids):
    """Calcule le centre de la BoundingBox pour l'origine des nouveaux blocs."""
    bbox = rs.BoundingBox(obj_ids)
    if not bbox: return [0,0,0]
    return [(bbox[0][i] + bbox[6][i]) / 2.0 for i in range(3)]

def get_free_indexed_name():
    """Génère le premier nom disponible de type new_bloc_01, 02..."""
    i = 1
    while True:
        name = "new_bloc_{:02d}".format(i)
        if not rs.IsBlock(name): return name
        i += 1

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
    """Analyse les objets et crée le mapping hiérarchique."""
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
            # Objet sans UserText (objet simple)
            if not (rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose"):
                simple_objects.append(obj)

    # Gestion des objets simples : on leur crée une signature "new_bloc_xx"
    if simple_objects:
        temp_name = get_free_indexed_name()
        mapping[temp_name] = {"level": 0, "objects": simple_objects, "pose": None}
    
    return mapping

def clean_name(signature):
    name = signature.split("#")[0] if "#" in signature else signature
    if name.lower().endswith("_base"): name = name[:-5]
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit(): name = name[:-3]
    return name

def rebuild_reciproque():
    initial_objs = rs.GetObjects("Sélectionnez les objets", preselect=True)
    if not initial_objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    current_selection = list(initial_objs)
    
    # --- PHASE 1 : ATTRIBUTION DES POSES ---
    h_map = get_hierarchy_map(current_selection)
    for sig, data in h_map.items():
        if data["pose"] is None:
            # Si pas de pose, on la crée au centre des objets
            center = get_bbox_center(data["objects"])
            temp_pose = rs.InsertBlock("Pose", center)
            # On marque la pose avec le UserText correspondant à la signature
            lvl_key = "BlockNameLevel_{}".format(data["level"])
            rs.SetUserText(temp_pose, lvl_key, sig)
            current_selection.append(temp_pose)

    # --- PHASE 2 : RECONSTRUCTION ---
    h_map = get_hierarchy_map(current_selection)
    unique_levels = sorted(list(set(d["level"] for d in h_map.values())), reverse=True)

    for current_lvl in unique_levels:
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl: continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            # Comportement spécifique : si c'est un "new_bloc", on force la demande de nom
            is_new = sig.startswith("new_bloc_")
            target_name = clean_name(sig)
            xform = rs.BlockInstanceXform(pose_obj)
            
            overwrite_block = False
            skip_reconstruction = False
            user_action = "Renommer" if is_new else "Ecraser"

            # --- BOUCLE DE VALIDATION ---
            while rs.IsBlock(target_name) or is_new:
                rs.UnselectAllObjects()
                rs.SelectObjects(geometries)
                rs.SelectObject(pose_obj)
                rs.EnableRedraw(True)
                
                msg = "Nom du bloc '{}' :".format(target_name)
                user_action = rs.GetString(msg, user_action, ["Ecraser", "Renommer", "Conserver", "Annuler"])
                rs.EnableRedraw(False)
                
                if user_action == "Renommer":
                    new_name = rs.StringBox("Saisir le nom final :", target_name, "Définition de bloc")
                    if not new_name: return
                    target_name = new_name
                    is_new = False # Sortie de la boucle forcée après premier renommage
                    if not rs.IsBlock(target_name): break
                elif user_action == "Ecraser":
                    overwrite_block = True
                    break
                elif user_action == "Conserver":
                    skip_reconstruction = True
                    break
                else: return # Annuler

            # --- RECONSTRUCTION GÉOMÉTRIQUE ---
            if not skip_reconstruction:
                inv_xform = rs.XformInverse(xform)
                temp_geos = []
                for g in geometries:
                    cp = rs.CopyObject(g)
                    rs.TransformObject(cp, inv_xform)
                    # Nettoyage UserText pour les enfants du nouveau bloc
                    for k in (rs.GetUserText(cp) or []):
                        if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, "")
                    temp_geos.append(cp)
                
                if overwrite_block and rs.IsBlock(target_name):
                    idef = sc.doc.InstanceDefinitions.Find(target_name)
                    geo_list = [sc.doc.Objects.Find(g).Geometry for g in temp_geos]
                    attr_list = [sc.doc.Objects.Find(g).Attributes for g in temp_geos]
                    sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geo_list, attr_list)
                    rs.DeleteObjects(temp_geos)
                else:
                    rs.AddBlock(temp_geos, [0,0,0], target_name, delete_input=True)

            # Insertion de l'instance finale
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # Transmission des UserTexts aux niveaux parents si nécessaire
            sample_obj = geometries[0]
            for k in (rs.GetUserText(sample_obj) or []):
                if k.startswith("BlockNameLevel_"):
                    try:
                        lvl_idx = int(k.split("_")[-1])
                        if lvl_idx < current_lvl:
                            rs.SetUserText(new_inst, k, rs.GetUserText(sample_obj, k))
                    except: pass

            # Nettoyage
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            current_selection = [o for o in current_selection if o not in geometries and o != pose_obj]
            current_selection.append(new_inst)

    rs.EnableRedraw(True)
    if current_selection: rs.SelectObjects(current_selection)
    print("Traitement terminé.")

if __name__ == "__main__":
    rebuild_reciproque()

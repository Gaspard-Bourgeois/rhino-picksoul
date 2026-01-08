# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def get_program_from_selection(selected_ids):
    """Retrouve les programmes liés aux éléments sélectionnés"""
    target_layers = set()
    for s_id in selected_ids:
        lyr = rs.ObjectLayer(s_id)
        if lyr:
            target_layers.add(lyr)
            parent = rs.ParentLayer(lyr)
            if parent: target_layers.add(parent)
    
    all_objs = rs.ObjectsByType(4096) # Instances de blocs
    programs = []
    if all_objs:
        for obj in all_objs:
            if rs.GetUserText(obj, "type") == "program":
                if rs.ObjectLayer(obj) in target_layers:
                    programs.append(obj)
    return list(set(programs))

def get_pose_copies(origin_uuid, all_pose_instances, selected_ids=None):
    """Cherche les copies manuelles d'une pose spécifique"""
    copies = []
    for inst in all_pose_instances:
        if str(inst) != origin_uuid:
            if rs.GetUserText(inst, "uuid_origin") == origin_uuid:
                if selected_ids:
                    if str(inst) in selected_ids: copies.append(inst)
                else:
                    copies.append(inst)
    return copies

def rebuild_trajectories():
    print("\n=== REBUILD TRAJECTOIRES : FIX NUMEROTATION & FORMAT 000X ===")
    
    # --- 1. SÉLECTION ET INITIALISATION ---
    selected = rs.SelectedObjects()
    selected_ids_str = [str(s) for s in selected] if selected else []
    
    all_instances = rs.ObjectsByType(4096) or []
    all_progs = [obj for obj in all_instances if rs.GetUserText(obj, "type") == "program"]
    all_poses_in_doc = [p for p in all_instances if rs.BlockInstanceName(p) == "Pose"]

    target_programs = []
    if not selected:
        if not all_progs: return
        choices = [rs.ObjectLayer(p) for p in all_progs]
        picked = rs.MultiListBox(choices, "Programmes à éditer", "Rebuild JBI")
        if not picked: return
        target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
    else:
        target_programs = get_program_from_selection(selected)
        if not target_programs:
            print("Selection invalide: Selectionnez un element du programme.")
            return

    rs.EnableRedraw(False)
    
    for prog_id in target_programs:
        prog_layer = rs.ObjectLayer(prog_id)
        print("Programme : " + prog_layer)
        
        # --- 2. RECUPERATION DES COURBES (Originales + Copies) ---
        original_crv_uuids = []
        i = 0
        while True:
            # On cherche Crv_0000, Crv_0001... (format souhaité)
            # Mais on checke aussi l'ancien format Crv_0 pour compatibilité ascendante
            key_new = "Crv_{:04d}".format(i)
            key_old = "Crv_{}".format(i)
            
            u = rs.GetUserText(prog_id, key_new)
            if not u: u = rs.GetUserText(prog_id, key_old)
            
            if not u: break
            if rs.IsObject(u): original_crv_uuids.append(u)
            i += 1
        
        # Identification des copies de courbes
        all_curves = rs.ObjectsByType(4) or []
        curve_copies = []
        for c_id in all_curves:
            origin = rs.GetUserText(c_id, "uuid_origin")
            if origin in original_crv_uuids and str(c_id) != origin:
                if selected:
                    if str(c_id) in selected_ids_str: curve_copies.append(c_id)
                else:
                    curve_copies.append(c_id)

        # Choix position courbes copiées
        insert_mode_crv = "After"
        if curve_copies:
            res = rs.ListBox(["Avant", "Après"], "Position des COPIES DE COURBES ?", "Ordre Courbes")
            if res: insert_mode_crv = res

        # Construction de la liste ORDONNÉE des courbes
        ordered_curve_list = []
        for o_crv in original_crv_uuids:
            relevant_copies = [c for c in curve_copies if rs.GetUserText(c, "uuid_origin") == o_crv]
            if insert_mode_crv == "Avant":
                ordered_curve_list.extend(relevant_copies)
                ordered_curve_list.append(o_crv)
            else:
                ordered_curve_list.append(o_crv)
                ordered_curve_list.extend(relevant_copies)

        # Choix position poses copiées (une fois globalement)
        pose_insert_mode = "After"
        # Check rapide s'il y a des copies
        has_pose_copies = any(rs.GetUserText(p, "uuid_origin") and rs.GetUserText(p, "uuid_origin") != str(p) for p in all_poses_in_doc)
        if has_pose_copies:
            res_p = rs.ListBox(["Avant", "Après"], "Position des COPIES DE POSES ?", "Ordre Poses")
            if res_p: pose_insert_mode = res_p

        # --- 3. RECONSTRUCTION LINEAIRE DES POSES ---
        final_pose_objects = [] # Liste plate de tous les UUIDs de poses finaux
        
        for crv_id in ordered_curve_list:
            is_copy_crv = (rs.GetUserText(crv_id, "uuid_origin") != str(crv_id))
            ref_crv = rs.GetUserText(crv_id, "uuid_origin") if is_copy_crv else str(crv_id)
            
            # Récupération des poses stockées dans la courbe de référence
            # On supporte Pt_0000 et Pt_0
            poses_in_curve = []
            p_idx = 0
            while True:
                # Essai format 000X puis X
                p_uuid = rs.GetUserText(ref_crv, "UUID_{:04d}".format(p_idx))
                if not p_uuid: p_uuid = rs.GetUserText(ref_crv, "UUID_{}".format(p_idx))
                
                if not p_uuid: break
                poses_in_curve.append(p_uuid)
                p_idx += 1
            
            if not is_copy_crv:
                # CAS A : COURBE ORIGINALE (Existante)
                for p_uuid in poses_in_curve:
                    if not rs.IsObject(p_uuid): continue
                    
                    # Gestion des copies de poses (doublons)
                    copies_of_this_pose = get_pose_copies(p_uuid, all_poses_in_doc, selected_ids_str)
                    
                    if pose_insert_mode == "Avant":
                        final_pose_objects.extend(copies_of_this_pose)
                        final_pose_objects.append(p_uuid)
                    else:
                        final_pose_objects.append(p_uuid)
                        final_pose_objects.extend(copies_of_this_pose)
            else:
                # CAS B : COURBE COPIÉE (Nouvelle trajectoire)
                # Création physique de nouvelles poses sur les sommets
                pts = rs.PolylineVertices(crv_id)
                # On ignore le dernier point si polyligne fermée identiquement au premier (rare en robotique mais possible)
                if len(pts) > 1 and rs.Distance(pts[0], pts[-1]) < 0.001: pts.pop()
                
                count = min(len(pts), len(poses_in_curve))
                
                for k in range(count):
                    orig_pose_id = poses_in_curve[k]
                    if rs.IsObject(orig_pose_id):
                        # 1. Copier la pose référence
                        new_pose = rs.CopyObject(orig_pose_id)
                        # 2. La déplacer au bon endroit (Sommet de la courbe copiée)
                        curr_pt = rs.BlockInstanceInsertPoint(new_pose)
                        translation = pts[k] - curr_pt
                        rs.MoveObject(new_pose, translation)
                        # 3. Ajouter à la liste finale
                        final_pose_objects.append(new_pose)

        # --- 4. MISE A JOUR DES POSES (Renommage & UUID Origin) ---
        pose_data_list = []
        
        # C'est ici qu'on assure la continuité : idx va de 0 à N sans interruption
        for idx, p_id in enumerate(final_pose_objects):
            if not rs.IsObject(p_id): continue
            
            # Format Nom : 0000, 0001, etc.
            new_name = "{:04d}".format(idx)
            rs.ObjectName(p_id, new_name)
            
            # MISE A JOUR CRITIQUE : l'élément devient sa propre origine
            # Cela permet aux futurs rebuilds de fonctionner sur cette nouvelle base
            rs.SetUserText(p_id, "uuid_origin", str(p_id))
            
            state = rs.GetUserText(p_id, "State") or "ARCOF"
            
            pose_data_list.append({
                'idx': new_name, # Stocké en string "0005"
                'uuid': str(p_id),
                'state': state,
                'pos': rs.BlockInstanceInsertPoint(p_id) # Position réelle mise à jour
            })

        # Nettoyage anciennes courbes
        rs.DeleteObjects(original_crv_uuids)
        if curve_copies: rs.DeleteObjects(curve_copies)

        # --- 5. RECONSTRUCTION GEOMETRIQUE DES COURBES ---
        # Préparation Layer
        parent_lyr = rs.ParentLayer(prog_layer)
        traj_lyr_name = "trajs_arcon_arcof"
        full_traj_lyr = (parent_lyr + "::" + traj_lyr_name) if parent_lyr else traj_lyr_name
        
        if not rs.IsLayer(full_traj_lyr): 
            # Fallback simple
            if rs.IsLayer(prog_layer + "::" + traj_lyr_name):
                 full_traj_lyr = prog_layer + "::" + traj_lyr_name
            else:
                 rs.AddLayer(traj_lyr_name, parent=prog_layer)
                 full_traj_lyr = prog_layer + "::" + traj_lyr_name
                 
        rs.CurrentLayer(full_traj_lyr)
        
        new_crv_uuids = []

        if len(pose_data_list) > 1:
            
            def create_poly(seg_data, is_arcon):
                if len(seg_data) < 2: return
                pts = [d['pos'] for d in seg_data]
                nc = rs.AddPolyline(pts)
                
                st_lbl = "ARCON" if is_arcon else "ARCOF"
                # Nom : ARCON_0005-0010
                rs.ObjectName(nc, "{}_{}-{}".format(st_lbl, seg_data[0]['idx'], seg_data[-1]['idx']))
                
                col = (255,0,0) if is_arcon else (150,150,150)
                rs.ObjectColor(nc, col)
                
                rs.SetUserText(nc, "uuid_origin", str(nc))
                
                # Formatage des UserStrings : Pt_0000, UUID_0000
                for k, d in enumerate(seg_data):
                    rs.SetUserText(nc, "Pt_{:04d}".format(k), d['idx'])
                    rs.SetUserText(nc, "UUID_{:04d}".format(k), d['uuid'])
                    
                new_crv_uuids.append(str(nc))

            # Segmentation logique ARCON/ARCOF
            current_seg = [pose_data_list[0]]
            # État initial défini par le premier segment (p0 -> p1) donc l'état de p1
            current_state_arcon = False
            if len(pose_data_list) > 1:
                current_state_arcon = (pose_data_list[1]['state'] == "ARCON")

            for i in range(1, len(pose_data_list)):
                p_curr = pose_data_list[i]
                is_arcon = (p_curr['state'] == "ARCON")
                
                # Si l'état change, on coupe
                if is_arcon != current_state_arcon:
                    create_poly(current_seg, current_state_arcon)
                    current_seg = [pose_data_list[i-1], p_curr] # On chaine
                    current_state_arcon = is_arcon
                else:
                    current_seg.append(p_curr)
            
            # Dernier segment
            create_poly(current_seg, current_state_arcon)

        # --- 6. MISE A JOUR BLOC PROGRAMME ---
        # Nettoyage clés
        keys = rs.GetUserText(prog_id)
        if keys:
            for k in keys:
                if k.startswith("Crv_"): rs.SetUserText(prog_id, k, "")
        
        # Ecriture format Crv_000X
        for i, u in enumerate(new_crv_uuids):
            rs.SetUserText(prog_id, "Crv_{:04d}".format(i), u)
            
        print("Rebuild termine. {} poses, {} courbes.".format(len(pose_data_list), len(new_crv_uuids)))

    rs.EnableRedraw(True)

if __name__ == "__main__":
    rebuild_trajectories()

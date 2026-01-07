# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def get_program_from_selection(selected_ids):
    target_layers = set()
    for s_id in selected_ids:
        lyr = rs.ObjectLayer(s_id)
        target_layers.add(lyr)
        parent = rs.ParentLayer(lyr)
        if parent: target_layers.add(parent)
    
    all_objs = rs.ObjectsByType(16) # Instances de blocs
    programs = []
    if all_objs:
        for obj in all_objs:
            if rs.GetUserText(obj, "type") == "program":
                if rs.ObjectLayer(obj) in target_layers:
                    programs.append(obj)
    return list(set(programs))

def rebuild_trajectories():
    # --- Étape 1 : Choix des programmes ---
    selected = rs.SelectedObjects()
    target_programs = []
    
    all_instances = rs.ObjectsByType(16) or []
    all_progs = [obj for obj in all_instances if rs.GetUserText(obj, "type") == "program"]

    if not selected:
        if not all_progs:
            print("Aucun programme trouvé.")
            return
        choices = [rs.ObjectLayer(p) for p in all_progs]
        picked = rs.MultiListBox(choices, "Programmes à éditer", "Rebuild JBI")
        if not picked: return
        target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
    else:
        target_programs = get_program_from_selection(selected)
        if not target_programs:
            print("Aucun programme associé à la sélection.")
            return

    rs.EnableRedraw(False)
    
    for prog_id in target_programs:
        prog_layer = rs.ObjectLayer(prog_id)
        print("--- Rebuild : {} ---".format(prog_layer))
        
        # Stats Debug
        stats = {"pose_in": 0, "pose_out": 0, "crv_in": 0, "crv_out": 0}

        # --- Étape 2 : Identification des courbes ---
        original_crv_uuids = []
        i = 0
        while True:
            u = rs.GetUserText(prog_id, "Crv_{}".format(i))
            if not u: break
            if rs.IsObject(u): original_crv_uuids.append(u)
            i += 1
        stats["crv_in"] = len(original_crv_uuids)

        # Doublons de courbes
        all_curves = rs.ObjectsByType(4) or []
        curve_copies = []
        for c_id in all_curves:
            origin = rs.GetUserText(c_id, "uuid_origin")
            if origin in original_crv_uuids and str(c_id) != origin:
                if selected:
                    if str(c_id) in [str(s) for s in selected]: curve_copies.append(c_id)
                else: curve_copies.append(c_id)

        insert_mode_crv = 1
        if curve_copies:
            res = rs.ListBox(["Avant", "Après"], "Position des copies de courbes", prog_layer)
            insert_mode_crv = 0 if res == "Avant" else 1

        # --- Étape 3 & 4 & 5 : Ordonnancement Global ---
        global_pose_list = []
        
        ordered_curves = []
        for o_crv in original_crv_uuids:
            relevant_copies = [c for c in curve_copies if rs.GetUserText(c, "uuid_origin") == o_crv]
            if insert_mode_crv == 0:
                ordered_curves.extend(relevant_copies)
                ordered_curves.append(o_crv)
            else:
                ordered_curves.append(o_crv)
                ordered_curves.extend(relevant_copies)

        for crv_id in ordered_curves:
            is_copy_crv = rs.GetUserText(crv_id, "uuid_origin") != str(crv_id)
            ref_crv = rs.GetUserText(crv_id, "uuid_origin") if is_copy_crv else str(crv_id)
            
            p_idx = 0
            while True:
                orig_pose_uuid = rs.GetUserText(ref_crv, "UUID_{}".format(p_idx))
                if not orig_pose_uuid: break
                
                # Trouver les copies de cette pose (Étape 3)
                # On filtre les instances dont le nom de bloc est "Pose"
                pose_copies = []
                for inst in all_instances:
                    if rs.BlockInstanceName(inst) == "Pose":
                        if rs.GetUserText(inst, "uuid_origin") == orig_pose_uuid and str(inst) != orig_pose_uuid:
                            if selected:
                                if str(inst) in [str(s) for s in selected]: pose_copies.append(inst)
                            else: pose_copies.append(inst)

                current_group = []
                if not is_copy_crv:
                    # Courbe originale : on garde l'originale et on ajoute les copies (doublons de pose)
                    current_group.append(orig_pose_uuid)
                    current_group.extend(pose_copies)
                else:
                    # Étape 4 : Courbe copiée -> création de nouvelles poses sur les points de la polyligne
                    pts = rs.PolylineVertices(crv_id)
                    if pts and p_idx < len(pts):
                        new_p = rs.CopyObject(orig_pose_uuid)
                        trans = pts[p_idx] - rs.BlockInstanceInsertPoint(orig_pose_uuid)
                        rs.MoveObject(new_p, trans)
                        current_group.append(new_p)

                for p_id in current_group:
                    global_pose_list.append(p_id)
                p_idx += 1

        # --- Étape 6 : Mise à jour UUID, Renommage et Nettoyage ---
        final_poses_clean = []
        for idx, p_id in enumerate(global_pose_list):
            rs.ObjectName(p_id, str(idx)) # Renommage (Étape 5)
            rs.SetUserText(p_id, "uuid_origin", str(p_id)) # Update UUID (Étape 6)
            final_poses_clean.append({
                'uuid': str(p_id),
                'state': rs.GetUserText(p_id, "State"),
                'pos': rs.BlockInstanceInsertPoint(p_id)
            })
        
        stats["pose_out"] = len(final_poses_clean)

        # Suppression anciennes courbes
        rs.DeleteObjects(original_crv_uuids)
        if curve_copies: rs.DeleteObjects(curve_copies)

        # --- Étape 6 (bis) : Création des nouvelles courbes ---
        # Préparation du calque
        traj_lyr_name = prog_layer + "::trajs_arcon_arcof"
        if not rs.IsLayer(traj_lyr_name): rs.AddLayer(traj_lyr_name)
        rs.CurrentLayer(traj_lyr_name)

        new_crv_uuids = []
        if len(final_poses_clean) > 1:
            def build_seg(data, is_arcon):
                if len(data) < 2: return
                nc = rs.AddPolyline([d['pos'] for d in data])
                lbl = "ARCON" if is_arcon else "ARCOF"
                rs.ObjectName(nc, "{}_{}-{}".format(lbl, rs.ObjectName(data[0]['uuid']), rs.ObjectName(data[-1]['uuid'])))
                rs.ObjectColor(nc, (255,0,0) if is_arcon else (150,150,150))
                rs.SetUserText(nc, "uuid_origin", str(nc))
                for j, d in enumerate(data):
                    rs.SetUserText(nc, "Pt_{}".format(j), rs.ObjectName(d['uuid']))
                    rs.SetUserText(nc, "UUID_{}".format(j), d['uuid'])
                new_crv_uuids.append(str(nc))

            # Logique : segment (i -> i+1) est ARCON si pose(i+1) est ARCON
            current_seg = [final_poses_clean[0]]
            for i in range(len(final_poses_clean)-1):
                p_start = final_poses_clean[i]
                p_end = final_poses_clean[i+1]
                
                # Détermine l'état du segment vers le point suivant
                seg_is_arcon = (p_end['state'] == "ARCON")
                
                # Si l'état change par rapport au segment en cours de construction
                # (Ou si c'est le premier segment)
                if i == 0:
                    current_state = seg_is_arcon
                
                if seg_is_arcon != current_state:
                    build_seg(current_seg, current_state)
                    current_seg = [p_start, p_end]
                    current_state = seg_is_arcon
                else:
                    current_seg.append(p_end)
            
            build_seg(current_seg, current_state)

        # Mise à jour du Bloc Program
        k = 0
        while rs.GetUserText(prog_id, "Crv_{}".format(k)):
            rs.SetUserText(prog_id, "Crv_{}".format(k), "")
            k += 1
        for i, u in enumerate(new_crv_uuids):
            rs.SetUserText(prog_id, "Crv_{}".format(i), u)
        
        stats["crv_out"] = len(new_crv_uuids)

        # --- Étape 7 : Debug ---
        print(" - Poses finales : {}".format(stats["pose_out"]))
        print(" - Courbes : {} -> {}".format(stats["crv_in"], stats["crv_out"]))

    rs.CurrentLayer(target_programs[0] if target_programs else None)
    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée.")

if __name__ == "__main__":
    rebuild_trajectories()

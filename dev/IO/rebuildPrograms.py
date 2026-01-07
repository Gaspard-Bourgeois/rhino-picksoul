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

def rebuild_trajectories():
    print("\n=== DEMARRAGE REBUILD TRAJECTOIRES ===")
    
    # --- Étape 1 : Choix des programmes ---
    selected = rs.SelectedObjects()
    target_programs = []
    
    all_instances = rs.ObjectsByType(4096) or []
    all_progs = [obj for obj in all_instances if rs.GetUserText(obj, "type") == "program"]
    print("Programmes 'type=program' detectes dans le document: {}".format(len(all_progs)))

    if not selected:
        if not all_progs:
            print("ERREUR: Aucun programme trouve.")
            return
        choices = [rs.ObjectLayer(p) for p in all_progs]
        picked = rs.MultiListBox(choices, "Programmes a editer", "Rebuild JBI")
        if not picked: return
        target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
    else:
        print("Analyse de la selection utilisateur ({} objets)...".format(len(selected)))
        target_programs = get_program_from_selection(selected)
        if not target_programs:
            print("ERREUR: Aucun programme associe a la selection.")
            return

    rs.EnableRedraw(False)
    
    for prog_id in target_programs:
        prog_layer = rs.ObjectLayer(prog_id)
        print("\n>>> TRAITEMENT PROGRAMME: {}".format(prog_layer))
        
        stats = {"pose_in": 0, "pose_out": 0, "crv_in": 0, "crv_out": 0}

        # --- Étape 2 : Identification des courbes via UserStrings ---
        original_crv_uuids = []
        i = 0
        while True:
            # Attention: Utilisation stricte du formatage Crv_0000
            key = "Crv_{:04d}".format(i)
            u = rs.GetUserText(prog_id, key)
            if not u: break
            if rs.IsObject(u):
                original_crv_uuids.append(u)
            else:
                print("DEBUG: Courbe referencee {} introuvable (supprimee?).".format(u))
            i += 1
        
        stats["crv_in"] = len(original_crv_uuids)
        print("Courbes originales trouvees: {}".format(stats["crv_in"]))

        # Recherche de doublons (copies) de courbes
        all_curves = rs.ObjectsByType(4) or []
        curve_copies = []
        for c_id in all_curves:
            origin = rs.GetUserText(c_id, "uuid_origin")
            if origin in original_crv_uuids and str(c_id) != origin:
                # Si selection, on filtre les copies selectionnees
                if selected:
                    if str(c_id) in [str(s) for s in selected]:
                        curve_copies.append(c_id)
                else:
                    curve_copies.append(c_id)
        
        print("Copies de courbes detectees: {}".format(len(curve_copies)))

        insert_mode_crv = 1
        if curve_copies:
            res = rs.ListBox(["Avant", "Après"], "Position des copies de courbes", prog_layer)
            if res: insert_mode_crv = 0 if res == "Avant" else 1

        # --- Étape 3, 4, 5 : Ordonnancement Global des Poses ---
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

        print("Traitement de l'ordre des courbes (Total: {})...".format(len(ordered_curves)))

        for crv_id in ordered_curves:
            is_copy_crv = rs.GetUserText(crv_id, "uuid_origin") != str(crv_id)
            # Si c'est une copie, on cherche les infos sur la courbe parente (origin)
            ref_crv = rs.GetUserText(crv_id, "uuid_origin") if is_copy_crv else str(crv_id)
            
            p_idx = 0
            while True:
                orig_pose_uuid = rs.GetUserText(ref_crv, "UUID_{:04d}".format(p_idx))
                if not orig_pose_uuid: break
                
                # Trouver les copies de poses
                pose_copies = []
                for inst in all_instances:
                    if rs.BlockInstanceName(inst) == "Pose":
                        if rs.GetUserText(inst, "uuid_origin") == orig_pose_uuid and str(inst) != orig_pose_uuid:
                            if selected:
                                if str(inst) in [str(s) for s in selected]: pose_copies.append(inst)
                            else:
                                pose_copies.append(inst)

                if not is_copy_crv:
                    global_pose_list.append(orig_pose_uuid)
                    global_pose_list.extend(pose_copies)
                else:
                    # Étape 4 : Generation poses sur sommets polyline
                    pts = rs.PolylineVertices(crv_id)
                    if pts and p_idx < len(pts):
                        new_p = rs.CopyObject(orig_pose_uuid)
                        trans = pts[p_idx] - rs.BlockInstanceInsertPoint(orig_pose_uuid)
                        rs.MoveObject(new_p, trans)
                        global_pose_list.append(new_p)
                p_idx += 1

        print("Sequence de poses generee. Nombre total: {}".format(len(global_pose_list)))

        # --- Étape 6 : Nettoyage et Renommage ---
        final_poses_clean = []
        for idx, p_id in enumerate(global_pose_list):
            if not rs.IsObject(p_id):
                print("error with uuid {}".format(p_id))
                continue
            
            rs.ObjectName(p_id, "{:04d}".format(idx))
            rs.SetUserText(p_id, "uuid_origin", str(p_id))
            
            final_poses_clean.append({
                'idx' : idx,
                'uuid': str(p_id),
                'state': rs.GetUserText(p_id, "State") or "ARCOF",
                'pos': rs.BlockInstanceInsertPoint(p_id)
            })
        
        stats["pose_out"] = len(final_poses_clean)

        # Suppression courbes obsolete
        rs.DeleteObjects(original_crv_uuids)
        if curve_copies: rs.DeleteObjects(curve_copies)

        # --- Étape 6 (bis) : Reconstruction des Courbes ---
        traj_lyr_name = prog_layer + "::trajs_arcon_arcof"
        if not rs.IsLayer(traj_lyr_name): rs.AddLayer(traj_lyr_name)
        rs.CurrentLayer(traj_lyr_name)

        new_crv_uuids = []
        if len(final_poses_clean) > 1:
            # --- Logique de segmentation ---
            current_seg_data = [final_poses_clean[0]]
            # On initialise l'etat du premier segment (0 vers 1)
            # Rappel: Segment est ARCON si la pose d'arrivee est ARCON
            current_state = (final_poses_clean[1]['state'] == "ARCON")

            for i in range(1, len(final_poses_clean)):
                p_this = final_poses_clean[i]
                
                # Etat du segment entrant vers p_this
                this_state = (p_this['state'] == "ARCON")
                
                if this_state != current_state:
                    # On ferme le segment precedent
                    if len(current_seg_data) >= 2:
                        nc = rs.AddPolyline([d['pos'] for d in current_seg_data])
                        if nc:
                            lbl = "ARCON" if current_state else "ARCOF"
                            rs.ObjectName(nc, "{}_{}-{}".format(lbl, current_seg_data[0]['idx'], current_seg_data[-1]['idx']))
                            rs.ObjectColor(nc, (255,0,0) if current_state else (150,150,150))
                            rs.SetUserText(nc, "uuid_origin", str(nc))
                            for j, d in enumerate(current_seg_data):
                                rs.SetUserText(nc, "Pt_{:04d}".format(j), rs.ObjectName(d['uuid']))
                                rs.SetUserText(nc, "UUID_{:04d}".format(j), d['uuid'])
                            new_crv_uuids.append(str(nc))
                    
                    # On commence le nouveau avec le point de transition
                    current_seg_data = [final_poses_clean[i-1], p_this]
                    current_state = this_state
                else:
                    current_seg_data.append(p_this)

            # Fermeture du dernier segment
            if len(current_seg_data) >= 2:
                nc = rs.AddPolyline([d['pos'] for d in current_seg_data])
                if nc:
                    lbl = "ARCON" if current_state else "ARCOF"
                    rs.ObjectColor(nc, (255,0,0) if current_state else (150,150,150))
                    rs.SetUserText(nc, "uuid_origin", str(nc))
                    for j, d in enumerate(current_seg_data):
                        rs.SetUserText(nc, "Pt_{:04d}".format(j), rs.ObjectName(d['uuid']))
                        rs.SetUserText(nc, "UUID_{:04d}".format(j), d['uuid'])
                    new_crv_uuids.append(str(nc))

        # --- Étape finale : Mise a jour des liens du Bloc Program ---
        # 1. Effacement propre (on cherche tous les Crv_*)
        all_keys = rs.GetUserText(prog_id)
        if all_keys:
            for k in all_keys:
                if k.startswith("Crv_"): rs.SetUserText(prog_id, k, "")

        # 2. Ecriture des nouveaux
        for i, u in enumerate(new_crv_uuids):
            rs.SetUserText(prog_id, "Crv_{:04d}".format(i), u)
        
        stats["crv_out"] = len(new_crv_uuids)
        print("DEBUG: {} nouvelles courbes creees.".format(stats["crv_out"]))

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminee.\nConsultez la console (F2) pour le detail.")

if __name__ == "__main__":
    rebuild_trajectories()

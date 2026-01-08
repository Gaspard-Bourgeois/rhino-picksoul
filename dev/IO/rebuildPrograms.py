# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

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
        # On ne prend que les instances qui ne sont PAS l'original
        if str(inst) != origin_uuid:
            # On vérifie si l'origine correspond
            if rs.GetUserText(inst, "uuid_origin") == origin_uuid:
                # Filtrage par sélection si actif
                if selected_ids:
                    if str(inst) in selected_ids:
                        copies.append(inst)
                else:
                    copies.append(inst)
    return copies

def rebuild_trajectories():
    print("\n=== DEMARRAGE REBUILD TRAJECTOIRES CORRIGE ===")
    
    # --- Étape 1 : Choix des programmes ---
    selected = rs.SelectedObjects()
    selected_ids_str = [str(s) for s in selected] if selected else []
    
    all_instances = rs.ObjectsByType(4096) or []
    all_progs = [obj for obj in all_instances if rs.GetUserText(obj, "type") == "program"]
    
    # Optimisation : pré-filtrer les instances de type "Pose" pour éviter de scanner tout le doc à chaque boucle
    all_poses_in_doc = [p for p in all_instances if rs.BlockInstanceName(p) == "Pose"]

    target_programs = []
    if not selected:
        if not all_progs:
            print("ERREUR: Aucun programme trouve.")
            return
        choices = [rs.ObjectLayer(p) for p in all_progs]
        picked = rs.MultiListBox(choices, "Programmes a editer", "Rebuild JBI")
        if not picked: return
        target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
    else:
        target_programs = get_program_from_selection(selected)
        if not target_programs:
            # Fallback : si on a sélectionné des objets mais pas le programme directement
            # On essaye de trouver le programme via le layer de la sélection
            print("Tentative de detection par calque...")
            choices = [rs.ObjectLayer(p) for p in all_progs]
            picked = rs.MultiListBox(choices, "Programmes a editer (Selection ambiguë)", "Rebuild JBI")
            if picked:
                target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
            else:
                return

    rs.EnableRedraw(False)
    
    for prog_id in target_programs:
        prog_layer = rs.ObjectLayer(prog_id)
        print("\n>>> TRAITEMENT PROGRAMME: {}".format(prog_layer))
        
        # Stats Debug
        stats = {
            "pose_before": len(rs.ObjectsByLayer(prog_layer) or []), # Approx
            "crv_arcon_before": 0, "crv_arcof_before": 0,
            "crv_arcon_after": 0, "crv_arcof_after": 0
        }

        # --- Étape 2 : Identification des courbes via UserStrings ---
        original_crv_uuids = []
        i = 0
        while True:
            # Format import original : Crv_0, Crv_1... (pas de padding 0000 dans import_jbi_final)
            key = "Crv_{}".format(i) 
            u = rs.GetUserText(prog_id, key)
            if not u: break
            if rs.IsObject(u):
                original_crv_uuids.append(u)
                # Stats
                if "ARCON" in rs.ObjectName(u): stats["crv_arcon_before"] += 1
                else: stats["crv_arcof_before"] += 1
            i += 1
        
        print("Courbes originales trouvees: {}".format(len(original_crv_uuids)))

        # Recherche de doublons (copies) de courbes
        all_curves = rs.ObjectsByType(4) or []
        curve_copies = []
        
        # On ne traite que les courbes qui sont des doublons d'une originale connue
        for c_id in all_curves:
            origin = rs.GetUserText(c_id, "uuid_origin")
            if origin in original_crv_uuids and str(c_id) != origin:
                if selected:
                    if str(c_id) in selected_ids_str: curve_copies.append(c_id)
                else:
                    curve_copies.append(c_id)
        
        print("Copies de courbes a traiter: {}".format(len(curve_copies)))

        insert_mode_crv = "After"
        if curve_copies:
            res = rs.ListBox(["Avant", "Après"], "Position des COPIES DE COURBES ?", "Ordre Courbes")
            if res: insert_mode_crv = res

        # --- Ordonnancement des courbes (Originales + Copies) ---
        ordered_curve_list = []
        
        for o_crv in original_crv_uuids:
            # Trouver les copies liées à CETTE courbe originale
            relevant_copies = [c for c in curve_copies if rs.GetUserText(c, "uuid_origin") == o_crv]
            
            if insert_mode_crv == "Avant":
                ordered_curve_list.extend(relevant_copies)
                ordered_curve_list.append(o_crv)
            else:
                ordered_curve_list.append(o_crv)
                ordered_curve_list.extend(relevant_copies)

        # --- Étape 3, 4, 5 : Construction de la liste PLATE des poses ---
        final_pose_objects = [] # Liste ordonnée des UUIDs de poses (existantes ou nouvelles)
        
        # On demande une seule fois pour les poses pour ne pas spammer, 
        # ou on peut demander à chaque fois qu'on trouve des copies. 
        # Pour l'ergonomie, on demande une fois globalement si des copies de poses existent.
        pose_insert_mode = "After" 
        # Petit check rapide s'il y a des copies de poses potentielles pour demander à l'utilisateur
        has_pose_copies = False
        for p in all_poses_in_doc:
            p_origin = rs.GetUserText(p, "uuid_origin")
            if p_origin and p_origin != str(p):
                 has_pose_copies = True
                 break
        
        if has_pose_copies:
             res_p = rs.ListBox(["Avant", "Après"], "Position des COPIES DE POSES ?", "Ordre Poses")
             if res_p: pose_insert_mode = res_p

        for crv_id in ordered_curve_list:
            is_copy_crv = (rs.GetUserText(crv_id, "uuid_origin") != str(crv_id))
            ref_crv = rs.GetUserText(crv_id, "uuid_origin") if is_copy_crv else str(crv_id)
            
            # Récupérer les ID de poses stockés dans la courbe ORIGINALE
            # Le script d'import utilise Pt_X pour l'index et UUID_X pour l'ID
            poses_in_curve = []
            p_idx = 0
            while True:
                # Format import: UUID_0, UUID_1...
                p_uuid = rs.GetUserText(ref_crv, "UUID_{}".format(p_idx))
                if not p_uuid: break
                poses_in_curve.append(p_uuid)
                p_idx += 1
            
            if not is_copy_crv:
                # CAS 1 : Courbe Originale -> On garde les poses originales + insertion des copies de poses
                for p_uuid in poses_in_curve:
                    # Trouver les copies manuelles de CETTE pose
                    copies_of_pose = get_pose_copies(p_uuid, all_poses_in_doc, selected_ids_str)
                    
                    if pose_insert_mode == "Avant":
                        final_pose_objects.extend(copies_of_pose)
                        final_pose_objects.append(p_uuid)
                    else:
                        final_pose_objects.append(p_uuid)
                        final_pose_objects.extend(copies_of_pose)
            
            else:
                # CAS 2 : Courbe Copiée (Étape 4) -> Création de NOUVELLES poses sur la géométrie
                # On doit créer des clones des poses de référence aux nouveaux emplacements
                pts = rs.PolylineVertices(crv_id)
                # Note: Une polyligne fermée a pt[0] == pt[-1], mais ici trajectoire robot souvent ouverte.
                # Si le nombre de points diffère du nombre de poses stockées, on s'arrête au min.
                count = min(len(pts), len(poses_in_curve))
                
                for k in range(count):
                    orig_pose_id = poses_in_curve[k]
                    target_pt = pts[k]
                    
                    if rs.IsObject(orig_pose_id):
                        # Cloner la pose originale
                        new_pose = rs.CopyObject(orig_pose_id)
                        # Déplacer au point de la polyligne copiée
                        # On calcule le vecteur entre l'origine de la pose source et le point cible
                        curr_pt = rs.BlockInstanceInsertPoint(new_pose)
                        trans = target_pt - curr_pt
                        rs.MoveObject(new_pose, trans)
                        
                        # Cette nouvelle pose fait partie de la séquence finale
                        final_pose_objects.append(new_pose)

        # --- Étape 6 : Mise à jour des UserStrings et Renommage ---
        pose_data_list = [] # Liste de dicts pour la reconstruction des courbes
        
        for idx, p_id in enumerate(final_pose_objects):
            if not rs.IsObject(p_id): continue
            
            # Renommage séquentiel
            rs.ObjectName(p_id, str(idx))
            
            # Mise à jour uuid_origin (une fois validé, l'objet devient sa propre origine)
            rs.SetUserText(p_id, "uuid_origin", str(p_id))
            
            state = rs.GetUserText(p_id, "State")
            if not state: state = "ARCOF" # Valeur par defaut securite
            
            pose_data_list.append({
                'idx': str(idx),
                'uuid': str(p_id),
                'state': state,
                'pos': rs.BlockInstanceInsertPoint(p_id)
            })

        print("Nombre total de poses après rebuild: {}".format(len(pose_data_list)))

        # Suppression des anciennes courbes (Originales + Copies utilisées)
        rs.DeleteObjects(original_crv_uuids)
        if curve_copies: rs.DeleteObjects(curve_copies)

        # --- Reconstruction des Courbes (Étape 6 bis) ---
        # Logique: On trace des traits entre les poses.
        # Le style (Couleur/Nom) du trait dépend de l'état "ARCON" ou "ARCOF".
        
        # Nettoyage layer trajectoires
        traj_lyr_name = "trajs_arcon_arcof"
        # On s'assure d'être dans le sous-layer du programme ou celui défini globalement
        # Le script import crée "trajs_arcon_arcof" sous le dossier job.
        # Ici on va essayer de trouver le layer existant ou en créer un sous le parent du prog
        parent_lyr = rs.ParentLayer(prog_layer)
        full_traj_lyr = parent_lyr + "::" + traj_lyr_name if parent_lyr else traj_lyr_name
        
        if not rs.IsLayer(full_traj_lyr): rs.AddLayer(traj_lyr_name, parent=parent_lyr)
        rs.CurrentLayer(full_traj_lyr)

        new_crv_uuids = []

        if len(pose_data_list) > 1:
            
            def create_segment_curve(segment_poses, is_arcon):
                if len(segment_poses) < 2: return
                
                # Création Polyligne
                pts = [d['pos'] for d in segment_poses]
                nc = rs.AddPolyline(pts)
                
                state_str = "ARCON" if is_arcon else "ARCOF"
                
                # Nommage : NOM_StartIdx-EndIdx
                name = "{} {}-{}".format(state_str, segment_poses[0]['idx'], segment_poses[-1]['idx'])
                rs.ObjectName(nc, name)
                
                # Couleur
                color = (255, 0, 0) if is_arcon else (150, 150, 150)
                rs.ObjectColor(nc, color)
                
                # UserStrings
                rs.SetUserText(nc, "uuid_origin", str(nc))
                for k, d in enumerate(segment_poses):
                    # Format compatible import: Pt_X, UUID_X
                    rs.SetUserText(nc, "Pt_{}".format(k), d['idx'])
                    rs.SetUserText(nc, "UUID_{}".format(k), d['uuid'])
                
                new_crv_uuids.append(str(nc))
                
                # Stats
                if is_arcon: stats["crv_arcon_after"] += 1
                else: stats["crv_arcof_after"] += 1

            # Boucle de segmentation
            current_seg = [pose_data_list[0]]
            # L'état du segment est déterminé par la cible. 
            # Si pose 1 est ARCON, le trait 0->1 est ARCON.
            current_state_arcon = (pose_data_list[0]['state'] == "ARCON") # Initiale, sera écrasée tout de suite
            if len(pose_data_list) > 1:
                 current_state_arcon = (pose_data_list[1]['state'] == "ARCON")

            for i in range(1, len(pose_data_list)):
                p_curr = pose_data_list[i]
                is_arcon = (p_curr['state'] == "ARCON")
                
                if is_arcon != current_state_arcon:
                    # Changement d'état : on ferme le segment précédent incluant le point courant (continuité)
                    # ATTENTION : En robotique, le changement d'état s'applique souvent au point.
                    # Ici on coupe : le segment précédent s'arrête au point i-1
                    # Mais pour continuité graphique, Rhino demande p[i-1] -> p[i].
                    
                    # Logique Import : 
                    # if inst_data[i]['arcon'] != last_s: build... seg = [prev, curr]
                    
                    # On finalise le segment en cours
                    create_segment_curve(current_seg, current_state_arcon)
                    
                    # On démarre le nouveau
                    current_seg = [pose_data_list[i-1], p_curr]
                    current_state_arcon = is_arcon
                else:
                    current_seg.append(p_curr)
            
            # Créer le dernier segment
            create_segment_curve(current_seg, current_state_arcon)

        # --- Mise à jour Bloc Programme ---
        # 1. Nettoyer anciennes clés Crv_
        all_keys = rs.GetUserText(prog_id)
        if all_keys:
            for k in all_keys:
                if k.startswith("Crv_"): rs.SetUserText(prog_id, k, "")
        
        # 2. Ecrire nouvelles clés
        for i, u in enumerate(new_crv_uuids):
            rs.SetUserText(prog_id, "Crv_{}".format(i), u)

        print("DEBUG STATS:")
        print("  Poses avant (approx): {}".format(stats["pose_before"]))
        print("  Poses apres: {}".format(len(pose_data_list)))
        print("  Courbes ARCON: {} -> {}".format(stats["crv_arcon_before"], stats["crv_arcon_after"]))
        print("  Courbes ARCOF: {} -> {}".format(stats["crv_arcof_before"], stats["crv_arcof_after"]))

    rs.EnableRedraw(True)
    rs.MessageBox("Rebuild Termine.\nVoir console (F2) pour details.")

if __name__ == "__main__":
    rebuild_trajectories()

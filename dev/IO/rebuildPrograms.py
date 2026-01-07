# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def get_program_from_selection(selected_ids):
    """Retrouve les programmes liés aux éléments sélectionnés (via calques)"""
    progs = []
    layers = set()
    for s_id in selected_ids:
        layers.add(rs.ObjectLayer(s_id))
        parent = rs.LayerParent(rs.ObjectLayer(s_id))
        if parent: layers.add(parent)
    
    all_progs = rs.ObjectsByUserText("type", "program")
    for p in all_progs:
        if rs.ObjectLayer(p) in layers:
            progs.append(p)
    return list(set(progs))

def get_all_programs():
    """Liste tous les programmes dans le document"""
    return rs.ObjectsByUserText("type", "program")

def ask_before_after(item_type):
    """Demande à l'utilisateur s'il veut insérer avant ou après"""
    res = rs.ListBox(["Avant l'original", "Après l'original"], 
                     "Où insérer les copies de {} ?".format(item_type), 
                     "Reconstruction Trajectoire")
    return 0 if res == "Avant l'original" else 1

def rebuild_trajectories():
    # --- Étape 1 : Choix des programmes ---
    selected = rs.SelectedObjects()
    target_programs = []
    
    if not selected:
        all_progs = get_all_programs()
        if not all_progs:
            print("Aucun programme trouvé.")
            return
        names = [rs.ObjectLayer(p) for p in all_progs]
        picked = rs.MultiListBox(names, "Sélectionnez les programmes à éditer", "Reconstruction")
        if not picked: return
        target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
    else:
        target_programs = get_program_from_selection(selected)
        if not target_programs:
            print("Aucun programme associé à la sélection.")
            return

    rs.EnableRedraw(False)
    
    for prog_id in target_programs:
        prog_name = rs.ObjectLayer(prog_id)
        print("--- Analyse du programme : {} ---".format(prog_name))
        
        # Stats Debug
        stats = {"pose_in": 0, "pose_out": 0, "crv_in": 0, "crv_out": 0}

        # --- Étape 2 : Analyse des courbes ---
        # On récupère les UUIDs stockés dans le bloc programme
        original_crv_uuids = []
        i = 0
        while True:
            u = rs.GetUserText(prog_id, "Crv_{}".format(i))
            if not u: break
            original_crv_uuids.append(u)
            i += 1
        
        stats["crv_in"] = len(original_crv_uuids)
        
        # Recherche de doublons de courbes dans le document
        # Un doublon a un uuid_origin qui pointe vers une courbe du programme mais possède un UUID différent
        all_doc_curves = rs.ObjectsByType(rs.filter.curve)
        curve_copies = []
        for c_id in all_doc_curves:
            origin = rs.GetUserText(c_id, "uuid_origin")
            if origin in original_crv_uuids and str(c_id) != origin:
                # Si l'utilisateur avait sélectionné des courbes, on filtre
                if selected:
                    if str(c_id) in [str(s) for s in selected]:
                        curve_copies.append(c_id)
                else:
                    curve_copies.append(c_id)

        # Choix utilisateur pour les courbes
        insert_mode_crv = 1
        if curve_copies:
            choice_crvs = rs.MultiListBox([str(c) for c in curve_copies], "Doublons de courbes trouvés. Lesquels intégrer ?", prog_name)
            if choice_crvs:
                insert_mode_crv = ask_before_after("courbes")
                curve_copies = [rg.ConnectableCurve.ObjectId.Parse(c) for c in choice_crvs]
            else:
                curve_copies = []

        # --- Étape 3 & 4 : Analyse des poses et création ---
        final_pose_list = [] # Liste de dictionnaires {'uuid':..., 'state':...}
        
        # On définit l'ordre de parcours des courbes (Originales + Copies)
        ordered_curves = []
        for o_crv in original_crv_uuids:
            if insert_mode_crv == 0: # Avant
                for copy in curve_copies:
                    if rs.GetUserText(copy, "uuid_origin") == o_crv: ordered_curves.append(copy)
                ordered_curves.append(o_crv)
            else: # Après
                ordered_curves.append(o_crv)
                for copy in curve_copies:
                    if rs.GetUserText(copy, "uuid_origin") == o_crv: ordered_curves.append(copy)

        for crv_id in ordered_curves:
            is_copy_crv = rs.GetUserText(crv_id, "uuid_origin") != str(crv_id)
            crv_poses = []
            
            # Récupération des poses référencées dans la courbe (originale ou modèle de la copie)
            ref_crv = rs.GetUserText(crv_id, "uuid_origin") if is_copy_crv else str(crv_id)
            
            p_idx = 0
            while True:
                pose_uuid = rs.GetUserText(ref_crv, "UUID_{}".format(p_idx))
                if not pose_uuid: break
                
                # Recherche de doublons de cette pose
                all_poses = rs.ObjectsByUserText("uuid_origin", pose_uuid)
                pose_copies = [p for p in all_poses if str(p) != pose_uuid]
                
                # Filtrage avec sélection initiale
                if selected:
                    pose_copies = [p for p in pose_copies if str(p) in [str(s) for s in selected]]

                # Ordonnancement des poses au sein de la courbe
                current_pose_group = []
                if not is_copy_crv:
                    # Logique d'insertion de doublons de points sur une courbe existante
                    insert_mode_pos = 1
                    if pose_copies:
                        # On pourrait demander ici, mais pour éviter 100 popups, on applique une règle globale
                        current_pose_group.append(pose_uuid)
                        current_pose_group.extend(pose_copies)
                    else:
                        current_pose_group.append(pose_uuid)
                else:
                    # Étape 4 : Pour une courbe copiée, on crée de nouvelles poses aux sommets
                    poly_pts = rs.PolylineVertices(crv_id)
                    if poly_pts and p_idx < len(poly_pts):
                        new_pose = rs.CopyObject(pose_uuid)
                        rs.MoveObject(new_pose, poly_pts[p_idx] - rs.BlockInstanceInsertPoint(pose_uuid))
                        current_pose_group.append(new_pose)

                for p_id in current_pose_group:
                    state = rs.GetUserText(p_id, "State")
                    crv_poses.append({'uuid': str(p_id), 'state': state, 'pos': rs.BlockInstanceInsertPoint(p_id)})
                
                p_idx += 1
            
            final_pose_list.extend(crv_poses)

        # Suppression des anciennes courbes
        rs.DeleteObjects(original_crv_uuids)
        if curve_copies: rs.DeleteObjects(curve_copies)

        # --- Étape 5 & 6 : Mise à jour UUID et Re-création ---
        # Nettoyage doublons éventuels de liste et mise à jour uuid_origin
        for item in final_pose_list:
            stats["pose_out"] += 1
            rs.SetUserText(item['uuid'], "uuid_origin", item['uuid'])

        # Création des nouvelles courbes (Logique ARCON/ARCOF)
        new_crv_uuids = []
        if len(final_pose_list) > 1:
            def build_new_crv(data):
                if len(data) < 2: return
                pts = [d['pos'] for d in data]
                new_c = rs.AddPolyline(pts)
                state = data[0]['state']
                pref = state
                rs.ObjectName(new_c, "{} Rebuilt".format(pref))
                rs.ObjectColor(new_c, (255,0,0) if state == "ARCON" else (150,150,150))
                rs.SetUserText(new_c, "uuid_origin", str(new_c))
                # Update des UserStrings de la courbe pour les points
                for i, d in enumerate(data):
                    rs.SetUserText(new_c, "Pt_{}".format(i), rs.ObjectName(d['uuid']))
                    rs.SetUserText(new_c, "UUID_{}".format(i), d['uuid'])
                new_crv_uuids.append(str(new_c))

            current_seg = [final_pose_list[0]]
            last_state = final_pose_list[0]['state']
            
            for i in range(1, len(final_pose_list)):
                if final_pose_list[i]['state'] != last_state:
                    build_new_crv(current_seg)
                    current_seg = [final_pose_list[i-1], final_pose_list[i]]
                    last_state = final_pose_list[i]['state']
                else:
                    current_seg.append(final_pose_list[i])
            build_new_crv(current_seg)

        # Mise à jour du bloc programme
        # On supprime les anciennes clés Crv_
        i = 0
        while rs.GetUserText(prog_id, "Crv_{}".format(i)):
            rs.SetUserText(prog_id, "Crv_{}".format(i), None)
            i += 1
        # On écrit les nouvelles
        for i, u in enumerate(new_crv_uuids):
            rs.SetUserText(prog_id, "Crv_{}".format(i), u)

        stats["crv_out"] = len(new_crv_uuids)

        # --- Étape 7 : Debug ---
        print("Rebuild terminé pour : {}".format(prog_name))
        print("- Poses : {} -> {}".format(stats["pose_in"], stats["pose_out"]))
        print("- Courbes : {} -> {}".format(stats["crv_in"], stats["crv_out"]))

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée avec succès")

if __name__ == "__main__":
    rebuild_trajectories()

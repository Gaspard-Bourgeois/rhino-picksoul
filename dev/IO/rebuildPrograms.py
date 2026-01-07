# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

def find_objects_by_user_text(key, value):
    """Alternative à ObjectsByUserText pour Rhino 7"""
    objs = rs.AllObjects()
    found = []
    for obj in objs:
        val = rs.GetUserText(obj, key)
        if val == value:
            found.append(obj)
    return found

def get_program_from_selection(selected_ids):
    """Retrouve les programmes liés aux éléments sélectionnés"""
    target_layers = set()
    for s_id in selected_ids:
        lyr = rs.ObjectLayer(s_id)
        target_layers.add(lyr)
        parent = rs.ParentLayer(lyr)
        if parent:
            target_layers.add(parent)
    
    # Trouver tous les blocs 'program'
    all_objs = rs.AllObjects()
    programs = []
    for obj in all_objs:
        if rs.IsBlockInstance(obj):
            if rs.GetUserText(obj, "type") == "program":
                if rs.ObjectLayer(obj) in target_layers:
                    programs.append(obj)
    return list(set(programs))

def rebuild_trajectories():
    # --- Étape 1 : Choix des programmes ---
    selected = rs.SelectedObjects()
    target_programs = []
    
    if not selected:
        all_progs = [obj for obj in rs.AllObjects() if rs.IsBlockInstance(obj) and rs.GetUserText(obj, "type") == "program"]
        if not all_progs:
            print("Aucun programme trouvé.")
            return
        
        choices = [rs.ObjectLayer(p) for p in all_progs]
        picked = rs.MultiListBox(choices, "Sélectionnez les programmes à éditer", "Rebuild JBI")
        if not picked: return
        target_programs = [p for p in all_progs if rs.ObjectLayer(p) in picked]
    else:
        target_programs = get_program_from_selection(selected)
        if not target_programs:
            print("Aucun programme trouvé associé à la sélection.")
            return

    rs.EnableRedraw(False)
    
    for prog_id in target_programs:
        prog_layer = rs.ObjectLayer(prog_id)
        print("--- Analyse du programme : {} ---".format(prog_layer))
        
        stats = {"pose_in": 0, "pose_out": 0, "crv_in": 0, "crv_out": 0}

        # --- Étape 2 : Doublons de courbes ---
        original_crv_uuids = []
        idx = 0
        while True:
            u = rs.GetUserText(prog_id, "Crv_{}".format(idx))
            if not u: break
            original_crv_uuids.append(u)
            idx += 1
        
        stats["crv_in"] = len(original_crv_uuids)

        # Recherche de copies de courbes
        all_curves = rs.ObjectsByType(rs.filter.curve)
        curve_copies = []
        for c_id in all_curves:
            origin = rs.GetUserText(c_id, "uuid_origin")
            if origin in original_crv_uuids and str(c_id) != origin:
                # Filtrer si l'utilisateur a sélectionné des copies précises
                if selected:
                    if str(c_id) in [str(s) for s in selected]:
                        curve_copies.append(c_id)
                else:
                    curve_copies.append(c_id)

        insert_mode_crv = 1 # Par défaut 'Après'
        if curve_copies:
            names = ["Copie de " + rs.ObjectName(c) if rs.ObjectName(c) else str(c) for c in curve_copies]
            choice_crvs = rs.MultiListBox(names, "Courbes copiées détectées. Lesquelles intégrer ?", prog_layer)
            if choice_crvs:
                res = rs.ListBox(["Avant l'original", "Après l'original"], "Position des copies", "Courbes")
                insert_mode_crv = 0 if res == "Avant l'original" else 1
                # On ne garde que les copies validées
                curve_copies = [curve_copies[i] for i, n in enumerate(names) if n in choice_crvs]
            else:
                curve_copies = []

        # --- Étape 3, 4 & 5 : Ordonnancement et reconstruction des poses ---
        final_pose_data = [] # Liste de dict {'uuid', 'state', 'pos'}
        
        # On construit l'ordre des courbes à traiter
        ordered_curves = []
        for o_crv in original_crv_uuids:
            relevant_copies = [c for c in curve_copies if rs.GetUserText(c, "uuid_origin") == o_crv]
            if insert_mode_crv == 0: # Avant
                ordered_curves.extend(relevant_copies)
                ordered_curves.append(o_crv)
            else: # Après
                ordered_curves.append(o_crv)
                ordered_curves.extend(relevant_copies)

        for crv_id in ordered_curves:
            is_copy_crv = rs.GetUserText(crv_id, "uuid_origin") != str(crv_id)
            ref_crv = rs.GetUserText(crv_id, "uuid_origin") if is_copy_crv else str(crv_id)
            
            p_idx = 0
            while True:
                orig_pose_uuid = rs.GetUserText(ref_crv, "UUID_{}".format(p_idx))
                if not orig_pose_uuid: break
                
                # Recherche doublons de pose
                all_inst = rs.ObjectsByFilter(rs.filter.instance)
                pose_copies = []
                for inst in all_inst:
                    if rs.GetUserText(inst, "uuid_origin") == orig_pose_uuid and str(inst) != orig_pose_uuid:
                        if selected:
                            if str(inst) in [str(s) for s in selected]: pose_copies.append(inst)
                        else:
                            pose_copies.append(inst)

                current_pose_group = []
                if not is_copy_crv:
                    # Courbe originale : on gère les poses ajoutées manuellement sur le tracé
                    current_pose_group.append(orig_pose_uuid)
                    if pose_copies:
                        # On pourrait demander ici, mais on simplifie en ajoutant après l'originale
                        current_pose_group.extend(pose_copies)
                else:
                    # Étape 4 : Courbe copiée -> On génère de nouvelles poses aux sommets de la polyline
                    poly_pts = rs.PolylineVertices(crv_id)
                    if poly_pts and p_idx < len(poly_pts):
                        # Copie le bloc pose original et le déplace au sommet
                        new_pose = rs.CopyObject(orig_pose_uuid)
                        translation = poly_pts[p_idx] - rs.BlockInstanceInsertPoint(orig_pose_uuid)
                        rs.MoveObject(new_pose, translation)
                        current_pose_group.append(new_pose)

                for p_id in current_pose_group:
                    stats["pose_in"] += 1 if not is_copy_crv else 0
                    final_pose_data.append({
                        'uuid': str(p_id),
                        'state': rs.GetUserText(p_id, "State"),
                        'pos': rs.BlockInstanceInsertPoint(p_id)
                    })
                p_idx += 1

        # --- Étape 6 : Mise à jour des uuid_origin et nettoyage ---
        for item in final_pose_data:
            rs.SetUserText(item['uuid'], "uuid_origin", item['uuid'])
            stats["pose_out"] += 1

        # Suppression anciennes courbes
        rs.DeleteObjects(original_crv_uuids)
        if curve_copies: rs.DeleteObjects(curve_copies)

        # --- Étape 6 (bis) : Création des nouvelles courbes ---
        new_crv_uuids = []
        if len(final_pose_data) > 1:
            def create_segment(data):
                if len(data) < 2: return
                pts = [d['pos'] for d in data]
                nc = rs.AddPolyline(pts)
                state = data[0]['state']
                rs.ObjectName(nc, "{} Rebuilt".format(state))
                rs.ObjectColor(nc, (255,0,0) if state == "ARCON" else (150,150,150))
                rs.SetUserText(nc, "uuid_origin", str(nc))
                for i, d in enumerate(data):
                    # On récupère le nom de l'instance pour Pt_X (index original)
                    name_idx = rs.ObjectName(d['uuid'])
                    rs.SetUserText(nc, "Pt_{}".format(i), name_idx if name_idx else str(i))
                    rs.SetUserText(nc, "UUID_{}".format(i), d['uuid'])
                new_crv_uuids.append(str(nc))

            seg = [final_pose_data[0]]
            last_s = final_pose_data[0]['state']
            for i in range(1, len(final_pose_data)):
                if final_pose_data[i]['state'] != last_s:
                    create_segment(seg)
                    seg = [final_pose_data[i-1], final_pose_data[i]]
                    last_s = final_pose_data[i]['state']
                else:
                    seg.append(final_pose_data[i])
            create_segment(seg)

        # Mise à jour du Bloc Program
        # Nettoyage des anciennes clés Crv_
        k = 0
        while rs.GetUserText(prog_id, "Crv_{}".format(k)):
            rs.SetUserText(prog_id, "Crv_{}".format(k), "")
            k += 1
        # Inscription des nouvelles
        for i, u in enumerate(new_crv_uuids):
            rs.SetUserText(prog_id, "Crv_{}".format(i), u)
        
        stats["crv_out"] = len(new_crv_uuids)

        # --- Étape 7 : Debug ---
        print("Rebuild terminé pour : {}".format(prog_layer))
        print(" - Poses traitées : {}".format(stats["pose_out"]))
        print(" - Courbes : {} -> {}".format(stats["crv_in"], stats["crv_out"]))

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée.")

if __name__ == "__main__":
    rebuild_trajectories()

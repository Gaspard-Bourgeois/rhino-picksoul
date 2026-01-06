import rhinoscriptsyntax as rs

def find_program_in_hierarchy(obj):
    """Remonte les calques pour trouver le bloc program parent."""
    curr_lyr = rs.ObjectLayer(obj)
    while curr_lyr:
        objs = rs.ObjectsByLayer(curr_lyr)
        for o in objs:
            if rs.IsBlockInstance(o) and rs.GetUserText(o, "type") == "program":
                return o
        curr_lyr = rs.ParentLayer(curr_lyr)
    return None

def analyze_and_rebuild_final():
    selection = rs.GetObjects("Sélectionnez un élément du programme", preselect=True)
    if not selection:
        rs.MessageBox("Aucune sélection effectuée.", 64)
        return

    progs = []
    for s in selection:
        p = find_program_in_hierarchy(s)
        if p and p not in progs: progs.append(p)

    if not progs:
        rs.MessageBox("Aucun bloc de type 'program' trouvé dans la hiérarchie.", 16)
        return

    rs.EnableRedraw(False)
    
    # Mapper toutes les courbes par leur UUID d'origine
    # Structure : { 'uuid_origine': [objet_rhino_1, objet_rhino_2, ...] }
    all_objs = rs.AllObjects()
    curve_map = {}
    obj_data_map = {} # Pour retrouver les infos des poses originales rapidement

    for o in all_objs:
        # Stocker les courbes
        u_origin = rs.GetUserText(o, "uuid_origin")
        if u_origin and rs.IsCurve(o):
            if u_origin not in curve_map: curve_map[u_origin] = []
            curve_map[u_origin].append(o)
        
        # Stocker les données des Poses originales pour référence
        if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose":
             # On utilise l'ID réel de l'objet comme clé car UUID_x dans la courbe pointe vers l'ID importé
             obj_data_map[str(o)] = o 
             # Mais si on a déjà fait un rebuild, on peut perdre la trace, 
             # on se fie aux UserText stockés dans les courbes lors de l'import (UUID_0, UUID_1...)

    copy_mode_choice = None # Pour ne pas redemander à chaque fois si l'utilisateur veut appliquer à tout

    for prog in progs:
        main_lyr = rs.ObjectLayer(prog)
        traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)

        # Récupérer l'ordre original du programme
        keys = sorted([k for k in rs.GetUserText(prog) if k.startswith("Crv_")], key=lambda x: int(x.split("_")[1]))
        original_seq_uuids = [rs.GetUserText(prog, k) for k in keys]

        final_curve_sequence = []

        # 1. Résolution de l'ordre (Gestion des Copies)
        for u_orig in original_seq_uuids:
            if u_orig not in curve_map: continue
            
            candidates = curve_map[u_orig]
            
            if len(candidates) == 1:
                final_curve_sequence.append(candidates[0])
            else:
                # C'est ici qu'on gère les copies
                # Identifier l'original (celui dont l'ID Rhino == uuid_origin)
                original_crv = None
                copies = []
                for c in candidates:
                    if str(c) == u_orig: original_crv = c
                    else: copies.append(c)
                
                # Si l'original a été supprimé, on prend tout comme des copies
                current_batch = []
                if original_crv: current_batch.append(original_crv)
                current_batch.extend(copies)

                if len(copies) > 0:
                    rs.EnableRedraw(True)
                    rs.SelectObjects(current_batch)
                    msg = "Des copies ont été détectées pour le segment {}.\nOù placer les copies par rapport à l'original ?".format(u_orig)
                    opt = rs.GetString(msg, "Apres", ["Avant", "Apres"])
                    rs.UnselectAllObjects()
                    rs.EnableRedraw(False)
                    
                    if opt and opt.upper() == "AVANT":
                        # Copies d'abord, Original ensuite
                        final_curve_sequence.extend(copies)
                        if original_crv: final_curve_sequence.append(original_crv)
                    else:
                        # Original d'abord, Copies ensuite (Défaut)
                        if original_crv: final_curve_sequence.append(original_crv)
                        final_curve_sequence.extend(copies)
                else:
                    final_curve_sequence.extend(current_batch)

        # 2. Nettoyage de l'existant (Poses et anciennes courbes non sélectionnées)
        # On supprime toutes les Poses existantes pour les recréer proprement aux sommets
        to_del = []
        layer_objs = rs.ObjectsByLayer(main_lyr)
        for o in layer_objs:
            if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) in ["Pose", "Start", "End"]:
                to_del.append(o)
        
        # On supprime les courbes dans traj_lyr car on va les recréer
        if rs.IsLayer(traj_lyr):
            to_del.extend(rs.ObjectsByLayer(traj_lyr))
            
        # Attention : ne pas supprimer les courbes qu'on est en train d'utiliser (final_curve_sequence)
        # Comme final_curve_sequence contient les objets GUID, on doit faire attention si elles sont dans traj_lyr
        # Astuce : On recrée de nouvelles courbes, donc on peut supprimer les anciennes APRES avoir lu leurs sommets
        
        # Extraction des données géométriques AVANT suppression
        construction_data = []
        for crv in final_curve_sequence:
            verts = rs.PolylineVertices(crv)
            if not verts: continue
            
            # Récupération Méta-données depuis la courbe
            # La courbe contient UUID_0, UUID_1 etc qui pointent vers les poses originales
            # Si c'est une copie, elle a les mêmes UUID_x, donc on copie les propriétés du mouvement original
            
            pts_data = []
            for i, pt in enumerate(verts):
                # On cherche la référence de la pose originale pour ce sommet
                ref_pose_uuid = rs.GetUserText(crv, "UUID_{}".format(i))
                meta = {}
                
                # On essaie de retrouver les infos stockées sur la courbe si possible, 
                # sinon on devrait aller voir l'objet pose original (mais il va être supprimé ou n'existe plus)
                # Le script d'import ne stockait pas les params V/PL sur la courbe, mais sur la Pose.
                # Il faut donc retrouver la pose originale via ref_pose_uuid.
                
                # Problème : Si on a importé, ref_pose_uuid est l'ID de la pose.
                # On cherche l'objet Pose dans la scène qui a cet ID (si pas encore supprimé) ou via une map
                
                # Comme on n'a pas encore supprimé 'to_del', on peut chercher dedans
                found_ref = None
                if ref_pose_uuid and rs.IsObject(ref_pose_uuid):
                    found_ref = ref_pose_uuid
                
                if found_ref:
                    # Copie des attributs
                    for key in ["ID_C", "BC", "Type", "V", "VJ", "PL", "Comment", "State"]:
                        val = rs.GetUserText(found_ref, key)
                        if val: meta[key] = val
                
                pts_data.append({'pos': pt, 'meta': meta})
            
            # Détermination état global courbe (pour la couleur)
            is_arcon = "ARCON" in (rs.ObjectName(crv) or "")
            if not is_arcon:
                # Fallback : vérifier le premier point
                if pts_data and 'State' in pts_data[0]['meta'] and pts_data[0]['meta']['State'] == "ARCON":
                    is_arcon = True

            construction_data.append({'points': pts_data, 'arcon': is_arcon, 'origin_uuid': rs.GetUserText(crv, "uuid_origin")})

        # Suppression maintenant que les données sont en mémoire
        safe_del = [o for o in to_del if o not in final_curve_sequence] # On garde les courbes guides pour l'instant
        rs.DeleteObjects(safe_del)
        # On peut aussi supprimer les courbes guides si on veut, ou les laisser cachées. 
        # Le script standard recrée les trajs, donc on supprime souvent les anciennes.
        rs.DeleteObjects(final_curve_sequence) 

        # 3. Reconstruction
        rs.CurrentLayer(main_lyr)
        
        global_idx = 0
        all_new_poses_ids = []
        all_new_poses_pts = []
        all_states = []

        # Aplatir la structure pour recréer une sequence continue
        # Attention aux doublons de points aux jonctions de courbes
        
        for i_crv, segment in enumerate(construction_data):
            seg_pts = segment['points']
            for i_pt, p_data in enumerate(seg_pts):
                # Si ce n'est pas la toute première courbe, le premier point est souvent le même que le dernier de la précédente
                # Dans un JBI les poses sont uniques. Si on découpe une ligne, on ajoute des poses.
                # Logique : On crée une Pose pour chaque sommet.
                
                # Filtre de proximité simple pour éviter doublons exacts aux jonctions
                if i_pt == 0 and i_crv > 0:
                    dist = rs.Distance(p_data['pos'], all_new_poses_pts[-1])
                    if dist < 0.001: continue # C'est le même point (jonction)

                nid = rs.InsertBlock("Pose", p_data['pos'])
                rs.ObjectName(nid, str(global_idx))
                rs.SetUserText(nid, "uuid_origin", str(nid)) # Nouvelle identité
                
                # Application Méta-données
                meta = p_data['meta']
                for k, v in meta.items(): rs.SetUserText(nid, k, v)
                
                # Mise à jour de l'état si présent dans les meta, sinon hérité du segment
                state = meta.get('State', "ARCON" if segment['arcon'] else "ARCOF")
                rs.SetUserText(nid, "State", state)

                all_new_poses_ids.append(str(nid))
                all_new_poses_pts.append(p_data['pos'])
                all_states.append(state)
                global_idx += 1

        # Start / End
        if all_new_poses_pts:
            rs.InsertBlock("Start", all_new_poses_pts[0])
            rs.InsertBlock("End", all_new_poses_pts[-1])

        # 4. Recréation des Courbes (Trajectoires)
        rs.CurrentLayer(traj_lyr)
        
        if len(all_new_poses_pts) > 1:
            curr_pts = [all_new_poses_pts[0]]
            curr_uids = [all_new_poses_ids[0]]
            curr_state = all_states[0]
            start_idx = 0

            def make_poly(pts, uids, st, si):
                if len(pts) < 2: return
                pl = rs.AddPolyline(pts)
                n_pref = "ARCON" if st == "ARCON" else "ARCOF"
                rs.ObjectName(pl, "{} {}-{}".format(n_pref, si, si+len(pts)-1))
                rs.ObjectColor(pl, (255,0,0) if st == "ARCON" else (150,150,150))
                # On remet uuid_origin vers lui-même car c'est une reconstruction neuve
                rs.SetUserText(pl, "uuid_origin", str(pl))
                for j, u in enumerate(uids):
                    rs.SetUserText(pl, "UUID_{}".format(j), u)
                    rs.SetUserText(pl, "Pt_{}".format(j), str(si+j))

            for i in range(1, len(all_new_poses_pts)):
                s = all_states[i]
                # Si changement d'état (ARCON vs ARCOF), on coupe la courbe
                if s != curr_state:
                    # On finit la courbe précédente au point actuel
                    curr_pts.append(all_new_poses_pts[i])
                    curr_uids.append(all_new_poses_ids[i])
                    make_poly(curr_pts, curr_uids, curr_state, start_idx)
                    
                    # Nouvelle courbe commence ici
                    curr_pts = [all_new_poses_pts[i-1], all_new_poses_pts[i]] # continuité visuelle ? 
                    # Non, logiquement un segment change d'état au point. 
                    # Redémarrons propre :
                    curr_pts = [all_new_poses_pts[i]]
                    curr_uids = [all_new_poses_ids[i]]
                    curr_state = s
                    start_idx = i
                else:
                    curr_pts.append(all_new_poses_pts[i])
                    curr_uids.append(all_new_poses_ids[i])
            
            # Finir la dernière
            make_poly(curr_pts, curr_uids, curr_state, start_idx)

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée avec succès.")

if __name__ == "__main__":
    analyze_and_rebuild_final()

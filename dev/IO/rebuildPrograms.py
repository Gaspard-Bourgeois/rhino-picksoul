import rhinoscriptsyntax as rs

def find_program_block(objs):
    """Trouve le bloc programme parent."""
    # On cherche d'abord dans la sélection
    for o in objs:
        if rs.IsBlockInstance(o) and rs.GetUserText(o, "type") == "program":
            return o
    
    # Sinon on remonte la hiérarchie du premier objet
    if objs:
        curr = rs.ObjectLayer(objs[0])
        while curr:
            l_objs = rs.ObjectsByLayer(curr)
            for o in l_objs:
                if rs.IsBlockInstance(o) and rs.GetUserText(o, "type") == "program":
                    return o
            curr = rs.ParentLayer(curr)
    return None

def get_sorted_instances(original_uuids, object_map, selection_ids, prompt_label):
    """
    Trie les objets selon l'ordre original.
    Gère les copies : demande à l'utilisateur s'il faut insérer Avant ou Après.
    Ne traite que les copies sélectionnées ou toutes si aucune sélection.
    """
    final_sequence = []
    
    # Demander l'ordre globalement pour ce type d'objet (Courbe ou Pose)
    # On ne demande que si on détecte au moins une copie à traiter
    copy_order_pref = None 
    
    for u_orig in original_uuids:
        if u_orig not in object_map: continue
        
        candidates = object_map[u_orig]
        
        # Filtrage : On garde l'original (ID == u_orig) ET les copies qui sont dans la sélection
        # Si selection_ids est vide (pas de sélection utilisateur), on prend tout.
        to_process = []
        original_obj = None
        
        for c in candidates:
            is_orig = (str(c) == u_orig)
            if is_orig: original_obj = c
            
            if not selection_ids or (str(c) in selection_ids) or is_orig:
                to_process.append(c)
        
        # Si on a plus d'un objet à traiter pour cet emplacement (donc des copies)
        if len(to_process) > 1:
            # Séparer original et copies
            copies = [x for x in to_process if x != original_obj]
            
            if copy_order_pref is None:
                # Premier conflit détecté, on pose la question
                msg = "Des copies de {} ont été détectées.\nOù placer les copies ?".format(prompt_label)
                copy_order_pref = rs.GetString(msg, "Apres", ["Avant", "Apres"])
                if not copy_order_pref: copy_order_pref = "Apres"
                copy_order_pref = copy_order_pref.upper()

            if copy_order_pref == "AVANT":
                final_sequence.extend(copies)
                if original_obj and original_obj in to_process: final_sequence.append(original_obj)
            else:
                if original_obj and original_obj in to_process: final_sequence.append(original_obj)
                final_sequence.extend(copies)
        else:
            final_sequence.extend(to_process)
            
    return final_sequence

def analyze_and_rebuild():
    sel = rs.GetObjects("Sélectionnez les éléments (Tout si vide)", preselect=True)
    sel_ids = [str(o) for o in sel] if sel else []
    
    # Si pas de sélection, on travaillera sur tous les objets du calque du programme
    # Mais on a besoin de trouver le programme d'abord
    search_pool = sel if sel else rs.AllObjects()
    prog_block = find_program_block(search_pool)
    
    if not prog_block:
        rs.MessageBox("Bloc 'Program' introuvable.", 16)
        return

    main_lyr = rs.ObjectLayer(prog_block)
    traj_lyr = main_lyr + "::trajs_arcon_arcof"
    
    rs.EnableRedraw(False)

    # 1. Cartographie de tous les objets par uuid_origin
    all_objs = rs.AllObjects()
    obj_map = {}
    for o in all_objs:
        u = rs.GetUserText(o, "uuid_origin")
        if u:
            if u not in obj_map: obj_map[u] = []
            obj_map[u].append(o)

    # 2. Récupération de l'ordre original des COURBES
    keys = sorted([k for k in rs.GetUserText(prog_block) if k.startswith("Crv_")], key=lambda x: int(x.split("_")[1]))
    orig_curve_uuids = [rs.GetUserText(prog_block, k) for k in keys]

    # 3. Traitement des COURBES (Copies & Ordre)
    sorted_curves = get_sorted_instances(orig_curve_uuids, obj_map, sel_ids, "Courbes")

    # 4. Extraction des données pour reconstruire les Poses
    # On parcourt les courbes ordonnées pour extraire les sommets et les métadonnées
    poses_to_create = [] # Liste de dicts
    
    # Pour récupérer les infos, on doit parfois regarder les Poses originales si elles existent encore
    # ou se fier aux UserText stockés dans les courbes
    
    for crv in sorted_curves:
        verts = rs.PolylineVertices(crv)
        if not verts: continue
        
        # Récupération état global pour fallback
        crv_name = rs.ObjectName(crv) or ""
        default_state = "ARCON" if "ARCON" in crv_name else "ARCOF"

        for i, pt in enumerate(verts):
            # Clés UserText sur la courbe : UUID_0, UUID_1...
            ref_uuid = rs.GetUserText(crv, "UUID_{}".format(i))
            
            meta = {}
            state = default_state
            
            # Essai de récupération des infos depuis la Pose originale (si elle existe)
            # ref_uuid est l'ID de la pose
            found_ref = None
            if ref_uuid and ref_uuid in obj_map:
                # On prend le premier objet qui correspond à cet UUID d'origine
                # (Même si c'est une copie, les infos sont censées être les mêmes)
                found_ref = obj_map[ref_uuid][0] 
            elif ref_uuid and rs.IsObject(ref_uuid):
                found_ref = ref_uuid
            
            if found_ref:
                for k in ["ID_C", "BC", "Type", "V", "VJ", "PL", "Comment", "State"]:
                    val = rs.GetUserText(found_ref, k)
                    if val: meta[k] = val
                
                if "State" in meta: state = meta["State"]
            
            poses_to_create.append({'pos': pt, 'meta': meta, 'state': state})

    # Note: On pourrait aussi traiter les Poses isolées (hors courbes) ici si nécessaire,
    # en utilisant une logique similaire avec get_sorted_instances sur des IDs de poses.
    # Pour ce script, on assume que les Courbes pilotent la structure principale.

    # 5. Nettoyage
    # On supprime Poses, Start, End et Courbes existantes dans les calques cibles
    to_del = []
    for o in rs.ObjectsByLayer(main_lyr):
        if rs.IsBlockInstance(o):
            bn = rs.BlockInstanceName(o)
            if bn in ["Pose", "Start", "End"]: to_del.append(o)
    
    if rs.IsLayer(traj_lyr):
        to_del.extend(rs.ObjectsByLayer(traj_lyr))
        
    # Attention : ne pas supprimer les objets qu'on vient de lire si rs.ObjectsByLayer les inclut
    # Comme on a déjà extrait 'poses_to_create', on peut supprimer.
    rs.DeleteObjects(to_del)

    # 6. Reconstruction Poses
    rs.CurrentLayer(main_lyr)
    new_pose_ids = []
    new_pose_pts = []
    new_pose_states = []
    
    idx_counter = 0
    
    # Filtrage doublons géométriques consécutifs (jonctions de courbes)
    final_poses = []
    for i, p_data in enumerate(poses_to_create):
        if i > 0:
            if rs.Distance(p_data['pos'], poses_to_create[i-1]['pos']) < 0.001:
                continue
        final_poses.append(p_data)

    for p_data in final_poses:
        pid = rs.InsertBlock("Pose", p_data['pos'])
        rs.ObjectName(pid, str(idx_counter))
        rs.SetUserText(pid, "uuid_origin", str(pid)) # Nouvel UUID origine
        
        for k, v in p_data['meta'].items():
            rs.SetUserText(pid, k, v)
        
        # Force le state si manquant
        st = p_data['state']
        rs.SetUserText(pid, "State", st)
        
        new_pose_ids.append(str(pid))
        new_pose_pts.append(p_data['pos'])
        new_pose_states.append(st)
        idx_counter += 1

    if new_pose_pts:
        rs.InsertBlock("Start", new_pose_pts[0])
        rs.InsertBlock("End", new_pose_pts[-1])

    # 7. Reconstruction Courbes (Logique Import respectée)
    if not rs.IsLayer(traj_lyr): rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    rs.CurrentLayer(traj_lyr)
    
    if len(new_pose_pts) > 1:
        cur_pts = [new_pose_pts[0]]
        cur_uids = [new_pose_ids[0]]
        cur_indices = [0]
        
        # Le premier segment est défini par l'état du point d'arrivée (index 1)
        last_s = new_pose_states[1]

        def build_c(pts, uids, st, idxs):
            if len(pts) < 2: return
            pl = rs.AddPolyline(pts)
            n = "ARCON" if st == "ARCON" else "ARCOF"
            rs.ObjectName(pl, "{} {}-{}".format(n, idxs[0], idxs[-1]))
            rs.ObjectColor(pl, (255,0,0) if st == "ARCON" else (150,150,150))
            rs.SetUserText(pl, "uuid_origin", str(pl))
            for k, u in enumerate(uids):
                rs.SetUserText(pl, "UUID_{}".format(k), u)
                rs.SetUserText(pl, "Pt_{}".format(k), str(idxs[k]))

        for i in range(1, len(new_pose_pts)):
            s = new_pose_states[i]
            
            if s != last_s:
                # Fin du segment précédent
                cur_pts.append(new_pose_pts[i])
                cur_uids.append(new_pose_ids[i])
                cur_indices.append(i)
                build_c(cur_pts, cur_uids, last_s, cur_indices)
                
                # Nouveau segment
                cur_pts = [new_pose_pts[i]]
                cur_uids = [new_pose_ids[i]]
                cur_indices = [i]
                last_s = s
            else:
                cur_pts.append(new_pose_pts[i])
                cur_uids.append(new_pose_ids[i])
                cur_indices.append(i)
        
        build_c(cur_pts, cur_uids, last_s, cur_indices)

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée.", 64)

if __name__ == "__main__":
    analyze_and_rebuild()

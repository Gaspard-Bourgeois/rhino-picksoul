import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import System

def is_program_block(block_id):
    """Vérifie si un bloc est un programme valide (UserText ou Contenu Texte)."""
    if not rs.IsBlockInstance(block_id): return False
    
    # 1. UserText
    if rs.GetUserText(block_id, "type") == "program": return True

    # 2. Contenu du bloc (Recherche d'un objet texte 'program')
    try:
        block_name = rs.BlockInstanceName(block_id)
        objects = rs.BlockObjects(block_name)
        if objects:
            for obj in objects:
                if rs.IsText(obj):
                    txt = rs.TextObjectText(obj)
                    if txt and "program" in txt.lower(): return True
                    # Vérification nom de l'objet texte
                    name = rs.ObjectName(obj)
                    if name and "program" in name.lower(): return True
    except:
        pass
        
    return False

def get_scene_map():
    """Mappe tous les objets de la scène par leur uuid_origin."""
    all_objs = rs.AllObjects()
    mapping = {}
    poses_spatial = [] # Liste pour recherche spatiale de secours
    
    for o in all_objs:
        # Clé d'origine
        u_orig = rs.GetUserText(o, "uuid_origin")
        if not u_orig: u_orig = str(o) # Fallback sur son propre ID
        
        if u_orig not in mapping: mapping[u_orig] = []
        mapping[u_orig].append(o)
        
        # Si c'est une Pose, on la garde pour la recherche spatiale
        if rs.IsBlockInstance(o) and "Pose" in rs.BlockInstanceName(o):
            poses_spatial.append(o)
            
    return mapping, poses_spatial

def ask_global_rule(entity_name):
    """Demande la règle de tri (Avant/Après)."""
    items = ["Apres", "Avant"]
    res = rs.ListBox(items, "Des COPIES de {} ont été détectées.\nOù les placer dans l'ordre ?".format(entity_name), "Règle Globale")
    return res if res else "Apres"

def get_sorted_curves(prog_block, obj_map, user_sel_ids):
    """Récupère et trie les courbes selon la règle et la sélection."""
    
    # 1. Lecture de l'ordre théorique dans le bloc Programme
    # On cherche les clés Crv_0, Crv_1...
    keys = []
    all_keys = rs.GetUserText(prog_block)
    if all_keys:
        for k in all_keys:
            if k.startswith("Crv_"):
                keys.append(k)
    
    # Tri des clés (Crv_1, Crv_2...)
    keys.sort(key=lambda x: int(x.split("_")[1]))
    
    if not keys:
        print("ERREUR: Aucune clé 'Crv_X' trouvée dans le bloc programme.")
        return []

    orig_uuids = [rs.GetUserText(prog_block, k) for k in keys]
    
    final_sequence = []
    rule_defined = False
    global_rule = "Apres" # Valeur par défaut
    
    for u_orig in orig_uuids:
        candidates = obj_map.get(u_orig, [])
        if not candidates: continue
        
        # Filtre sélection utilisateur
        if user_sel_ids:
            filtered = [c for c in candidates if str(c) in user_sel_ids]
            # Si filtrage vide mais qu'il y avait des candidats, on ignore (ce n'est pas sélectionné)
            # SAUF si c'est l'original et qu'on veut garder la structure ? 
            # Non, la demande est de filtrer.
            if not filtered: continue
            to_process = filtered
        else:
            to_process = candidates
            
        # Identification original vs copies
        # L'original est celui dont l'ID Rhino == u_orig OU dont uuid_origin == ID Rhino
        original = None
        copies = []
        for obj in to_process:
            # Vérification robuste de l'original
            is_orig = (str(obj) == u_orig) or (rs.GetUserText(obj, "uuid_origin") == str(obj))
            if is_orig: original = obj
            else: copies.append(obj)
            
        # S'il n'y a que l'original (ou une seule copie unique), on ajoute direct
        if not copies:
            final_sequence.extend(to_process)
            continue
            
        # --- Cas avec Copies ---
        # Si règle pas encore définie, on interagit
        if not rule_defined:
            rs.EnableRedraw(True)
            rs.UnselectAllObjects()
            rs.SelectObjects(copies)
            rs.Redraw()
            global_rule = ask_global_rule("TRAJECTOIRES")
            rule_defined = True
            rs.UnselectAllObjects()
            rs.EnableRedraw(False)
            
        # Application règle
        if global_rule == "Avant":
            final_sequence.extend(copies)
            if original: final_sequence.append(original)
        else:
            if original: final_sequence.append(original)
            final_sequence.extend(copies)
            
    return final_sequence

def find_best_pose_for_vertex(vertex, curve_origin_uuid, pt_index, obj_map, poses_spatial, selection_ids):
    """
    Trouve la Pose correspondante à un sommet de courbe.
    1. Essaie par ID (UserText sur la courbe originale).
    2. Essaie par Proximité spatiale (secours).
    """
    
    # Tentative 1 : Via ID stocké dans la courbe originale
    target_id = rs.GetUserText(curve_origin_uuid, "Pt_{}".format(pt_index))
    if not target_id:
        target_id = rs.GetUserText(curve_origin_uuid, "UUID_{}".format(pt_index))
        
    found_obj = None
    min_dist = 1000.0
    
    # Si on a un ID cible, on regarde dans la map
    if target_id and target_id in obj_map:
        candidates = obj_map[target_id]
        # On cherche le candidat le plus proche géométriquement du point
        for c in candidates:
            # Filtre sélection
            if selection_ids and str(c) not in selection_ids: continue
            
            d = rs.Distance(vertex, rs.BlockInstanceInsertPoint(c))
            if d < 1.0: # Tolérance 1 unité
                if d < min_dist:
                    min_dist = d
                    found_obj = c
    
    # Tentative 2 : Si échec par ID, recherche spatiale pure (Fallback)
    if not found_obj:
        min_dist = 0.5 # Rayon de recherche très strict
        for p_obj in poses_spatial:
            # On ignore si c'est pas dans la sélection active (si sélection existe)
            if selection_ids and str(p_obj) not in selection_ids: continue
            
            d = rs.Distance(vertex, rs.BlockInstanceInsertPoint(p_obj))
            if d < min_dist:
                min_dist = d
                found_obj = p_obj

    return found_obj

def analyze_and_rebuild():
    # 1. Sélection Utilisateur
    sel = rs.GetObjects("Sélectionnez Programmes et/ou Trajets (Entrée = Tout)", preselect=True)
    sel_ids = [str(o) for o in sel] if sel else []
    
    # 2. Trouver les blocs Programmes
    pool = sel if sel else rs.ObjectsByType(rs.filter.instance)
    prog_blocks = []
    if pool:
        for o in pool:
            if is_program_block(o): prog_blocks.append(o)
            
    if not prog_blocks:
        # Si on n'a rien trouvé dans la sélection, on cherche partout
        all_inst = rs.ObjectsByType(rs.filter.instance)
        for o in all_inst:
            if is_program_block(o): prog_blocks.append(o)
    
    if not prog_blocks:
        rs.MessageBox("Aucun bloc 'Program' trouvé.")
        return

    # 3. Choix des programmes (MultiListBox simple)
    names = [rs.ObjectName(p) or "Prog_ID_"+str(p)[-4:] for p in prog_blocks]
    # Tri alphabétique pour la propreté
    # Mais on doit garder la synchro avec la liste d'objets. 
    # On laisse dans l'ordre de découverte.
    
    selected_names = rs.MultiListBox(names, "Programmes à reconstruire :")
    if not selected_names: return

    # 4. Indexation de la scène
    print("Indexation de la scène...")
    rs.EnableRedraw(False)
    obj_map, poses_spatial = get_scene_map()
    
    # 5. Boucle principale
    count_ok = 0
    for name in selected_names:
        # Retrouver l'objet bloc
        idx = names.index(name)
        blk = prog_blocks[idx]
        
        print("Traitement de : " + name)
        
        # A. Tri des Courbes
        sorted_crvs = get_sorted_curves(blk, obj_map, sel_ids)
        if not sorted_crvs:
            print(" -> Pas de courbes trouvées ou tri échoué.")
            continue
            
        # B. Analyse des Poses
        rebuild_data = [] # liste de {pos, state, meta, original_uuid}
        
        for crv in sorted_crvs:
            # Détection état (ARCON/ARCOF)
            nm = rs.ObjectName(crv) or ""
            is_arcon = "ARCON" in nm.upper()
            state_default = "ARCON" if is_arcon else "ARCOF"
            
            # Origine de la courbe (pour lire les UserText Pt_0...)
            u_orig = rs.GetUserText(crv, "uuid_origin")
            if not u_orig: u_orig = str(crv)
            
            verts = rs.PolylineVertices(crv)
            if not verts: continue
            
            for i, v in enumerate(verts):
                # Trouver la pose
                pose_obj = find_best_pose_for_vertex(v, u_orig, i, obj_map, poses_spatial, sel_ids)
                
                meta = {}
                st = state_default
                
                if pose_obj:
                    # Copie des données
                    keys = rs.GetUserText(pose_obj)
                    if keys:
                        for k in keys: meta[k] = rs.GetUserText(pose_obj, k)
                    if "State" in meta: st = meta["State"]
                    
                rebuild_data.append({
                    'pos': v,
                    'state': st,
                    'meta': meta
                })
                
        # C. Nettoyage
        main_lyr = rs.ObjectLayer(blk)
        traj_lyr = main_lyr + "::trajs_arcon_arcof"
        
        # Suppr poses
        on_main = rs.ObjectsByLayer(main_lyr)
        if on_main:
            for o in on_main:
                if rs.IsBlockInstance(o):
                    bn = rs.BlockInstanceName(o)
                    if bn in ["Pose", "Start", "End"]: rs.DeleteObject(o)
        # Suppr trajs
        if rs.IsLayer(traj_lyr):
            rs.DeleteObjects(rs.ObjectsByLayer(traj_lyr))
        else:
            rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)

        # D. Reconstruction
        rs.CurrentLayer(main_lyr)
        
        # Filtrage doublons points
        clean_pts = []
        for i, p in enumerate(rebuild_data):
            if i > 0 and rs.Distance(p['pos'], rebuild_data[i-1]['pos']) < 0.001:
                continue
            clean_pts.append(p)
            
        points_info = [] # pour les lignes
        
        for i, p in enumerate(clean_pts):
            new_blk = rs.InsertBlock("Pose", p['pos'])
            rs.ObjectName(new_blk, str(i))
            # Important : Le nouvel objet devient sa propre origine
            rs.SetUserText(new_blk, "uuid_origin", str(new_blk))
            
            # Injection meta
            for k, val in p['meta'].items():
                rs.SetUserText(new_blk, k, val)
            rs.SetUserText(new_blk, "State", p['state'])
            
            points_info.append({
                'pos': p['pos'],
                'idx': str(i),
                'uuid': str(new_blk),
                'arcon': (p['state'] == "ARCON")
            })

        # Start / End
        if points_info:
            rs.InsertBlock("Start", points_info[0]['pos'])
            rs.InsertBlock("End", points_info[-1]['pos'])

        # Lignes
        rs.CurrentLayer(traj_lyr)
        if len(points_info) > 1:
            segment = [points_info[0]]
            current_state = points_info[0]['arcon']
            
            for k in range(1, len(points_info)):
                next_pt = points_info[k]
                if next_pt['arcon'] != current_state:
                    # Fin du segment
                    create_poly(segment, current_state)
                    # Nouveau segment (chevauchement)
                    segment = [points_info[k-1], next_pt]
                    current_state = next_pt['arcon']
                else:
                    segment.append(next_pt)
            # Dernier bout
            create_poly(segment, current_state)
            
        count_ok += 1

    rs.EnableRedraw(True)
    if count_ok > 0:
        rs.MessageBox("Terminé avec succès pour {} programme(s).".format(count_ok))
    else:
        rs.MessageBox("Terminé mais aucune reconstruction effectuée (voir historique pour erreurs).")

def create_poly(data_list, is_arcon):
    if len(data_list) < 2: return
    pts = [d['pos'] for d in data_list]
    pl = rs.AddPolyline(pts)
    
    prefix = "ARCON" if is_arcon else "ARCOF"
    s_id = data_list[0]['idx']
    e_id = data_list[-1]['idx']
    
    rs.ObjectName(pl, "{} {}-{}".format(prefix, s_id, e_id))
    col = (255, 0, 0) if is_arcon else (150, 150, 150)
    rs.ObjectColor(pl, col)
    
    # Meta data vitale pour le prochain run
    rs.SetUserText(pl, "uuid_origin", str(pl))
    for i, d in enumerate(data_list):
        rs.SetUserText(pl, "Pt_{}".format(i), d['idx'])
        rs.SetUserText(pl, "UUID_{}".format(i), d['uuid'])

if __name__ == "__main__":
    analyze_and_rebuild()

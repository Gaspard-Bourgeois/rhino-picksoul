import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

# ------------------------------------------------------------------
# 1. OUTILS DE RECHERCHE ET DECOUVERTE
# ------------------------------------------------------------------

def is_program_block(block_id):
    """
    Vérifie si un bloc contient un objet Texte nommé 'program' 
    ou dont le contenu est 'program'.
    """
    if not rs.IsBlockInstance(block_id): return False
    
    # 1. Vérification rapide par UserText sur l'instance (standard habituel)
    if rs.GetUserText(block_id, "type") == "program":
        return True

    # 2. Vérification par inspection du contenu du bloc (Spécification demandée)
    block_name = rs.BlockInstanceName(block_id)
    # On regarde dans la définition du bloc
    objects_in_block = rs.BlockObjects(block_name)
    if objects_in_block:
        for obj in objects_in_block:
            # On cherche un objet texte
            if rs.IsText(obj):
                txt_content = rs.TextObjectText(obj)
                obj_name = rs.ObjectName(obj)
                # Si le nom est "program" ou le texte contient "program"
                if (obj_name and "program" in obj_name.lower()) or \
                   (txt_content and "program" in txt_content.lower()):
                    return True
    return False

def get_all_objects_map():
    """
    Crée un dictionnaire de tous les objets de la scène
    Clé = uuid_origin (l'identifiant unique d'origine)
    Valeur = Liste des objets (Original + Copies)
    """
    all_objs = rs.AllObjects()
    obj_map = {}
    for o in all_objs:
        # On cherche l'identifiant d'origine stocké
        u_orig = rs.GetUserText(o, "uuid_origin")
        if not u_orig:
            # Si pas d'uuid_origin, on utilise l'ID de l'objet lui-même (cas de l'original initial)
            u_orig = str(o)
        
        if u_orig not in obj_map:
            obj_map[u_orig] = []
        obj_map[u_orig].append(o)
    return obj_map

# ------------------------------------------------------------------
# 2. LOGIQUE DE TRI ET D'INTERACTION
# ------------------------------------------------------------------

def interactive_sort(original_uuids, object_map, selection_ids, entity_type_name, forced_rule=None):
    """
    Trie les objets (Courbes ou Poses).
    - Détecte les copies.
    - Filtre selon la sélection utilisateur.
    - Interaction visuelle + Question globale si copies détectées.
    """
    final_sequence = []
    global_rule = forced_rule # "Avant" ou "Apres" ou None
    
    # Pour savoir si on doit poser la question (on ne la pose qu'une fois)
    rule_defined = (forced_rule is not None)

    for u_orig in original_uuids:
        # Récupération des candidats (Original + Copies)
        candidates = object_map.get(u_orig, [])
        if not candidates: continue

        # FILTRE : On ne garde que ce qui est dans la sélection utilisateur
        # (Sauf si la sélection utilisateur est vide, on garde tout)
        if selection_ids:
            filtered_candidates = [c for c in candidates if str(c) in selection_ids]
            
            # CRITIQUE : Si le filtrage vide tout, on saute.
            # Mais si on a filtré et qu'il reste au moins une copie, on traite.
            if not filtered_candidates: continue
            current_batch = filtered_candidates
        else:
            current_batch = candidates

        # Identification de l'original (celui dont l'ID Rhino == u_orig)
        # Note : u_orig est l'ID théorique.
        original_obj = None
        copies = []
        
        for obj in current_batch:
            # Si l'objet a un UserText 'uuid_origin' qui est lui-même, c'est l'original
            # Ou si l'ID Rhino correspond à la clé recherchée
            if str(obj) == u_orig or rs.GetUserText(obj, "uuid_origin") == str(obj):
                original_obj = obj
            else:
                copies.append(obj)
        
        # S'il n'y a pas de copies (ou qu'on a filtré les copies), pas de question à poser
        if not copies:
            final_sequence.extend(current_batch)
            continue

        # --- GESTION DES COPIES DETECTEES ---
        
        # Si la règle n'est pas encore définie, on interagit VISUELLEMENT
        if not rule_defined:
            rs.EnableRedraw(True)
            rs.UnselectAllObjects()
            rs.SelectObjects(copies) # On montre les copies
            rs.Redraw()
            
            msg = "Copies de {} détectées dans la sélection.\n\nRègle GLOBALE pour ce programme :\nOù placer les copies par rapport à l'original ?".format(entity_type_name)
            res = rs.GetString(msg, "Apres", ["Avant", "Apres"])
            
            rs.UnselectAllObjects()
            rs.EnableRedraw(False)
            
            global_rule = "Avant" if (res and res.upper() == "AVANT") else "Apres"
            rule_defined = True

        # Application de la règle
        if global_rule == "Avant":
            final_sequence.extend(copies)
            if original_obj and original_obj in current_batch:
                final_sequence.append(original_obj)
        else:
            if original_obj and original_obj in current_batch:
                final_sequence.append(original_obj)
            final_sequence.extend(copies)
            
    return final_sequence, global_rule

# ------------------------------------------------------------------
# 3. TRAITEMENT PAR PROGRAMME
# ------------------------------------------------------------------

def process_program(prog_block, obj_map, selection_ids):
    prog_name = rs.ObjectName(prog_block) or "SansNom"
    
    # A. Lecture de la séquence officielle dans le bloc Program
    # On cherche les clés Crv_0, Crv_1, etc.
    keys = sorted([k for k in rs.GetUserText(prog_block) if k.startswith("Crv_")], 
                  key=lambda x: int(x.split("_")[1]))
    
    if not keys:
        print("Programme {} vide ou mal formé.".format(prog_name))
        return

    orig_curve_uuids = [rs.GetUserText(prog_block, k) for k in keys]

    # B. Traitement des COURBES (Trajs)
    # On trie et on demande la règle pour les courbes
    sorted_curves, rule_curves = interactive_sort(orig_curve_uuids, obj_map, selection_ids, "TRAJECTOIRES")
    
    if not sorted_curves:
        return

    # C. Extraction des données pour les POSES
    # On doit trouver les poses associées aux courbes triées.
    # LOGIQUE : On lit les UserText de la courbe (Pt_0 -> ID_Pose).
    
    poses_to_create = [] # Liste de dicts
    
    for crv in sorted_curves:
        # L'UUID Origin de cette courbe (pour savoir quelles clés lire)
        u_orig_crv = rs.GetUserText(crv, "uuid_origin")
        if not u_orig_crv: u_orig_crv = str(crv)
        
        # Récupération de l'état (Arcon/Arcof)
        # On regarde le nom ou une métadonnée
        is_arcon = False
        state_txt = "ARCOF"
        
        # Essai de détection de l'état via le nom ou UserText
        nm = rs.ObjectName(crv) or ""
        if "ARCON" in nm: 
            is_arcon = True
            state_txt = "ARCON"
        
        # Récupération des points géométriques
        verts = rs.PolylineVertices(crv)
        if not verts: continue
        
        # Pour chaque sommet, on cherche l'ID de la pose cible
        for i, pt_pos in enumerate(verts):
            # Clé attendue : Pt_0, Pt_1...
            key_pt = "Pt_{}".format(i)
            target_pose_origin_id = rs.GetUserText(u_orig_crv, key_pt)
            
            # Clé pour l'UUID : UUID_0, UUID_1... (souvent utilisé en backup)
            target_pose_uuid_key = "UUID_{}".format(i)
            backup_uuid = rs.GetUserText(u_orig_crv, target_pose_uuid_key)
            
            target_id = target_pose_origin_id if target_pose_origin_id else backup_uuid
            
            # Recherche de la Pose correspondante
            found_pose_obj = None
            
            if target_id and target_id in obj_map:
                candidates = obj_map[target_id]
                
                # PRÉCISION PAR ID + PROXIMITÉ :
                # Si c'est une copie, on a plusieurs Poses avec le même uuid_origin.
                # On prend celle qui est physiquement sous le sommet de la courbe.
                # C'est le seul moyen de lier "Copie Courbe A" -> "Copie Pose A" sans ambiguité
                best_dist = 0.1 # Tolérance
                
                for cand in candidates:
                    # Si une sélection est active, on vérifie si la pose est dedans
                    if selection_ids and str(cand) not in selection_ids:
                        continue
                        
                    dist = rs.Distance(pt_pos, rs.BlockInstanceInsertPoint(cand))
                    if dist < best_dist:
                        best_dist = dist
                        found_pose_obj = cand
            
            # Extraction métadonnées de la Pose trouvée
            meta_data = {}
            if found_pose_obj:
                # On copie tout le UserText
                keys_ut = rs.GetUserText(found_pose_obj)
                for k in keys_ut:
                    meta_data[k] = rs.GetUserText(found_pose_obj, k)
                
                # Mise à jour de l'état si défini dans la pose
                if "State" in meta_data:
                    state_txt = meta_data["State"]
            
            poses_to_create.append({
                'pos': pt_pos,
                'state': state_txt,
                'meta': meta_data,
                'origin_id': target_id # On garde le lien
            })

    # D. Nettoyage (Remplacement in-place)
    main_lyr = rs.ObjectLayer(prog_block)
    traj_lyr = main_lyr + "::trajs_arcon_arcof"
    
    # Suppression des anciennes Poses et Start/End sur le calque principal
    existing_objs = rs.ObjectsByLayer(main_lyr)
    to_delete = []
    for o in existing_objs:
        if rs.IsBlockInstance(o):
            bn = rs.BlockInstanceName(o)
            if bn in ["Pose", "Start", "End"]:
                to_delete.append(o)
    
    # Suppression des trajectoires
    if rs.IsLayer(traj_lyr):
        to_delete.extend(rs.ObjectsByLayer(traj_lyr))
        
    if to_delete:
        rs.DeleteObjects(to_delete)

    # E. Reconstruction
    rs.CurrentLayer(main_lyr)
    
    new_inst_data = [] # Pour reconstruire les courbes après
    
    # Filtrage doublons points (si fin == début suivant)
    final_points = []
    for i, p in enumerate(poses_to_create):
        if i > 0 and rs.Distance(p['pos'], poses_to_create[i-1]['pos']) < 0.001:
            continue
        final_points.append(p)
        
    for idx, p_data in enumerate(final_points):
        # Création du bloc Pose
        pid = rs.InsertBlock("Pose", p_data['pos'])
        rs.ObjectName(pid, str(idx))
        
        # Injection métadonnées
        rs.SetUserText(pid, "uuid_origin", str(pid)) # Devient une nouvelle origine
        for k, v in p_data['meta'].items():
            rs.SetUserText(pid, k, v)
        rs.SetUserText(pid, "State", p_data['state'])
        
        is_arcon = (p_data['state'] == "ARCON")
        new_inst_data.append({'idx': str(idx), 'pos': p_data['pos'], 'arcon': is_arcon, 'uuid': str(pid)})

    # Start / End
    if new_inst_data:
        rs.InsertBlock("Start", new_inst_data[0]['pos'])
        rs.InsertBlock("End", new_inst_data[-1]['pos'])

    # Reconstruction des lignes (Courbes)
    if not rs.IsLayer(traj_lyr): rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    rs.CurrentLayer(traj_lyr)

    if len(new_inst_data) > 1:
        seg = [new_inst_data[0]]
        last_s = new_inst_data[0]['arcon']
        
        def build_poly(data_seg, state):
            if len(data_seg) < 2: return
            pts = [d['pos'] for d in data_seg]
            pl = rs.AddPolyline(pts)
            
            prefix = "ARCON" if state else "ARCOF"
            start_i = data_seg[0]['idx']
            end_i = data_seg[-1]['idx']
            
            rs.ObjectName(pl, "{} {}-{}".format(prefix, start_i, end_i))
            rs.ObjectColor(pl, (255, 0, 0) if state else (150, 150, 150))
            
            # Stockage des IDs pour le prochain run (cycle vertueux)
            rs.SetUserText(pl, "uuid_origin", str(pl))
            for i, d in enumerate(data_seg):
                rs.SetUserText(pl, "Pt_{}".format(i), d['idx']) # Nom/Index
                rs.SetUserText(pl, "UUID_{}".format(i), d['uuid']) # Guid
        
        for i in range(1, len(new_inst_data)):
            curr_s = new_inst_data[i]['arcon']
            if curr_s != last_s:
                build_poly(seg, last_s)
                seg = [new_inst_data[i-1], new_inst_data[i]] # Chevauchement pour continuité
                last_s = curr_s
            else:
                seg.append(new_inst_data[i])
        build_poly(seg, last_s)

# ------------------------------------------------------------------
# 4. FONCTION PRINCIPALE
# ------------------------------------------------------------------

def main():
    # 1. Sélection Initiale Utilisateur (Portée & Filtre)
    sel = rs.GetObjects("Sélectionnez les programmes et/ou trajectoires (Entrée = Tout)", preselect=True)
    sel_ids = [str(o) for o in sel] if sel else []
    
    # 2. Identification des Programmes concernés
    all_objs = sel if sel else rs.AllObjects()
    prog_blocks = []
    
    # Recherche large : on cherche les blocs Programmes dans tout le fichier 
    # ou dans la sélection
    candidates = sel if sel else rs.ObjectsByType(rs.filter.instance)
    for obj in candidates:
        if is_program_block(obj):
            prog_blocks.append(obj)
            
    if not prog_blocks:
        # Si la sélection ne contenait pas le bloc programme lui-même mais juste des courbes,
        # on essaie de trouver le programme parent via les calques ou recherche globale
        # Pour simplifier ici : on cherche tous les programmes et on demande à l'utilisateur.
        candidates = rs.ObjectsByType(rs.filter.instance)
        for obj in candidates:
            if is_program_block(obj):
                prog_blocks.append(obj)

    if not prog_blocks:
        rs.MessageBox("Aucun bloc 'Program' trouvé (contenant texte 'program').")
        return

    # Liste de choix pour traiter plusieurs programmes
    prog_names = [rs.ObjectName(p) or "Prog_{}".format(i) for i, p in enumerate(prog_blocks)]
    # On pré-sélectionne ceux qui étaient dans la sélection utilisateur
    defaults = [True if str(p) in sel_ids else False for p in prog_blocks]
    # Si rien sélectionné, tout cocher par défaut ? Non, laissons l'utilisateur choisir.
    if not any(defaults): defaults = [True] * len(prog_blocks)
    
    selected_programs_idx = rs.MultiListBox(prog_names, "Quels programmes reconstruire ?", "Batch Rebuild", defaults)
    
    if not selected_programs_idx: return

    # 3. Préparation globale (Map des objets)
    rs.EnableRedraw(False)
    object_map = get_all_objects_map()
    
    # 4. Exécution
    for idx in range(len(prog_names)):
        # MultiListBox renvoie les indices si on ne passe pas la liste, ou les noms ?
        # RhinoScript MultiListBox renvoie les strings sélectionnés.
        # Il faut retrouver l'index.
        p_name = selected_programs_idx[idx] # Attention logique boucle
        # Correction boucle pour matcher les noms retournés
        pass

    # Boucle corrigée sur les noms retournés
    for p_name in selected_programs_idx:
        # Retrouver l'objet bloc correspondant au nom
        # (Attention si doublons de noms, mieux vaut utiliser indices si possible, 
        # mais MultiListBox renvoie les items)
        idx = prog_names.index(p_name)
        target_block = prog_blocks[idx]
        
        process_program(target_block, object_map, sel_ids)

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée pour {} programme(s).".format(len(selected_programs_idx)))

if __name__ == "__main__":
    main()

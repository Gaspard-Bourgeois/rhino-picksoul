import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

# ------------------------------------------------------------------
# OUTILS DE DEBUG ET LOG
# ------------------------------------------------------------------
def log(msg):
    """Affiche un message dans la console pour le debug."""
    print("[DEBUG] " + str(msg))

# ------------------------------------------------------------------
# 1. RECHERCHE ET IDENTIFICATION
# ------------------------------------------------------------------

def is_program_block(obj_id):
    """
    Vérifie si un bloc contient un objet texte 'program' (Spécification stricte).
    """
    if not rs.IsBlockInstance(obj_id): 
        return False
    
    block_name = rs.BlockInstanceName(obj_id)
    # On regarde dans la définition du bloc
    objects_in_block = rs.BlockObjects(block_name)
    
    if not objects_in_block:
        return False
        
    for o in objects_in_block:
        # On cherche un objet texte
        if rs.IsText(o):
            txt_content = rs.TextObjectText(o)
            obj_name = rs.ObjectName(o)
            # Critère : Nom de l'objet ou contenu du texte contient "program"
            if (obj_name and "program" in obj_name.lower()) or \
               (txt_content and "program" in txt_content.lower()):
                return True
    return False

def get_all_objects_map():
    """
    Indexe TOUS les objets de la scène par leur 'uuid_origin'.
    C'est la base de données pour retrouver les copies.
    """
    log("Indexation des objets de la scène...")
    all_objs = rs.AllObjects()
    obj_map = {} 
    
    count = 0
    for o in all_objs:
        u_orig = rs.GetUserText(o, "uuid_origin")
        # Si pas d'uuid_origin, l'objet est son propre original
        if not u_orig: u_orig = str(o)
        
        if u_orig not in obj_map: obj_map[u_orig] = []
        obj_map[u_orig].append(o)
        count += 1
        
    log("Indexation terminée. {} objets traités.".format(count))
    return obj_map

# ------------------------------------------------------------------
# 2. LOGIQUE DE TRI (Adaptation Script 1)
# ------------------------------------------------------------------

def get_sorted_instances_global(original_uuids, object_map, selection_ids, entity_label, forced_rule=None):
    """
    Trie les instances.
    Si copies détectées :
    1. Sélectionne visuellement (Script 1 logic).
    2. Demande l'ordre UNE SEULE FOIS (Global logic).
    3. Filtre par sélection utilisateur.
    """
    final_sequence = []
    current_rule = forced_rule # "Avant", "Apres" ou None si pas encore défini
    
    log("--- Tri des {} ({} originaux à traiter) ---".format(entity_label, len(original_uuids)))

    for u_orig in original_uuids:
        if u_orig not in object_map:
            log("ATTENTION: L'objet original {} est introuvable dans la scène (supprimé ?)".format(u_orig))
            continue
        
        candidates = object_map[u_orig]
        
        # Filtre : On ne garde que ceux qui sont dans la sélection utilisateur
        to_process = []
        original_obj = None
        
        # Identification de l'original au sens strict (ID Rhino match l'UUID cherché)
        # ou self-reference dans UserText
        for c in candidates:
            is_orig = (str(c) == u_orig) or (rs.GetUserText(c, "uuid_origin") == str(c))
            if is_orig: original_obj = c
            
            # Logique de filtre stricte :
            # Si aucune sélection active (None/Empty) -> On prend tout.
            # Si sélection active -> On ne prend que ce qui est dedans.
            if not selection_ids or (str(c) in selection_ids):
                to_process.append(c)
        
        if not to_process: 
            # log("Ignoré : {} (Hors sélection)".format(u_orig))
            continue

        # Gestion des Copies
        if len(to_process) == 1:
            # Cas simple : Un seul objet (Original ou une copie unique)
            final_sequence.append(to_process[0])
        
        else:
            # Cas multiple : Il faut trier
            log("Doublons détectés pour l'ID {}. Candidats : {}".format(u_orig, len(to_process)))
            
            copies = [x for x in to_process if x != original_obj]
            # S'il n'y a pas de copies dans le lot filtré (juste l'original), on continue
            if not copies:
                if original_obj and original_obj in to_process:
                    final_sequence.append(original_obj)
                continue

            # INTERACTION VISUELLE (Si règle pas encore définie)
            if current_rule is None:
                log("Interaction utilisateur requise pour règle globale...")
                rs.EnableRedraw(True)
                rs.UnselectAllObjects()
                rs.SelectObjects(copies) # Montrer les copies
                rs.Redraw()
                
                msg = "Copies détectées pour {}.\nRègle GLOBALE : Où placer les copies par rapport à l'original ?".format(entity_label)
                opt = rs.GetString(msg, "Apres", ["Avant", "Apres"])
                
                rs.UnselectAllObjects()
                rs.EnableRedraw(False)
                
                current_rule = "Avant" if (opt and opt.upper() == "AVANT") else "Apres"
                log("Règle définie : " + current_rule)

            # Application de la règle
            batch = []
            if current_rule == "Avant":
                batch.extend(copies)
                if original_obj and original_obj in to_process: batch.append(original_obj)
            else:
                if original_obj and original_obj in to_process: batch.append(original_obj)
                batch.extend(copies)
            
            final_sequence.extend(batch)
            
    return final_sequence, current_rule

# ------------------------------------------------------------------
# 3. ANALYSE ET RECONSTRUCTION
# ------------------------------------------------------------------

def process_single_program(prog_block, obj_map, user_sel_ids):
    p_name = rs.ObjectName(prog_block) or str(prog_block)
    log("Traitement du programme : " + p_name)
    
    # --- ETAPE A : Les Courbes ---
    # Lecture des clés Crv_ dans le UserText du bloc
    keys = sorted([k for k in rs.GetUserText(prog_block) if k.startswith("Crv_")], key=lambda x: int(x.split("_")[1]))
    if not keys:
        log("ERREUR CRITIQUE : Aucune clé 'Crv_' trouvée dans le bloc programme.")
        return

    orig_curve_uuids = [rs.GetUserText(prog_block, k) for k in keys]
    
    # Tri interactif des courbes
    sorted_curves, rule_curves = get_sorted_instances_global(orig_curve_uuids, obj_map, user_sel_ids, "TRAJECTOIRES")
    
    if not sorted_curves:
        log("Aucune courbe à traiter après filtrage/tri.")
        return

    # --- ETAPE B : Extraction des Données (Poses) ---
    # Logique : On parcourt les courbes TRIEES. Pour chaque sommet, on trouve la Pose.
    poses_data_list = []
    
    log("Extraction des données depuis {} courbes...".format(len(sorted_curves)))
    
    for crv_idx, crv in enumerate(sorted_curves):
        verts = rs.PolylineVertices(crv)
        if not verts: continue
        
        # Récupération de l'ID origine de CETTE courbe (pour savoir quel Pt_X chercher)
        u_orig_crv = rs.GetUserText(crv, "uuid_origin")
        if not u_orig_crv: u_orig_crv = str(crv)
        
        # État (ARCON/ARCOF) basé sur le nom
        nm = rs.ObjectName(crv) or ""
        state_curve = "ARCON" if "ARCON" in nm else "ARCOF"

        for i, pt in enumerate(verts):
            # C'est ici que la précision par ID intervient
            # On cherche l'ID de la Pose Originale associée au point i de la Courbe Originale
            
            # Clé Pt_i ou UUID_i
            pose_orig_id = rs.GetUserText(u_orig_crv, "Pt_{}".format(i))
            if not pose_orig_id:
                 pose_orig_id = rs.GetUserText(u_orig_crv, "UUID_{}".format(i))
            
            best_pose = None
            
            if pose_orig_id and pose_orig_id in obj_map:
                candidates = obj_map[pose_orig_id]
                
                # PRÉCISION STRICTE :
                # Parmi les candidats (Original + Copies de la pose), lequel est sous le sommet ?
                # On utilise une tolérance géométrique très fine (0.01 comme Script 1)
                
                # Si filtrage activé, on ne regarde que les poses sélectionnées par l'utilisateur
                valid_candidates = []
                for c in candidates:
                     if not user_sel_ids or str(c) in user_sel_ids:
                         valid_candidates.append(c)
                
                # Recherche géométrique
                min_dist = 0.1 # Tolérance
                for cand in valid_candidates:
                    dist = rs.Distance(pt, rs.BlockInstanceInsertPoint(cand))
                    if dist < min_dist:
                        best_pose = cand
                        min_dist = dist # On prend le plus proche si ambiguité
            else:
                log("AVERTISSEMENT : Pas d'ID de pose trouvé sur la courbe (index {}) ou ID inconnu.".format(i))

            # Extraction Metadatas
            meta = {}
            state = state_curve # Par défaut, état de la courbe
            
            if best_pose:
                # Copie intégrale des UserText
                ut_keys = rs.GetUserText(best_pose)
                if ut_keys:
                    for k in ut_keys: meta[k] = rs.GetUserText(best_pose, k)
                
                if "State" in meta: state = meta["State"]
            else:
                log("ERREUR : Aucune Pose trouvée sous le sommet {} de la courbe {}. ID cible : {}".format(i, crv_idx, pose_orig_id))
                # Pas de sécurité demandée : on enregistre quand même le point, mais il sera "vide" de meta

            poses_data_list.append({'pos': pt, 'meta': meta, 'state': state})

    # --- ETAPE C : Nettoyage (In-Place) ---
    log("Nettoyage des anciens objets...")
    main_lyr = rs.ObjectLayer(prog_block)
    traj_lyr = main_lyr + "::trajs_arcon_arcof"
    
    # Suppression Poses existantes sur le calque
    to_del = []
    layer_objs = rs.ObjectsByLayer(main_lyr)
    if layer_objs:
        for o in layer_objs:
            if rs.IsBlockInstance(o):
                bn = rs.BlockInstanceName(o)
                if bn in ["Pose", "Start", "End"]: to_del.append(o)
    
    # Suppression Trajectoires existantes
    if rs.IsLayer(traj_lyr):
        to_del.extend(rs.ObjectsByLayer(traj_lyr))
    
    if to_del:
        rs.DeleteObjects(to_del)
        log("{} objets supprimés.".format(len(to_del)))

    # --- ETAPE D : Reconstruction ---
    log("Reconstruction...")
    rs.CurrentLayer(main_lyr)
    
    new_inst_data = []
    idx_counter = 0

    # Filtre anti-doublon (points superposés)
    final_points = []
    for i, p in enumerate(poses_data_list):
        if i > 0 and rs.Distance(p['pos'], poses_data_list[i-1]['pos']) < 0.001:
            continue
        final_points.append(p)

    # Création des blocs Poses
    for p_data in final_points:
        pid = rs.InsertBlock("Pose", p_data['pos'])
        rs.ObjectName(pid, str(idx_counter))
        
        # Le nouvel objet devient sa propre référence pour le futur
        rs.SetUserText(pid, "uuid_origin", str(pid))
        
        for k, v in p_data['meta'].items():
            rs.SetUserText(pid, k, v)
        
        # Forcer l'écriture du State
        rs.SetUserText(pid, "State", p_data['state'])
        
        is_arcon = (p_data['state'] == "ARCON")
        new_inst_data.append({'idx': str(idx_counter), 'pos': p_data['pos'], 'arcon': is_arcon, 'uuid': str(pid)})
        idx_counter += 1

    # Start / End
    if new_inst_data:
        rs.InsertBlock("Start", new_inst_data[0]['pos'])
        rs.InsertBlock("End", new_inst_data[-1]['pos'])

    # Création des Courbes (Exactement logique Import)
    if not rs.IsLayer(traj_lyr): rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    rs.CurrentLayer(traj_lyr)

    if len(new_inst_data) > 1:
        def build_t(data, state):
            if len(data) < 2: return
            pid = rs.AddPolyline([d['pos'] for d in data])
            pref = "ARCON" if state else "ARCOF"
            rs.ObjectName(pid, "{} {}-{}".format(pref, data[0]['idx'], data[-1]['idx']))
            rs.ObjectColor(pid, (255,0,0) if state else (150,150,150))
            
            # Stockage crucial pour relecture future
            rs.SetUserText(pid, "uuid_origin", str(pid))
            for i, d in enumerate(data):
                rs.SetUserText(pid, "Pt_{}".format(i), d['idx'])    # Le nom (0, 1, 2...)
                rs.SetUserText(pid, "UUID_{}".format(i), d['uuid']) # L'ID unique

        seg = [new_inst_data[0]]
        last_s = new_inst_data[0]['arcon']
        
        for i in range(1, len(new_inst_data)):
            if new_inst_data[i]['arcon'] != last_s:
                build_t(seg, last_s)
                seg = [new_inst_data[i-1], new_inst_data[i]]
                last_s = new_inst_data[i]['arcon']
            else:
                seg.append(new_inst_data[i])
        build_t(seg, last_s)

    log("Fin du traitement pour ce programme.")


def main():
    rs.ClearCommandHistory()
    log("Démarrage du script...")
    
    # 1. Sélection Utilisateur
    sel = rs.GetObjects("Sélectionnez les programmes et éléments à traiter (Entrée = Tout)", preselect=True)
    sel_ids = [str(o) for o in sel] if sel else []
    
    # 2. Recherche des blocs "Program"
    # On cherche dans la sélection, ou partout si pas de sélection
    search_pool = sel if sel else rs.ObjectsByType(rs.filter.instance)
    prog_blocks = []
    
    if search_pool:
        for o in search_pool:
            if is_program_block(o):
                prog_blocks.append(o)
    
    # Si rien trouvé dans la sélection, on cherche dans TOUT le document (si l'utilisateur n'a sélectionné que des courbes par erreur)
    if not prog_blocks and sel:
        log("Pas de programme dans la sélection directe, recherche globale...")
        all_inst = rs.ObjectsByType(rs.filter.instance)
        for o in all_inst:
            if is_program_block(o): prog_blocks.append(o)
            
    if not prog_blocks:
        log("ERREUR FATALE : Aucun bloc 'Program' trouvé (contenant texte 'program').")
        rs.MessageBox("Aucun bloc 'Program' trouvé.")
        return

    # 3. Choix des programmes
    # Simplification : on liste tout, l'utilisateur coche
    names = [rs.ObjectName(p) or "Prog_SansNom_{}".format(i) for i, p in enumerate(prog_blocks)]
    
    # On utilise GetObjects si possible, sinon MultiListBox
    # MultiListBox est plus sûr pour les noms
    selected_names = rs.MultiListBox(names, "Quels programmes reconstruire ?", "Batch Rebuild")
    
    if not selected_names: 
        log("Annulation utilisateur.")
        return

    # 4. Map globale
    object_map = get_all_objects_map()
    
    rs.EnableRedraw(False)
    
    # 5. Boucle principale
    for name in selected_names:
        idx = names.index(name)
        blk = prog_blocks[idx]
        process_single_program(blk, object_map, sel_ids)
        
    rs.EnableRedraw(True)
    rs.MessageBox("Terminé. Vérifiez l'historique de commande (F2) pour les détails.")

if __name__ == "__main__":
    main()

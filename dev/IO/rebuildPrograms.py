import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def find_program_block(objs):
    """Trouve le bloc programme parent."""
    for o in objs:
        if rs.IsBlockInstance(o) and rs.GetUserText(o, "type") == "program":
            return o
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
    Trie les objets. Si copies détectées :
    1. Sélectionne visuellement les objets concernés.
    2. Demande l'ordre (Avant/Après).
    3. Désélectionne.
    """
    final_sequence = []
    
    # On itère sur la séquence définie dans le bloc Program
    for u_orig in original_uuids:
        if u_orig not in object_map: continue
        
        candidates = object_map[u_orig]
        
        # Filtre : On ne garde que ceux qui sont dans la sélection utilisateur (s'il y en a une)
        # OU si pas de sélection, on prend tout.
        to_process = []
        original_obj = None
        
        for c in candidates:
            # On identifie l'original par son ID Rhino qui match l'uuid_origin
            is_orig = (str(c) == u_orig)
            if is_orig: original_obj = c
            
            # Si aucune sélection active, on traite tout.
            # Si sélection active, on ne traite que si c'est dedans (ou si c'est l'original, on le garde souvent pour référence)
            if not selection_ids or (str(c) in selection_ids):
                to_process.append(c)
        
        # Si après filtrage on a rien, on passe
        if not to_process: continue

        # Gestion des Copies
        # Cas 1: Unique (Original ou une seule copie sélectionnée)
        if len(to_process) == 1:
            final_sequence.append(to_process[0])
        
        # Cas 2: Multiples (Original + Copies ou plusieurs Copies)
        else:
            # Identifier les copies
            copies = [x for x in to_process if x != original_obj]
            current_batch = []
            if original_obj and original_obj in to_process: current_batch.append(original_obj)
            current_batch.extend(copies)

            if len(copies) > 0:
                # INTERACTION : Sélectionner pour montrer à l'utilisateur
                rs.EnableRedraw(True)
                rs.UnselectAllObjects()
                rs.SelectObjects(current_batch)
                rs.Redraw()
                
                msg = "Copies détectées pour {}.\nOù placer les copies sélectionnées par rapport à l'original ?".format(prompt_label)
                opt = rs.GetString(msg, "Apres", ["Avant", "Apres"])
                
                rs.UnselectAllObjects()
                rs.EnableRedraw(False)
                
                if not opt: opt = "Apres"
                
                if opt.upper() == "AVANT":
                    final_sequence.extend(copies)
                    if original_obj and original_obj in to_process: final_sequence.append(original_obj)
                else:
                    if original_obj and original_obj in to_process: final_sequence.append(original_obj)
                    final_sequence.extend(copies)
            else:
                final_sequence.extend(current_batch)
            
    return final_sequence

def analyze_and_rebuild():
    sel = rs.GetObjects("Sélectionnez les éléments (Laissez vide pour tout traiter)", preselect=True)
    sel_ids = [str(o) for o in sel] if sel else []
    
    search_pool = sel if sel else rs.AllObjects()
    prog_block = find_program_block(search_pool)
    
    if not prog_block:
        rs.MessageBox("Bloc 'Program' introuvable.", 16)
        return

    main_lyr = rs.ObjectLayer(prog_block)
    traj_lyr = main_lyr + "::trajs_arcon_arcof"
    
    rs.EnableRedraw(False)

    # 1. Indexation de tous les objets par leur origine
    all_objs = rs.AllObjects()
    obj_map = {} # Map curve_uuid -> [obj_curve_1, obj_curve_2]
    
    # On a aussi besoin de trouver les poses spatialement plus tard
    # On stocke toutes les Poses présentes dans la scène pour recherche de proximité
    scene_poses = [] 

    for o in all_objs:
        u = rs.GetUserText(o, "uuid_origin")
        if u:
            if u not in obj_map: obj_map[u] = []
            obj_map[u].append(o)
        
        if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose":
            scene_poses.append(o)

    # 2. Ordonnancement des COURBES
    keys = sorted([k for k in rs.GetUserText(prog_block) if k.startswith("Crv_")], key=lambda x: int(x.split("_")[1]))
    orig_curve_uuids = [rs.GetUserText(prog_block, k) for k in keys]

    sorted_curves = get_sorted_instances(orig_curve_uuids, obj_map, sel_ids, "segment de courbe")

    # 3. Extraction des données (Memory Build)
    # On va construire une liste plate de tous les points à créer
    poses_data_list = []
    
    for crv in sorted_curves:
        verts = rs.PolylineVertices(crv)
        if not verts: continue
        
        # Pour chaque sommet de la courbe, on doit trouver la Pose correspondante
        # Si c'est une copie, la Pose est aussi une copie située au même endroit.
        for i, pt in enumerate(verts):
            
            # Recherche de la Pose la plus proche géométriquement
            # C'est la méthode la plus robuste pour les copies (car UserText UUID pointe vers l'original)
            best_pose = None
            min_dist = 0.01 # Tolérance
            
            for p_obj in scene_poses:
                # Optimisation possible : vérifier d'abord si p_obj est dans la selection ou calque
                if rs.Distance(pt, rs.BlockInstanceInsertPoint(p_obj)) < min_dist:
                    best_pose = p_obj
                    break # On a trouvé la pose sous le sommet
            
            meta = {}
            state = "ARCOF" # Défaut
            
            if best_pose:
                # On récupère les infos de la pose trouvée
                for k in ["ID_C", "BC", "Type", "V", "VJ", "PL", "Comment", "State"]:
                    val = rs.GetUserText(best_pose, k)
                    if val: meta[k] = val
                
                if "State" in meta: state = meta["State"]
            else:
                # Fallback : si on ne trouve pas de pose (supprimée?), on essaie de lire les infos 
                # stockées en backup sur la courbe elle-même lors de l'import (UUID_x pointe vers pose orig)
                ref_u = rs.GetUserText(crv, "UUID_{}".format(i))
                # On ne peut pas facilement récupérer les datas d'un objet supprimé, 
                # donc on espère que la Pose est là.
                pass

            poses_data_list.append({'pos': pt, 'meta': meta, 'state': state})

    # 4. Suppression de l'ancien (Clean up)
    # On ne supprime que ce qui est sur les calques cibles
    to_del = []
    for o in rs.ObjectsByLayer(main_lyr):
        if rs.IsBlockInstance(o):
            bn = rs.BlockInstanceName(o)
            if bn in ["Pose", "Start", "End"]: to_del.append(o)
    
    if rs.IsLayer(traj_lyr):
        to_del.extend(rs.ObjectsByLayer(traj_lyr))
        
    rs.DeleteObjects(to_del)

    # 5. Création des nouvelles Poses
    rs.CurrentLayer(main_lyr)
    
    new_inst_data = [] # Pour la reconstruction des courbes
    idx_counter = 0

    # Filtre anti-doublon strict (si fin courbe 1 == début courbe 2)
    # On fusionne uniquement si distance ~ 0
    final_points = []
    for i, p in enumerate(poses_data_list):
        if i > 0 and rs.Distance(p['pos'], poses_data_list[i-1]['pos']) < 0.001:
            continue
        final_points.append(p)

    for p_data in final_points:
        pid = rs.InsertBlock("Pose", p_data['pos'])
        rs.ObjectName(pid, str(idx_counter))
        rs.SetUserText(pid, "uuid_origin", str(pid))
        
        for k, v in p_data['meta'].items():
            rs.SetUserText(pid, k, v)
        
        # S'assurer que State est écrit
        st = p_data['state']
        rs.SetUserText(pid, "State", st)
        
        # On prépare la data pour les courbes (compatible avec logique Import)
        #

import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import re

def get_num_from_name(name):
    """Extrait le premier nombre d'une chaîne (ex: 'ARCON 0-5' -> 0)."""
    match = re.search(r'\d+', name)
    return int(match.group()) if match else -1

def get_instance_id(obj):
    """Récupère le nom de l'instance comme entier."""
    name = rs.ObjectName(obj)
    try: return int(name)
    except: return -1

def is_copy(obj_id):
    """Vérifie si l'objet est une copie via l'UUID d'origine."""
    origin_uuid = rs.GetUserText(obj_id, "uuid_origin")
    return str(obj_id) != origin_uuid

def get_obj_position(obj_id):
    """Retourne la position (point d'insertion pour bloc, ou premier point pour courbe)."""
    if rs.IsBlockInstance(obj_id):
        return rs.BlockInstanceInsertPoint(obj_id)
    elif rs.IsPolyline(obj_id):
        return rs.PolylineVertices(obj_id)[0]
    return None

def analyze_and_rebuild_jbi():
    # 1. Paramètres Utilisateur
    parent_layer = rs.GetLayer("Sélectionner le calque du programme à analyser")
    if not parent_layer: return

    copy_order = rs.GetString("Ordre des copies", "last", ["first", "last"])
    if not copy_order: return

    # 2. Collecte des données
    all_objs = rs.ObjectsByLayer(parent_layer, True)
    instances = []
    curves = []

    for obj in all_objs:
        if rs.IsBlockInstance(obj):
            instances.append(obj)
        elif rs.IsCurve(obj):
            # On ne prend que les polylignes nommées ARCON/ARCOF
            name = rs.ObjectName(obj)
            if name and ("ARCON" in name or "ARCOF" in name):
                curves.append(obj)

    if not curves: 
        print("Aucune courbe de trajectoire trouvée.")
        return

    # 3. Groupement des instances par Nom (ID numérique)
    inst_groups = {}
    for inst in instances:
        idx = get_instance_id(inst)
        if idx not in inst_groups: inst_groups[idx] = []
        
        # Déduplication par position
        pos = get_obj_position(inst)
        is_dup_pos = False
        for existing in inst_groups[idx]:
            if rs.Distance(pos, get_obj_position(existing)) < 0.001:
                is_dup_pos = True
                break
        
        if not is_dup_pos:
            inst_groups[idx].append(inst)

    # Tri des instances dans chaque groupe (Original vs Copie selon copyOrder)
    for idx in inst_groups:
        inst_groups[idx].sort(key=lambda x: is_copy(x), reverse=(copy_order == "first"))

    # 4. Groupement et Tri des Courbes
    # On trie par le numéro de départ présent dans le nom
    curves.sort(key=lambda x: (get_num_from_name(rs.ObjectName(x)), is_copy(x)))
    
    # Si copyOrder = first, on doit s'assurer que pour un même numéro, la copie passe avant
    if copy_order == "first":
        # Tri stable : d'abord par UUID (copie ou pas), puis par numéro
        curves.sort(key=lambda x: is_copy(x), reverse=True)
        curves.sort(key=lambda x: get_num_from_name(rs.ObjectName(x)))

    # 5. Reconstruction de la séquence
    new_sequence_points = [] # Liste de dict: {'pos': Point3d, 'arcon': bool, 'old_inst': ID}
    used_instances = set()

    for crv in curves:
        is_arcon = "ARCON" in rs.ObjectName(crv)
        vertices = rs.PolylineVertices(crv)
        if not vertices: continue

        # Récupération des IDs d'instances liés à cette courbe via UserStrings
        # Note: On suit l'ordre des points de la polyligne
        for i in range(len(vertices)):
            inst_name = rs.GetUserText(crv, "Pt_{}".format(i))
            if inst_name is None: continue
            
            idx = int(inst_name)
            if idx in inst_groups and inst_groups[idx]:
                # On prend l'instance selon l'ordre défini (first/last)
                # Mais si on a plusieurs copies d'une courbe, il faut une logique de mapping
                # Ici, on simplifie : on prend l'instance du groupe
                target_inst = inst_groups[idx][0] # À affiner selon le nombre de copies de la courbe
                
                new_sequence_points.append({
                    'pos': vertices[i],
                    'arcon': is_arcon,
                    'old_obj': target_inst
                })
                used_instances.add(target_inst)

    # 6. Nettoyage et Renommage
    # Supprimer les instances non utilisées
    for inst in instances:
        if inst not in used_instances:
            rs.DeleteObject(inst)

    # 7. Création du nouveau programme
    # On recrée un calque "REBUILT_PROG"
    new_parent = rs.AddLayer("REBUILT_" + parent_layer.split("::")[-1])
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=new_parent)
    
    # Renommage des instances restantes et replacement
    final_instances = []
    for i, data in enumerate(new_sequence_points):
        # On déplace l'ancienne instance ou on en crée une nouvelle si nécessaire
        # Ici on renomme simplement les instances existantes dans l'ordre
        old_obj = data['old_obj']
        new_id_name = str(i)
        
        # Si l'objet a déjà été renommé (partagé entre 2 courbes), on l'ignore ou on duplique
        rs.ObjectName(old_obj, new_id_name)
        rs.ObjectLayer(old_obj, new_parent)
        final_instances.append(old_obj)

    # 8. Recréation des courbes ARCON/ARCOF
    rs.CurrentLayer(traj_lyr)
    if len(new_sequence_points) > 1:
        temp_pts = [new_sequence_points[0]['pos']]
        last_state = new_sequence_points[0]['arcon']
        start_idx = 0

        def build_final_curve(pts, state, s_idx, e_idx):
            if len(pts) < 2: return
            cid = rs.AddPolyline(pts)
            pref = "ARCON" if state else "ARCOF"
            rs.ObjectName(cid, "{} {}-{}".format(pref, s_idx, e_idx))
            rs.ObjectColor(cid, (255,0,0) if state else (150,150,150))

        for i in range(1, len(new_sequence_points)):
            curr = new_sequence_points[i]
            if curr['arcon'] != last_state:
                build_final_curve(temp_pts, last_state, start_idx, i-1)
                temp_pts = [new_sequence_points[i-1]['pos'], curr['pos']]
                start_idx = i - 1
                last_state = curr['arcon']
            else:
                temp_pts.append(curr['pos'])
        
        build_final_curve(temp_pts, last_state, start_idx, len(new_sequence_points)-1)

    rs.MessageBox("Analyse terminée. Nouveau programme créé dans le calque REBUILT.")

if __name__ == "__main__":
    analyze_and_rebuild_jbi()

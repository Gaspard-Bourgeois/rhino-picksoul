# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def create_pose_block():
    """Crée le bloc 'Pose' (trièdre RVB) s'il n'existe pas."""
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        items = []
        # Axes X (Rouge), Y (Vert), Z (Bleu)
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
        rs.EnableRedraw(True)
    return "Pose"

def explode_instance_only(obj_id):
    """Explose l'objet uniquement s'il s'agit d'une instance de bloc."""
    if rs.IsBlockInstance(obj_id):
        return rs.ExplodeBlockInstance(obj_id)
    return None

def get_next_instance_index(block_name):
    """
    Trouve l'indice Y unique pour un block_name donné dans le document
    en scannant les UserTexts existants.
    """
    max_index = 0
    # On cherche dans tous les objets du document ayant du UserText
    all_objs = rs.AllObjects()
    for obj in all_objs:
        keys = rs.GetUserText(obj)
        if keys:
            for key in keys:
                if key.startswith("BlockNameLevel_"):
                    value = rs.GetUserText(obj, key)
                    if value and "#" in value:
                        name_part, index_part = value.split("#")
                        if name_part == block_name:
                            try:
                                idx = int(index_part)
                                if idx > max_index: max_index = idx
                            except ValueError:
                                continue
    return max_index + 1

def get_current_hierarchy_info(obj_id):
    """
    Récupère le niveau d'imbrication actuel à partir des UserTexts.
    Retourne le niveau suivant (X) et les dictionnaires de textes existants.
    """
    keys = rs.GetUserText(obj_id)
    max_level = -1
    existing_data = {}
    
    if keys:
        for key in keys:
            if key.startswith("BlockNameLevel_"):
                try:
                    lvl = int(key.split("_")[-1])
                    if lvl > max_level: max_level = lvl
                    existing_data[key] = rs.GetUserText(obj_id, key)
                except ValueError:
                    continue
    
    return max_level + 1, existing_data

def decompose_reciproque():
    # Sélection multiple
    object_ids = rs.GetObjects("Sélectionnez les blocs à décomposer", preselect=True)
    if not object_ids: return

    all_results = []
    create_pose_block()
    
    rs.EnableRedraw(False)
    
    for obj_id in object_ids:
        # --- CAS 1 : C'EST UN BLOC ---
        if rs.IsBlockInstance(obj_id):
            block_name = rs.BlockInstanceName(obj_id)
            block_xform = rs.BlockInstanceXform(obj_id)
            
            # 1. Récupération de la hiérarchie actuelle
            next_level, hierarchy_history = get_current_hierarchy_info(obj_id)
            
            # 2. Calcul de l'indice unique Y pour ce nom de bloc
            instance_index = get_next_instance_index(block_name)
            
            # 3. Explosion (un seul niveau)
            exploded_items = explode_instance_only(obj_id)
            if not exploded_items: continue
            
            # 4. Insertion du bloc Pose à l'origine locale transformée
            origin_obj = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(origin_obj, block_xform)
            
            # 5. Marquage UserText
            # On reporte l'historique des niveaux parents
            for key, val in hierarchy_history.items():
                rs.SetUserText(origin_obj, key, val)
            
            # On ajoute le niveau actuel : BlockNameLevel_X = block_name#Y
            new_key = "BlockNameLevel_{}".format(next_level)
            new_value = "{}#{}".format(block_name, instance_index)
            rs.SetUserText(origin_obj, new_key, new_value)
            
            all_results.extend(exploded_items)
            all_results.append(origin_obj)

        # --- CAS 2 : OBJET GÉOMÉTRIQUE ---
        else:
            # On le garde tel quel
            all_results.append(obj_id)

    # Finalisation (pas de groupe selon les instructions)
    rs.UnselectAllObjects()
    if all_results:
        rs.SelectObjects(all_results)
    
    rs.EnableRedraw(True)
    print("Décomposition terminée. {} objets traités.".format(len(all_results)))

if __name__ == "__main__":
    decompose_reciproque()

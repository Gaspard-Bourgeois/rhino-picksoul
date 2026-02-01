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

def explode_any(obj_id):
    """
    Fonction utilitaire pour exploser n'importe quel type d'objet.
    Remplace le 'rs.ExplodeObjects' inexistant.
    """
    if rs.IsPolysurface(obj_id):
        return rs.ExplodePolysurfaces(obj_id, delete_input=True)
    elif rs.IsCurve(obj_id) and not rs.IsLine(obj_id):
        return rs.ExplodeCurves(obj_id, delete_input=True)
    elif rs.IsMesh(obj_id):
        return rs.ExplodeMesh(obj_id, delete_input=True)
    return None

def decompose_reciproque():
    # Sélection multiple
    object_ids = rs.GetObjects("Sélectionnez les objets ou blocs à décomposer", preselect=True)
    if not object_ids: return

    all_results = []
    create_pose_block()
    
    rs.EnableRedraw(False)
    
    for obj_id in object_ids:
        # --- CAS 1 : C'EST UN BLOC ---
        if rs.IsBlockInstance(obj_id):
            block_name = rs.BlockInstanceName(obj_id)
            block_xform = rs.BlockInstanceXform(obj_id)
            insert_pt = rs.BlockInstanceInsertPoint(obj_id)
            
            # Explosion du bloc (un seul niveau)
            exploded_items = rs.ExplodeBlockInstance(obj_id)
            
            origin_obj = None
            # On cherche si un sous-bloc "Pose" est déjà présent à l'origine
            for item in exploded_items:
                if rs.IsBlockInstance(item):
                    if rs.BlockInstanceInsertPoint(item) == insert_pt:
                        origin_obj = item
                        break
            
            # Si pas de Pose trouvée, on l'insère
            if not origin_obj:
                origin_obj = rs.InsertBlock("Pose", [0,0,0])
                rs.TransformObject(origin_obj, block_xform)
                exploded_items.append(origin_obj)

            # Marquage avec le nom d'origine
            rs.SetUserText(origin_obj, "OriginalBlockName", block_name)
            
            # Groupement du résultat
            group = rs.AddGroup()
            rs.AddObjectsToGroup(exploded_items, group)
            all_results.extend(exploded_items)

        # --- CAS 2 : C'EST UN OBJET GÉOMÉTRIQUE (Polysurface, Courbe, etc.) ---
        else:
            exploded_geo = explode_any(obj_id)
            if exploded_geo:
                group = rs.AddGroup()
                rs.AddObjectsToGroup(exploded_geo, group)
                all_results.extend(exploded_geo)
            else:
                # Si l'objet n'est pas explosable (ex: une ligne seule), on le garde
                all_results.append(obj_id)

    # Finalisation
    rs.UnselectAllObjects()
    if all_results:
        rs.SelectObjects(all_results)
    
    rs.EnableRedraw(True)
    print("Décomposition terminée pour {} objet(s).".format(len(object_ids)))

if __name__ == "__main__":
    decompose_reciproque()

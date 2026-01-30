import rhinoscriptsyntax as rs

def create_pose_block():
    if not rs.IsBlock("Pose"):
        items = []
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
    return "Pose"

def decompose_reciproque():
    # Support de la présélection
    block_id = rs.GetObject("Sélectionnez une instance de bloc", rs.filter.instance, preselect=True)
    if not block_id: return

    block_name = rs.BlockInstanceName(block_id)
    block_xform = rs.BlockInstanceXform(block_id)
    
    # Exploser le bloc
    exploded_objects = rs.ExplodeBlockInstance(block_id)
    
    origin_obj = None
    # On cherche un objet qui a la même transformation (situé à l'origine 0,0,0 du bloc original)
    # Dans Rhino, après explosion, on vérifie la position relative
    for obj in exploded_objects:
        # Si c'est une instance (sous-bloc), on peut comparer les xform
        if rs.IsBlockInstance(obj):
            if rs.BlockInstanceXform(obj) == block_xform:
                origin_obj = obj
                break
    
    # Si pas d'objet trouvé, on ajoute le bloc Pose
    if not origin_obj:
        create_pose_block()
        origin_obj = rs.InsertBlock("Pose", [0,0,0])
        rs.TransformObject(origin_obj, block_xform)
        exploded_objects.append(origin_obj)

    # Ajouter la clé
    rs.SetUserText(origin_obj, "OriginalBlockName", block_name)
    
    # Grouper
    group_name = rs.AddGroup()
    rs.AddObjectsToGroup(exploded_objects, group_name)
    
    # Sélectionner les objets à la fin
    rs.UnselectAllObjects()
    rs.SelectObjects(exploded_objects)
    print("Bloc décomposé. Objet origine : {}".format(origin_obj))

if __name__ == "__main__":
    decompose_reciproque()

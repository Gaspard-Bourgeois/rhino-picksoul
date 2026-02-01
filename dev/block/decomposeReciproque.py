import rhinoscriptsyntax as rs

def create_pose_block():
    """Vérifie l'existence du bloc 'Pose' ou le crée avec un trièdre RVB."""
    if not rs.IsBlock("Pose"):
        items = []
        # X = Rouge, Y = Vert, Z = Bleu
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
    return "Pose"

def decompose_reciproque():
    # Support de la sélection multiple (objets de tout type)
    object_ids = rs.GetObjects("Sélectionnez les blocs ou objets à décomposer", preselect=True)
    if not object_ids: return

    all_results = []
    
    rs.EnableRedraw(False)
    
    for obj_id in object_ids:
        if rs.IsBlockInstance(obj_id):
            # --- TRAITEMENT DES BLOCS ---
            block_name = rs.BlockInstanceName(obj_id)
            block_xform = rs.BlockInstanceXform(obj_id)
            # Point d'insertion dans le repère Monde
            insert_pt = rs.BlockInstanceInsertPoint(obj_id)
            
            # Exploser l'instance
            exploded_items = rs.ExplodeBlockInstance(obj_id)
            
            origin_obj = None
            # Recherche d'un sous-bloc situé exactement à l'origine du bloc parent
            for item in exploded_items:
                if rs.IsBlockInstance(item):
                    # On compare le point d'insertion du sous-objet avec celui du parent
                    if rs.BlockInstanceInsertPoint(item) == insert_pt:
                        origin_obj = item
                        break
            
            # Si aucune "Pose" ou objet d'origine n'est trouvé, on en crée un
            if not origin_obj:
                create_pose_block()
                origin_obj = rs.InsertBlock("Pose", [0,0,0])
                rs.TransformObject(origin_obj, block_xform)
                exploded_items.append(origin_obj)

            # Ajout de la clé UserText
            rs.SetUserText(origin_obj, "OriginalBlockName", block_name)
            
            # Création d'un groupe pour les composants du bloc explosé
            group_name = rs.AddGroup()
            rs.AddObjectsToGroup(exploded_items, group_name)
            all_results.extend(exploded_items)
            
        else:
            # --- TRAITEMENT DES AUTRES OBJETS (Explode standard) ---
            # rs.ExplodeObjects décompose les courbes, polysurfaces, etc.
            exploded_geometry = rs.ExplodeObjects(obj_id, delete_input=True)
            
            if exploded_geometry:
                # Si l'objet a pu être décomposé, on groupe le résultat
                group_name = rs.AddGroup()
                rs.AddObjectsToGroup(exploded_geometry, group_name)
                all_results.extend(exploded_geometry)
            else:
                # Si l'objet ne peut pas être explosé (ex: une ligne simple), on le garde
                all_results.append(obj_id)

    # --- FINALISATION ---
    rs.UnselectAllObjects()
    if all_results:
        rs.SelectObjects(all_results)
        
    rs.EnableRedraw(True)
    print("Traitement terminé sur {} objet(s) source(s).".format(len(object_ids)))

if __name__ == "__main__":
    decompose_reciproque()

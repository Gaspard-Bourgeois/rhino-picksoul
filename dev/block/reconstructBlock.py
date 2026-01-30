import rhinoscriptsyntax as rs

def are_geometries_different(objs, block_name, origin_xform):
    # Comparaison simplifiée : nombre d'objets
    def_objs_count = rs.BlockObjectCount(block_name)
    # On soustrait 1 pour ignorer l'objet "origine" dans le compte
    if (len(objs) - 1) != def_objs_count:
        return True
    return False # On pourrait pousser la comparaison par IDs ou BoundingBox ici

def reconstruct_block():
    # Correction : rs.GetObjects n'a pas groupSelect, Rhino gère les groupes par défaut
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None

    for obj in initial_objs:
        name = rs.GetUserText(obj, "OriginalBlockName")
        if name:
            origin_obj = obj
            block_name = name
            break

    if not origin_obj:
        print("Aucun objet origine trouvé.")
        return

    # Récupérer la transformation de l'objet origine
    # Si c'est une instance, on prend sa xform, sinon on peut utiliser sa Box
    if rs.IsBlockInstance(origin_obj):
        xform = rs.BlockInstanceXform(origin_obj)
    else:
        # Pour un objet standard, on génère une xform de translation simple vers son point de base
        pt = rs.BoxPoint(rs.BoundingBox(origin_obj), 0)
        xform = rs.XformTranslation(pt)

    # Insérer une instance temporaire pour comparaison/visu
    temp_instance = rs.InsertBlock(block_name, [0,0,0])
    rs.TransformObject(temp_instance, xform)
    rs.SelectObject(temp_instance) # Sélectionner avant la question

    if are_geometries_different(initial_objs, block_name, xform):
        msg = "La géométrie diffère. Mettre à jour la définition de '{}' ?".format(block_name)
        update = rs.GetString(msg, "Non", ["Oui", "Non"])
        
        if update == "Oui":
            # Calcul de l'inverse (Correction : renvoie 1 seul argument)
            inv_xform = rs.XformInverse(xform)
            
            new_def_geometries = []
            for o in initial_objs:
                if o != origin_obj:
                    copy = rs.CopyObject(o)
                    rs.TransformObject(copy, inv_xform)
                    new_def_geometries.append(copy)
            
            # Recréer le bloc (écrase l'ancien)
            rs.AddBlock(new_def_geometries, [0,0,0], block_name, delete_input=True)
            # Supprimer la version temporaire devenue obsolète et en remettre une à jour
            rs.DeleteObject(temp_instance)
            temp_instance = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(temp_instance, xform)
            print("Définition mise à jour.")

    # Garder les objets initiaux sélectionnés à la fin
    rs.UnselectAllObjects()
    rs.SelectObjects(initial_objs)
    print("Reconstruction terminée.")

if __name__ == "__main__":
    reconstruct_block()

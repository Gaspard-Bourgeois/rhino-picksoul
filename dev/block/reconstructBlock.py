import rhinoscriptsyntax as rs

def rebuild_reciproque():
    # 1. Sélection des objets
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None
    xform = None

    # 2. Recherche de l'objet origine via la clé
    for obj in initial_objs:
        val = rs.GetUserText(obj, "OriginalBlockName")
        if val:
            origin_obj = obj
            block_name = val
            if rs.IsBlockInstance(obj):
                xform = rs.BlockInstanceXform(obj)
            break

    # 3. Gestion de l'absence d'origine (Correction sur le nom de l'objet)
    if not origin_obj:
        ref_id = rs.GetObject("Origine non trouvée. Référence ou [Entrée] pour Monde")
        if ref_id:
            # On utilise le nom de l'objet (ObjectName) et non celui de la définition de bloc
            block_name = rs.ObjectName(ref_id)
            if not block_name and rs.IsBlockInstance(ref_id):
                block_name = rs.BlockInstanceName(ref_id)
            
            # Si toujours pas de nom, on demande
            if not block_name:
                block_name = rs.GetString("Nom du bloc", "NouveauBloc")
                
            xform = rs.BlockInstanceXform(ref_id) if rs.IsBlockInstance(ref_id) else rs.XformRotation(0, [0,0,1], [0,0,0])
        else:
            block_name = rs.GetString("Nom du bloc", "NouveauBloc")
            xform = rs.XformIdentity()
    
    if not block_name: return

    # 4. Insertion préalable pour comparaison visuelle
    temp_instance = None
    if rs.IsBlock(block_name):
        temp_instance = rs.InsertBlock(block_name, [0,0,0])
        rs.TransformObject(temp_instance, xform)
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        
        msg = "Le bloc '{}' existe déjà. Mettre à jour sa définition et remplacer les objets ?".format(block_name)
    else:
        msg = "Le bloc '{}' n'existe pas. Créer la définition et remplacer les objets ?".format(block_name)

    # 5. Demande à l'utilisateur
    confirm = rs.GetString(msg, "Oui", ["Oui", "Non"])
    
    if confirm == "Oui":
        # Préparation de la géométrie (Transformation inverse pour le repère local 0,0,0)
        inv_xform = rs.XformInverse(xform)
        
        new_geometries = []
        for o in initial_objs:
            # On exclut l'objet "Pose" (trièdre) de la nouvelle définition pour ne pas polluer le bloc
            if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose":
                continue
            
            copy = rs.CopyObject(o)
            rs.TransformObject(copy, inv_xform)
            new_geometries.append(copy)

        # Mise à jour ou création de la définition
        rs.AddBlock(new_geometries, [0,0,0], block_name, delete_input=True)
        
        # Si on avait inséré une instance temporaire, elle est déjà à jour (Rhino met à jour les instances)
        # Sinon, on en insère une nouvelle
        if not temp_instance:
            temp_instance = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(temp_instance, xform)
        
        # Suppression des objets initiaux
        rs.DeleteObjects(initial_objs)
        
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        print("Bloc '{}' reconstruit avec succès.".format(block_name))
        
    else:
        # Si Non : on nettoie l'instance temporaire si elle a été créée
        if temp_instance:
            rs.DeleteObject(temp_instance)
        rs.UnselectAllObjects()
        rs.SelectObjects(initial_objs)
        print("Action annulée.")

if __name__ == "__main__":
    rebuild_reciproque()

import rhinoscriptsyntax as rs

def rebuild_reciproque():
    # 1. Sélection des objets (preselect=True, Rhino gère les groupes par défaut)
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None
    xform = None

    # 2. Recherche de l'objet origine via la clé UserText
    for obj in initial_objs:
        val = rs.GetUserText(obj, "OriginalBlockName")
        if val:
            origin_obj = obj
            block_name = val
            # On récupère la transformation (si c'est une instance)
            if rs.IsBlockInstance(obj):
                xform = rs.BlockInstanceXform(obj)
            break

    # 3. Gestion de l'absence d'origine
    if not origin_obj:
        ref_id = rs.GetObject("Origine non trouvée. Référence ou [Entrée] pour Monde", rs.filter.instance)
        if ref_id:
            block_name = rs.BlockInstanceName(ref_id)
            xform = rs.BlockInstanceXform(ref_id)
        else:
            block_name = rs.GetString("Nom du bloc", "NouveauBloc")
            xform = rs.XformIdentity()
    
    # Si après tout ça on n'a toujours pas de nom, on arrête
    if not block_name: return

    # 4. Comparaison (facultatif selon les étapes, mais on vérifie si la définition existe)
    # On prépare la géométrie pour la définition (déplacement vers 0,0,0 local)
    inv_xform = rs.XformInverse(xform) # Un seul argument renvoyé
    
    new_geometries = []
    for o in initial_objs:
        # On évite d'inclure le trièdre "Pose" dans la définition si c'est lui l'origine
        if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose":
            continue
        
        copy = rs.CopyObject(o)
        rs.TransformObject(copy, inv_xform)
        new_geometries.append(copy)

    # 5. Mise à jour de la définition de bloc
    # rs.AddBlock avec un nom existant redéfinit le bloc
    rs.AddBlock(new_geometries, [0,0,0], block_name, delete_input=True)
    
    # 6. Substitution visuelle
    # On insère la nouvelle instance au même endroit que l'origine trouvée
    new_instance = rs.InsertBlock(block_name, [0,0,0])
    rs.TransformObject(new_instance, xform)
    
    # On sélectionne l'instance pour que l'utilisateur puisse comparer avant suppression
    rs.UnselectAllObjects()
    rs.SelectObject(new_instance)
    
    # Question de confirmation pour la mise à jour (Optionnel selon votre flux)
    confirm = rs.GetString("Remplacer les objets par le bloc '{}' ?".format(block_name), "Oui", ["Oui", "Non"])
    
    if confirm == "Oui":
        rs.DeleteObjects(initial_objs)
        # On garde uniquement la nouvelle instance sélectionnée
        rs.SelectObject(new_instance)
        print("Bloc '{}' mis à jour et substitué.".format(block_name))
    else:
        # On supprime l'instance temporaire et on revient à l'état initial
        rs.DeleteObject(new_instance)
        rs.SelectObjects(initial_objs)
        print("Reconstruction annulée, objets conservés.")

if __name__ == "__main__":
    rebuild_reciproque()

import rhinoscriptsyntax as rs

def reconstruct_block():
    objs = rs.GetObjects("Sélectionnez les objets ou le groupe à reconstruire", groupSelect=True)
    if not objs: return

    origin_obj = None
    block_name = None

    # Trouver l'objet origine avec la clé UserText
    for obj in objs:
        name = rs.GetUserText(obj, "OriginalBlockName")
        if name:
            origin_obj = obj
            block_name = name
            break

    if not origin_obj:
        print("Erreur : Aucun objet d'origine avec métadonnées trouvé.")
        return

    # Obtenir la transformation actuelle de l'objet Pose
    # On utilise sa matrice de transformation relative au plan monde
    xform = rs.BlockInstanceXform(origin_obj)
    
    # Demander si on veut mettre à jour la définition
    update = rs.GetString("Mettre à jour la définition du bloc '{}' ?".format(block_name), "Non", ["Oui", "Non"])
    
    if update == "Oui":
        # On définit le point d'insertion comme l'origine de l'objet Pose (inverse de la xform)
        inv_xform, success = rs.XformInverse(xform)
        
        # On duplique les objets pour la définition (sans l'objet Pose lui-même)
        geometry_to_define = [rs.CopyObject(o) for o in objs if o != origin_obj]
        for g in geometry_to_define:
            rs.TransformObject(g, inv_xform)
            
        # Mise à jour (Supprimer l'ancienne définition et recréer)
        rs.AddBlock(geometry_to_define, [0,0,0], block_name, delete_input=True)
        print("Définition du bloc '{}' mise à jour.".format(block_name))

    # Insérer l'instance (optionnel : on peut choisir de remplacer les objets ou juste l'ajouter)
    new_instance = rs.InsertBlock(block_name, [0,0,0])
    rs.TransformObject(new_instance, xform)
    
    print("Instance du bloc '{}' insérée.".format(block_name))
    # Note : les objets sélectionnés sont conservés comme demandé.

if __name__ == "__main__":
    reconstruct_block()

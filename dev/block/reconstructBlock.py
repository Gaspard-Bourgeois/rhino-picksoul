import rhinoscriptsyntax as rs
import math
import Rhino

def rebuild_reciproque():
    # 1. Sélection des objets
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None
    xform = None
    block_name_list = rs.BlockNames()

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
            block_name = rs.BlockInstanceName(ref_id)
          
            
            if rs.IsBlockInstance(ref_id):
                xform = rs.BlockInstanceXform(ref_id) 
            else:
                box = rs.BoundingBox(ref_id)
                center = math.mean(box)
                xform = Rhino.Geometry.Transform.Translation(center-[0,0,0])
        else:
            block_name = "NouveauBloc"
            xform = rs.XformIdentity()

        if block_name[-5:].lower() == "_base":
            block_name = block_name[:-5]
        if block_name[-2:].isdigit() and block_name[-3] == "_":
            block_name = block_name[:-3]
        
        free_block_name = block_name
        for i in range(100):
            if free_block_name not in block_name_list:
                break
            free_block_name =  "{}_{:02d}".format(block_name, i)
        block_name = free_block_name
    
    if not block_name: return

    # 4. Insertion préalable pour comparaison visuelle
    confirm = "Oui"
    temp_instance = None
    if rs.IsBlock(block_name):
        temp_instance = rs.InsertBlock(block_name, [0,0,0])
        rs.TransformObject(temp_instance, xform)
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        
        msg = "Le bloc '{}' existe déjà. Mettre à jour sa définition et remplacer les objets ?".format(block_name)
        # 5. Demande à l'utilisateur
        confirm = rs.GetString(msg, "Oui", ["Oui", "Non"])
    
    if confirm == "Oui":
        # Préparation de la géométrie (Transformation inverse pour le repère local 0,0,0)
        inv_xform = rs.XformInverse(xform)
        
        new_geometries = []
        for o in initial_objs:
            # On exclut l'objet "Pose" (trièdre) de la nouvelle définition pour ne pas polluer le bloc
            if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose" and rs.GetUserText(o, "OriginalBlockName"):
                continue
            
            copy = rs.CopyObject(o)
            rs.TransformObject(copy, inv_xform)
            new_geometries.append(copy)

        # Mise à jour ou création de la définition
        rs.AddBlock(new_geometries, [0,0,0], block_name, delete_input=True)
        rs.DeleteObjects(new_geometries)
        
        # Si on avait inséré une instance temporaire, elle est déjà à jour (Rhino met à jour les instances)
        # Sinon, on en insère une nouvelle
        if not temp_instance:
            temp_instance = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(temp_instance, xform)
        
        # Suppression des objets initiaux
        rs.DeleteObjects(initial_objs)
        
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        print("Bloc '{}' (re)construit avec succès.".format(block_name))
        

if __name__ == "__main__":
    rebuild_reciproque()

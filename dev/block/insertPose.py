import rhinoscriptsyntax as rs

def create_pose_block():
    """Vérifie l'existence du bloc 'Pose' ou le crée avec un trièdre RVB."""
    if rs.IsBlock("Pose"):
        return "Pose"
    
    # Empêcher le rafraîchissement pendant la création des composants
    rs.EnableRedraw(False)
    
    # Création des axes du trièdre (1 unité de long)
    origin = [0, 0, 0]
    x_axis = rs.AddLine(origin, [1, 0, 0])
    y_axis = rs.AddLine(origin, [0, 1, 0])
    z_axis = rs.AddLine(origin, [0, 0, 1])
    
    # Attribution des couleurs RVB
    rs.ObjectColor(x_axis, [255, 0, 0])
    rs.ObjectColor(y_axis, [0, 255, 0])
    rs.ObjectColor(z_axis, [0, 0, 255])
    
    # Définition du bloc et suppression des objets temporaires
    rs.AddBlock([x_axis, y_axis, z_axis], origin, "Pose", True)
    
    rs.EnableRedraw(True)
    return "Pose"

def main():
    block_name = create_pose_block()
    selected_ids = rs.SelectedObjects()
    
    insertion_points = []
    
    # CAS D : Rien n'est sélectionné -> Insertion au point [0,0,0]
    if not selected_ids:
        insertion_points.append([0, 0, 0])
        
    # CAS A : Une seule instance de bloc sélectionnée
    elif len(selected_ids) == 1 and rs.IsBlockInstance(selected_ids[0]):
        insertion_points.append(rs.BlockInstanceInsertPoint(selected_ids[0]))
        
    else:
        # CAS B : Recherche de blocs avec la clé "BlocOrigin" dans la sélection
        points_from_keys = []
        for obj_id in selected_ids:
            if rs.IsBlockInstance(obj_id):
                if rs.GetUserText(obj_id, "BlocOrigin") is not None:
                    points_from_keys.append(rs.BlockInstanceInsertPoint(obj_id))
        
        if points_from_keys:
            insertion_points = points_from_keys
        else:
            # CAS C : Centre de la Bounding Box de TOUS les objets sélectionnés
            bbox = rs.BoundingBox(selected_ids)
            if bbox:
                # Moyenne entre le point min (0) et le point max diagonalement opposé (6)
                center = (bbox[0] + bbox[6]) / 2
                insertion_points.append(center)

    # --- Insertion et Sélection ---
    if insertion_points:
        rs.EnableRedraw(False)
        
        # On désélectionne tout pour ne garder que les nouveaux blocs à la fin
        rs.UnselectAllObjects()
        
        new_instances = []
        for pt in insertion_points:
            new_id = rs.InsertBlock(block_name, pt)
            if new_id:
                new_instances.append(new_id)
        
        # Sélection finale des objets créés
        if new_instances:
            rs.SelectObjects(new_instances)
            
        rs.EnableRedraw(True)
        print("Opération terminée : {} instance(s) 'Pose' insérée(s).".format(len(new_instances)))

if __name__ == "__main__":
    main()

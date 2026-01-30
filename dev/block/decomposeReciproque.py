import rhinoscriptsyntax as rs
import Rhino

def create_pose_block():
    # Crée un trièdre de base si le bloc "Pose" n'existe pas
    if not rs.IsBlock("Pose"):
        items = []
        # Axe X (Rouge), Y (Vert), Z (Bleu)
        items.append(rs.AddLine([0,0,0], [1,0,0])) # X
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0])) # Y
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1])) # Z
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
    return "Pose"

def decompose_reciproque():
    block_id = rs.GetObject("Sélectionnez une instance de bloc", rs.filter.instance)
    if not block_id: return

    block_name = rs.BlockInstanceName(block_id)
    xform = rs.BlockInstanceXform(block_id)
    
    # Créer/Récupérer le bloc Pose
    create_pose_block()
    
    # Exploser le bloc
    exploded_objects = rs.ExplodeBlockInstance(block_id)
    
    # Insérer le marqueur de Pose à l'emplacement exact du bloc
    pose_id = rs.InsertBlock("Pose", [0,0,0])
    rs.TransformObject(pose_id, xform)
    
    # Ajouter la clé pour la reconstruction
    rs.SetUserText(pose_id, "OriginalBlockName", block_name)
    rs.ObjectName(pose_id, "ORIGIN_" + block_name)
    
    # Grouper le tout
    all_objs = exploded_objects + [pose_id]
    group_name = rs.AddGroup()
    rs.AddObjectsToGroup(all_objs, group_name)
    
    print("Bloc '{}' décomposé avec succès.".format(block_name))

if __name__ == "__main__":
    decompose_reciproque()

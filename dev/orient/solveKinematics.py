import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import json

def get_joint_info(obj_id):
    """Récupère et décode les données du joint."""
    data_str = rs.GetUserString(obj_id, "KinematicJoint")
    if not data_str: return None
    return json.loads(data_str)

def align_blocks(parent_id, child_id):
    """Calcule et applique la transformation pour aligner l'enfant sur le parent."""
    data_p = get_joint_info(parent_id)
    data_c = get_joint_info(child_id)
    
    if not data_p or not data_c: return

    # 1. Obtenir les matrices actuelles
    xform_p = rs.BlockInstanceXform(parent_id)
    xform_c = rs.BlockInstanceXform(child_id)

    # 2. Calculer la position CIBLE (définie par le Parent dans le monde)
    target_pt = rg.Point3d(*data_p["origin"])
    target_pt.Transform(xform_p)
    
    target_axis = None
    if data_p["axis"]:
        target_axis = rg.Vector3d(*data_p["axis"])
        target_axis.Transform(xform_p)

    # 3. Obtenir la position ACTUELLE du joint sur l'enfant (dans le monde)
    current_pt = rg.Point3d(*data_c["origin"])
    current_pt.Transform(xform_c)
    
    current_axis = None
    if data_c["axis"]:
        current_axis = rg.Vector3d(*data_c["axis"])
        current_axis.Transform(xform_c)

    # --- LOGIQUE SELON LE TYPE ---
    joint_type = data_c["type"]
    
    # A. Translation (Sauf pour la Glissière pure où la translation est libre sur l'axe)
    if joint_type != "SLIDER":
        translation = rg.Transform.Translation(target_pt - current_pt)
        rs.TransformObject(child_id, translation)
        # Mettre à jour la matrice de l'enfant après translation pour le calcul de rotation
        xform_c = rs.BlockInstanceXform(child_id)
        current_pt.Transform(translation)

    # B. Orientation (Pivot, Glissière, Rigide, Cylindrique nécessitent un alignement d'axe)
    needs_axis = ["REVOLUTE", "SLIDER", "CYLINDRICAL", "RIGID", "PIN_SLOT"]
    if joint_type in needs_axis and target_axis and current_axis:
        # Calcul de la rotation pour aligner le vecteur actuel sur le vecteur cible
        rotation = rg.Transform.Rotation(current_axis, target_axis, target_pt)
        rs.TransformObject(child_id, rotation)

def solve_kinematics(start_node=None):
    """
    Parcourt la chaîne cinématique. 
    Si start_node est fourni (après création), il commence par là.
    Sinon, demande à l'utilisateur.
    """
    if not start_node:
        start_node = rs.GetObject("Sélectionnez le bloc parent (racine)", rs.filter.instance)
    
    if not start_node: return

    # File d'attente pour traiter la chaîne (BFS)
    queue = [start_node]
    processed = []

    while queue:
        current_parent = queue.pop(0)
        processed.append(current_parent)
        
        # Trouver les enfants (ceux qui pointent vers ce parent)
        all_instances = rs.ObjectsByType(rs.filter.instance)
        for inst in all_instances:
            if inst in processed: continue
            
            info = get_joint_info(inst)
            if info and info["partner"] == str(current_parent):
                print("Alignement de {0} sur {1} (Type: {2})".format(inst, current_parent, info["type"]))
                align_blocks(current_parent, inst)
                queue.append(inst)

if __name__ == "__main__":
    solve_kinematics()

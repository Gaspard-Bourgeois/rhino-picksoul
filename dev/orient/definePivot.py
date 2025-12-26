import rhinoscriptsyntax as rs

# --- Inclure les fonctions utilitaires ici ---
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import json

def get_local_data(instance_id, world_pt, world_vec=None):
    """Convertit un point et un vecteur du monde vers l'espace local du bloc."""
    # Matrice de transformation du bloc (Monde vers Instance)
    xform = rs.BlockInstanceXform(instance_id)
    # On doit l'inverser pour passer de Monde à Local
    inverse_xform = xform.TryGetInverse()[1]
    
    local_pt = rg.Point3d(world_pt)
    local_pt.Transform(inverse_xform)
    
    local_vec = None
    if world_vec:
        local_vec = rg.Vector3d(world_vec)
        local_vec.Transform(inverse_xform)
        
    return [local_pt.X, local_pt.Y, local_pt.Z], ([local_vec.X, local_vec.Y, local_vec.Z] if world_vec else None)

def save_joint_data(obj_id, partner_id, joint_type, local_pt, local_vec):
    data = {
        "partner": str(partner_id),
        "type": joint_type,
        "origin": local_pt,
        "axis": local_vec
    }
    # On stocke en JSON dans les UserStrings pour la flexibilité
    rs.SetUserString(obj_id, "KinematicJoint", json.dumps(data))

def define_pivot():
    id_a = rs.GetObject("Sélectionnez le premier bloc", rs.filter.instance)
    id_b = rs.GetObject("Sélectionnez le second bloc", rs.filter.instance)
    if not id_a or not id_b: return

    origin = rs.GetPoint("Centre de rotation (Pivot)")
    axis_pt = rs.GetPoint("Point sur l'axe de rotation", origin)
    axis_vec = rs.VectorCreate(axis_pt, origin)

    # Calcul et stockage pour le bloc A
    loc_pt_a, loc_vec_a = get_local_data(id_a, origin, axis_vec)
    save_joint_data(id_a, id_b, "REVOLUTE", loc_pt_a, loc_vec_a)

    # Calcul et stockage pour le bloc B
    loc_pt_b, loc_vec_b = get_local_data(id_b, origin, axis_vec)
    save_joint_data(id_b, id_a, "REVOLUTE", loc_pt_b, loc_vec_b)
    
    print("Liaison Pivot enregistrée.")

if __name__ == "__main__":
    define_pivot()

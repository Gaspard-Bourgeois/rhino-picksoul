"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 05/01/26

Script calcul Centre de Gravité (COG)
Pondéré par la masse (Volume * Densité)
Insère un point au résultat.
"""
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import math

KEY_NAME = "VolumicMass"

def get_doc_unit_scale_to_meter():
    us = sc.doc.ModelUnitSystem
    return Rhino.RhinoMath.UnitScale(us, Rhino.UnitSystem.Meters)

def get_material_density_by_name_logic(mat_name):
    if not mat_name: return 0.0
    for mat in sc.doc.Materials:
        if mat.Name == mat_name:
            s_val = mat.GetUserString(KEY_NAME)
            if s_val:
                try: return float(s_val)
                except: pass
            break
    return 0.0

def get_obj_density(obj_id):
    mat_name = None
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index > -1:
        temp_mat = sc.doc.Materials[mat_index]
        if temp_mat: mat_name = temp_mat.Name
    
    if not mat_name:
        layer_name = rs.ObjectLayer(obj_id)
        layer_mat_index = rs.LayerMaterialIndex(layer_name)
        if layer_mat_index > -1:
            temp_mat = sc.doc.Materials[layer_mat_index]
            if temp_mat: mat_name = temp_mat.Name
            
    if not mat_name: return 0.0
    return get_material_density_by_name_logic(mat_name)

def calculate_moments_recursive(obj_id, xform, data_accum, scale_factor):
    """
    data_accum est une liste mutable [total_mass, moment_x, moment_y, moment_z]
    """
    if rs.IsBlockInstance(obj_id):
        inst_xform = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_name = rs.BlockInstanceName(obj_id)
        block_objs = rs.BlockObjects(block_name)
        if block_objs:
            for child in block_objs:
                calculate_moments_recursive(child, total_xform, data_accum, scale_factor)
        return
    
    if rs.IsPoint(obj_id):
        return
        
    if rs.IsPolysurfaceClosed(obj_id) or rs.IsSurfaceClosed(obj_id) or rs.IsMeshClosed(obj_id):
        rho = get_obj_density(obj_id)
        if rho <= 0: return 

        geo = rs.coercegeometry(obj_id)
        if not geo: return
        
        mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
        if not mp: return
        
        # Centroïde local de l'objet de définition
        centroid = mp.Centroid
        # Volume local
        raw_vol = mp.Volume
        
        # On transforme le centroïde vers l'espace Monde (selon le bloc)
        centroid.Transform(xform)
        
        # Calcul du volume réel (déterminant matrice)
        det = xform.Determinant
        final_vol_rhino = raw_vol * abs(det)
        
        # Masse (kg)
        vol_m3 = final_vol_rhino * math.pow(scale_factor, 3)
        mass = vol_m3 * rho
        
        # Accumulation
        # Moment = Masse * Position
        data_accum[0] += mass
        data_accum[1] += mass * centroid.X
        data_accum[2] += mass * centroid.Y
        data_accum[3] += mass * centroid.Z

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le Centre de Gravité", preselect=True)
    if not ids: return

    # [Masse, MomentX, MomentY, MomentZ]
    data = [0.0, 0.0, 0.0, 0.0]
    scale_to_meter = get_doc_unit_scale_to_meter()
    identity = Rhino.Geometry.Transform.Identity

    rs.EnableRedraw(False)
    for guid in ids:
        calculate_moments_recursive(guid, identity, data, scale_to_meter)
    rs.EnableRedraw(True)

    total_mass = data[0]

    if total_mass <= 0:
        # rs.MessageBox("Masse totale nulle ou matériaux non définis.", 48)
        print("Masse totale nulle ou matériaux non définis.")
        return

    # COG = Somme(Moments) / Masse Totale
    cog_x = data[1] / total_mass
    cog_y = data[2] / total_mass
    cog_z = data[3] / total_mass

    cog_pt = Rhino.Geometry.Point3d(cog_x, cog_y, cog_z)
    
    # Création du point dans Rhino
    pt_id = sc.doc.Objects.AddPoint(cog_pt)
    rs.ObjectName(pt_id, "COG_Result")
    rs.ObjectColor(pt_id, (255, 0, 0)) # Rouge
    rs.UnselectAllObjects()
    rs.SelectObject(pt_id)
    
    msg = "Masse totale considérée : {:.3f} kg\n".format(total_mass)
    msg += "1 point inséré\n"
    msg += "Centre de Gravité créé à :\n XYZ : {:.2f}, {:.2f}, {:.2f}".format(cog_x, cog_y, cog_z)
    # rs.MessageBox(msg, 64, "COG Calculé")
    print(str(msg))
    # print("Point inséré : {}".format(pt_id))

if __name__ == "__main__":
    main()

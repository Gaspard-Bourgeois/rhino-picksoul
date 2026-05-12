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
                try:
                    return float(s_val)
                except:
                    pass
            break
    return 0.0

def get_obj_density(obj_id):
    mat_name = None
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index > -1:
        temp_mat = sc.doc.Materials[mat_index]
        if temp_mat:
            mat_name = temp_mat.Name
    if not mat_name:
        layer_name = rs.ObjectLayer(obj_id)
        layer_mat_index = rs.LayerMaterialIndex(layer_name)
        if layer_mat_index > -1:
            temp_mat = sc.doc.Materials[layer_mat_index]
            if temp_mat:
                mat_name = temp_mat.Name
    if not mat_name:
        return 0.0, "Non Defini"
    density = get_material_density_by_name_logic(mat_name)
    return density, mat_name

def classify_object(obj_id):
    """
    Classifie un objet selon sa capacité à avoir un volume.
    Retourne (has_vol: bool, is_open: bool, type_label: str)
      - has_vol  : True  → solide fermé, calcul possible
      - is_open  : True  → géométrie ouverte, avertissement
      - type_label : None → ignoré silencieusement (courbe, point, etc.)
    """
    # --- Objets sans volume : ignorés silencieusement ---
    if rs.IsPoint(obj_id):      return False, False, None
    if rs.IsCurve(obj_id):      return False, False, None
    if rs.IsLight(obj_id):      return False, False, None
    if rs.IsTextDot(obj_id):    return False, False, None

    # Annotation via RhinoCommon (rs.IsAnnotation n'existe pas)
    rh_obj = sc.doc.Objects.FindId(obj_id)
    if rh_obj is None:          return False, False, None
    if isinstance(rh_obj, Rhino.DocObjects.AnnotationObjectBase):
        return False, False, None

    # --- Mesh ---
    if rs.IsMesh(obj_id):
        if rs.IsMeshClosed(obj_id):
            return True, False, "Solide (Mesh)"
        return False, True, "Mesh ouvert"

    # --- Brep : surface simple ou polysurface ---
    if rs.IsBrep(obj_id):
        geo = rs.coercebrep(obj_id)
        if geo is None:         return False, False, None
        if geo.IsSolid:
            return True, False, "Solide (Brep)"
        label = "Polysurface ouverte" if geo.Faces.Count > 1 else "Surface ouverte"
        return False, True, label

    # --- Extrusion native Rhino ---
    if isinstance(rh_obj.Geometry, Rhino.Geometry.Extrusion):
        geo = rh_obj.Geometry
        if geo.IsSolid():
            return True, False, "Solide (Extrusion)"
        return False, True, "Extrusion ouverte"

    # --- Tout autre type : ignoré silencieusement ---
    return False, False, None

def calculate_mass_recursive(obj_id, xform, stats_dict, warnings, scale_factor):
    # --- Bloc imbriqué ---
    if rs.IsBlockInstance(obj_id):
        inst_xform = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_name  = rs.BlockInstanceName(obj_id)
        block_objs  = rs.BlockObjects(block_name)
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, warnings, scale_factor)
        return

    # --- Classification ---
    has_vol, is_open, type_label = classify_object(obj_id)

    if is_open:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — masse non calculable (géométrie ouverte)".format(
            type_label, obj_name))
        return

    if not has_vol:
        return  # Ignoré silencieusement

    # --- Densité ---
    rho, mat_name = get_obj_density(obj_id)
    if rho <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — ignoré (aucune densité pour \"{}\")".format(
            type_label, obj_name, mat_name))
        return

    # --- Volume ---
    geo = rs.coercegeometry(obj_id)
    if geo is None:
        warnings.append("  • Impossible de lire la géométrie de {}".format(obj_id))
        return

    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if mp is None:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — calcul du volume échoué".format(type_label, obj_name))
        return

    raw_vol = mp.Volume
    if raw_vol <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — volume nul ou négatif, ignoré".format(type_label, obj_name))
        return

    det    = xform.Determinant
    vol_m3 = raw_vol * abs(det) * math.pow(scale_factor, 3)
    mass   = vol_m3 * rho

    stats_dict[mat_name] = stats_dict.get(mat_name, 0.0) + mass

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    stats          = {}
    warnings       = []
    scale_to_meter = get_doc_unit_scale_to_meter()

    print("Calcul en cours...")
    rs.EnableRedraw(False)
    identity = Rhino.Geometry.Transform.Identity

    for guid in ids:
        calculate_mass_recursive(guid, identity, stats, warnings, scale_to_meter)

    rs.EnableRedraw(True)

    # --- Construction du message ---
    msg = ""
    if stats:
        total_mass = sum(stats.values())
        msg += "MASSE TOTALE : {:.3f} kg\n".format(total_mass)
        msg += "-" * 10 + " Par matériau " + "-" * 10 + "\n"
        for name, mass in sorted(stats.items()):
            msg += "  {}: {:.3f} kg\n".format(name, mass)
    else:
        msg += "Aucun objet valide avec un matériau défini n'a été trouvé.\n"

    if warnings:
        msg += "\n⚠ Avertissements ({}) :\n".format(len(warnings))
        msg += "\n".join(warnings)

    print(msg)
    if warnings or not stats:
        rs.MessageBox(msg, 48 if not stats else 64, "Résultats Masse")

if __name__ == "__main__":
    main()
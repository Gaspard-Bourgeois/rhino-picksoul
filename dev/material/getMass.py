import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import math

KEY_NAME = "VolumicMass"

# Types sans volume — ignorés silencieusement
_SILENT_IGNORE_TYPES = frozenset([
    Rhino.DocObjects.ObjectType.Point,
    Rhino.DocObjects.ObjectType.PointSet,
    Rhino.DocObjects.ObjectType.Curve,
    Rhino.DocObjects.ObjectType.Annotation,
    Rhino.DocObjects.ObjectType.Light,
    Rhino.DocObjects.ObjectType.TextDot,
    Rhino.DocObjects.ObjectType.Grip,
    Rhino.DocObjects.ObjectType.Phantom,
    Rhino.DocObjects.ObjectType.ClipPlane,
])

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
        if temp_mat: mat_name = temp_mat.Name
    if not mat_name:
        layer_name = rs.ObjectLayer(obj_id)
        layer_mat_index = rs.LayerMaterialIndex(layer_name)
        if layer_mat_index > -1:
            temp_mat = sc.doc.Materials[layer_mat_index]
            if temp_mat: mat_name = temp_mat.Name
    if not mat_name:
        return 0.0, "Non Defini"
    density = get_material_density_by_name_logic(mat_name)
    return density, mat_name

def has_volume(obj_id):
    """
    Retourne (has_vol: bool, is_open: bool, type_label: str)
    Via un unique appel rs.ObjectType() pour minimiser les aller-retours COM.
    """
    obj_type = rs.ObjectType(obj_id)

    # --- Ignorés silencieusement ---
    if obj_type in _SILENT_IGNORE_TYPES:
        return False, False, None

    # --- Surfaces / Polysurfaces ---
    if obj_type == Rhino.DocObjects.ObjectType.Brep:
        geo = rs.coercegeometry(obj_id)
        if geo is None:
            return False, False, None
        if geo.IsSolid:
            return True, False, "Solide (Brep)"
        # Distinguer surface simple et polysurface pour le message
        label = "Polysurface ouverte" if geo.Faces.Count > 1 else "Surface ouverte"
        return False, True, label

    # --- Mesh ---
    if obj_type == Rhino.DocObjects.ObjectType.Mesh:
        geo = rs.coercegeometry(obj_id)
        if geo is None:
            return False, False, None
        if geo.IsClosed:
            return True, False, "Solide (Mesh)"
        return False, True, "Mesh ouvert"

    # --- Extrusion (type natif Rhino) ---
    if obj_type == Rhino.DocObjects.ObjectType.Extrusion:
        geo = rs.coercegeometry(obj_id)
        if geo is None:
            return False, False, None
        if geo.IsSolid():
            return True, False, "Solide (Extrusion)"
        return False, True, "Extrusion ouverte"

    # --- Bloc : traité en amont, ne devrait pas arriver ici ---
    if obj_type == Rhino.DocObjects.ObjectType.InstanceReference:
        return False, False, None

    # --- Tout autre type non géré ---
    return False, False, None

def calculate_mass_recursive(obj_id, xform, stats_dict, warnings, scale_factor):
    # --- Bloc imbriqué ---
    if rs.IsBlockInstance(obj_id):
        inst_xform = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_name = rs.BlockInstanceName(obj_id)
        block_objs = rs.BlockObjects(block_name)
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, warnings, scale_factor)
        return

    # --- Vérification du type ---
    has_vol, is_open, type_label = has_volume(obj_id)

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

    # --- Géométrie déjà chargée dans has_volume, on la recharge (coerce est mis en cache par Rhino) ---
    geo = rs.coercegeometry(obj_id)
    if not geo:
        warnings.append("  • Impossible de lire la géométrie de {}".format(obj_id))
        return

    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if not mp:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — calcul du volume échoué".format(type_label, obj_name))
        return

    raw_vol = mp.Volume
    if raw_vol <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — volume nul ou négatif, ignoré".format(type_label, obj_name))
        return

    det = xform.Determinant
    vol_m3 = raw_vol * abs(det) * math.pow(scale_factor, 3)
    mass = vol_m3 * rho

    stats_dict[mat_name] = stats_dict.get(mat_name, 0.0) + mass

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    stats    = {}
    warnings = []
    scale_to_meter = get_doc_unit_scale_to_meter()

    print("Calcul en cours...")
    rs.EnableRedraw(False)
    identity = Rhino.Geometry.Transform.Identity

    for guid in ids:
        calculate_mass_recursive(guid, identity, stats, warnings, scale_to_meter)

    rs.EnableRedraw(True)

    # --- Résultats ---
    msg = ""
    if stats:
        total_mass = sum(stats.values())
        msg += "MASSE TOTALE : {:.3f} kg\n".format(total_mass)
        msg += "-" * 10 + " Par matériau " + "-" * 10 + "\n"
        for name, mass in sorted(stats.items()):
            msg += "  {}: {:.3f} kg\n".format(name, mass)
    else:
        msg += "Aucun objet valide avec matériau défini trouvé.\n"

    if warnings:
        msg += "\n⚠ Avertissements ({}) :\n".format(len(warnings))
        msg += "\n".join(warnings)

    print(msg)
    if warnings or not stats:
        rs.MessageBox(msg, 48 if not stats else 64, "Résultats Masse")

if __name__ == "__main__":
    main()
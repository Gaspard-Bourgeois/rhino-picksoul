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
    Vérifie si un objet est susceptible d'avoir un volume calculable.
    Retourne (bool_has_volume, is_open_polysurface, type_label)
    """
    # Objets sans volume → ignorer silencieusement
    if rs.IsPoint(obj_id):        return False, False, "Point"
    if rs.IsCurve(obj_id):        return False, False, "Courbe"
    if rs.IsAnnotation(obj_id):   return False, False, "Annotation"
    if rs.IsLight(obj_id):        return False, False, "Lumière"
    if rs.IsTextDot(obj_id):      return False, False, "TextDot"
    if rs.IsGroup(obj_id):        return False, False, "Groupe"

    # Polysurface ouverte → signaler, pas de calcul possible
    if rs.IsPolysurface(obj_id) and not rs.IsPolysurfaceClosed(obj_id):
        return False, True, "Polysurface ouverte"

    # Surface ouverte → signaler aussi
    if rs.IsSurface(obj_id) and not rs.IsSurfaceClosed(obj_id):
        return False, True, "Surface ouverte"

    # Mesh ouvert → signaler
    if rs.IsMesh(obj_id) and not rs.IsMeshClosed(obj_id):
        return False, True, "Mesh ouvert"

    # Géométries valides pour le volume
    if (rs.IsPolysurfaceClosed(obj_id) or
        rs.IsSurfaceClosed(obj_id) or
        rs.IsMeshClosed(obj_id)):
        return True, False, "Solide"

    # Cas non identifié → ignorer silencieusement
    return False, False, "Type inconnu"

def calculate_mass_recursive(obj_id, xform, stats_dict, warnings, scale_factor):
    """
    Parcourt récursivement les objets et blocs.
    warnings : liste des avertissements à afficher en fin de script
    """
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
        # On signale mais on n'arrête pas le traitement global
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] {} — masse non calculable (géométrie ouverte)".format(
            type_label, obj_name))
        return

    if not has_vol:
        return  # Ignoré silencieusement (courbes, points, etc.)

    # --- Calcul du volume ---
    rho, mat_name = get_obj_density(obj_id)
    if rho <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] {} — ignoré (aucune densité définie pour \"{}\")".format(
            type_label, obj_name, mat_name))
        return

    geo = rs.coercegeometry(obj_id)
    if not geo:
        warnings.append("  • Impossible de lire la géométrie de l'objet {}".format(obj_id))
        return

    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if not mp:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] {} — calcul du volume échoué".format(type_label, obj_name))
        return

    raw_vol = mp.Volume
    if raw_vol <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] {} — volume nul ou négatif, ignoré".format(type_label, obj_name))
        return

    det = xform.Determinant
    final_vol_rhino_units = raw_vol * abs(det)
    vol_m3 = final_vol_rhino_units * math.pow(scale_factor, 3)
    mass = vol_m3 * rho

    if mat_name not in stats_dict:
        stats_dict[mat_name] = 0.0
    stats_dict[mat_name] += mass

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    stats = {}
    warnings = []
    scale_to_meter = get_doc_unit_scale_to_meter()

    print("Calcul en cours...")
    rs.EnableRedraw(False)

    identity = Rhino.Geometry.Transform.Identity

    for guid in ids:
        calculate_mass_recursive(guid, identity, stats, warnings, scale_to_meter)

    rs.EnableRedraw(True)

    # --- Affichage des résultats ---
    msg = ""

    if stats:
        total_mass = sum(stats.values())
        msg += "MASSE TOTALE : {:.3f} kg\n".format(total_mass)
        msg += "-" * 10 + " Par matériau " + "-" * 10 + "\n"
        for name, mass in stats.items():
            msg += "  {}: {:.3f} kg\n".format(name, mass)
    else:
        msg += "Aucun objet valide avec un matériau défini n'a été trouvé.\n"

    if warnings:
        msg += "\n⚠ Avertissements ({}) :\n".format(len(warnings))
        msg += "\n".join(warnings)

    print(msg)

    # Affiche une boîte de dialogue seulement s'il y a des avertissements
    # ou si aucun résultat n'a été trouvé
    if warnings or not stats:
        icon = 48 if not stats else 64
        rs.MessageBox(msg, icon, "Résultats Masse")

if __name__ == "__main__":
    main()
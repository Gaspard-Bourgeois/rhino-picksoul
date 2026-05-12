import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import math

KEY_NAME = "VolumicMass"

# ─────────────────────────────────────────────
# Utilitaires document
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# Calcul de volume avec fallback mesh
# ─────────────────────────────────────────────

def compute_volume(geo, type_label, obj_name, warnings):
    """
    Tente de calculer le volume d'une géométrie.
    Stratégie 1 : VolumeMassProperties natif (rapide).
    Stratégie 2 : tessélation en mesh (fallback si stratégie 1 échoue).
    Retourne le volume brut (unités Rhino) ou None en cas d'échec total.
    """
    # ── Stratégie 1 : calcul natif ──
    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if mp is not None and mp.Volume > 0:
        return mp.Volume

    # ── Stratégie 2 : fallback mesh ──
    # Applicable uniquement aux Brep (Polysurface / Surface)
    brep = None
    if isinstance(geo, Rhino.Geometry.Brep):
        brep = geo
    elif isinstance(geo, Rhino.Geometry.Extrusion):
        brep = geo.ToBrep(True)

    if brep is not None:
        mesh_params = Rhino.Geometry.MeshingParameters.FastRenderMesh
        meshes = Rhino.Geometry.Mesh.CreateFromBrep(brep, mesh_params)
        if meshes:
            joined = Rhino.Geometry.Mesh()
            for m in meshes:
                joined.Append(m)
            joined.Weld(math.pi)
            joined.RebuildNormals()
            mp2 = Rhino.Geometry.VolumeMassProperties.Compute(joined)
            if mp2 is not None and mp2.Volume > 0:
                warnings.append(
                    "  • [{}] \"{}\" — volume calculé par tessélation mesh (fallback)".format(
                        type_label, obj_name))
                return mp2.Volume

    warnings.append(
        "  • [{}] \"{}\" — calcul du volume échoué (natif + fallback mesh)".format(
            type_label, obj_name))
    return None

# ─────────────────────────────────────────────
# Classification
# ─────────────────────────────────────────────

def classify_object(obj_id):
    """
    Retourne (has_vol: bool, is_open: bool, type_label: str|None, geo)
    geo est déjà chargé ici pour éviter un second appel coerce plus bas.
    """
    # Objets sans volume — ignorés silencieusement
    if rs.IsPoint(obj_id):   return False, False, None, None
    if rs.IsCurve(obj_id):   return False, False, None, None
    if rs.IsLight(obj_id):   return False, False, None, None
    if rs.IsTextDot(obj_id): return False, False, None, None

    # Annotation (pas de rs.IsAnnotation)
    rh_obj = sc.doc.Objects.FindId(obj_id)
    if rh_obj is None: return False, False, None, None
    if isinstance(rh_obj, Rhino.DocObjects.AnnotationObjectBase):
        return False, False, None, None

    # ── Mesh ──
    if rs.IsMesh(obj_id):
        geo = rh_obj.Geometry
        if geo is None: return False, False, None, None
        if geo.IsClosed:
            return True, False, "Solide (Mesh)", geo
        return False, True, "Mesh ouvert", None

    # ── Brep (surface simple ou polysurface) ──
    if rs.IsBrep(obj_id):
        geo = rh_obj.Geometry
        if geo is None: return False, False, None, None
        if geo.IsSolid:
            label = "Polysurface" if geo.Faces.Count > 1 else "Surface"
            return True, False, label, geo
        label = "Polysurface ouverte" if geo.Faces.Count > 1 else "Surface ouverte"
        return False, True, label, None

    # ── Extrusion native ──
    if isinstance(rh_obj.Geometry, Rhino.Geometry.Extrusion):
        geo = rh_obj.Geometry
        if geo.IsSolid():
            return True, False, "Solide (Extrusion)", geo
        return False, True, "Extrusion ouverte", None

    return False, False, None, None

# ─────────────────────────────────────────────
# Récursion blocs + calcul masse
# ─────────────────────────────────────────────

def calculate_mass_recursive(obj_id, xform, stats_dict, warnings, scale_factor):

    # ── Bloc imbriqué ──
    if rs.IsBlockInstance(obj_id):
        inst_xform  = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_name  = rs.BlockInstanceName(obj_id)
        block_objs  = rs.BlockObjects(block_name)
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, warnings, scale_factor)
        return

    # ── Classification ──
    has_vol, is_open, type_label, geo = classify_object(obj_id)

    if is_open:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — masse non calculable (géométrie ouverte)".format(
            type_label, obj_name))
        return

    if not has_vol:
        return  # Ignoré silencieusement

    # ── Densité ──
    rho, mat_name = get_obj_density(obj_id)
    if rho <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — ignoré (aucune densité pour \"{}\")".format(
            type_label, obj_name, mat_name))
        return

    # ── Volume ──
    obj_name = rs.ObjectName(obj_id) or str(obj_id)
    raw_vol  = compute_volume(geo, type_label, obj_name, warnings)
    if raw_vol is None:
        return

    det    = xform.Determinant
    vol_m3 = raw_vol * abs(det) * math.pow(scale_factor, 3)
    mass   = vol_m3 * rho

    stats_dict[mat_name] = stats_dict.get(mat_name, 0.0) + mass

# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

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

    # ── Message de résultat ──
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
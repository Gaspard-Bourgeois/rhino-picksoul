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
        return 0.0
    return get_material_density_by_name_logic(mat_name)

# ─────────────────────────────────────────────
# Classification
# ─────────────────────────────────────────────

def classify_object(obj_id):
    """
    Retourne (has_vol: bool, is_open: bool, type_label: str|None, geo)
    geo est déjà chargé ici pour éviter un second appel coerce plus bas.
    """
    if rs.IsPoint(obj_id):   return False, False, None, None
    if rs.IsCurve(obj_id):   return False, False, None, None
    if rs.IsLight(obj_id):   return False, False, None, None
    if rs.IsTextDot(obj_id): return False, False, None, None

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

    # ── Brep ──
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
# Calcul de volume + centroïde avec fallback mesh
# ─────────────────────────────────────────────

def compute_volume_and_centroid(geo, type_label, obj_name, warnings):
    """
    Retourne (volume: float, centroid: Point3d) ou (None, None) en cas d'échec.
    Stratégie 1 : VolumeMassProperties natif.
    Stratégie 2 : tessélation mesh (fallback).
    """
    # ── Stratégie 1 ──
    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if mp is not None and mp.Volume > 0:
        return mp.Volume, mp.Centroid

    # ── Stratégie 2 : fallback mesh ──
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
                    "  • [{}] \"{}\" — centroïde calculé par tessélation mesh (fallback)".format(
                        type_label, obj_name))
                return mp2.Volume, mp2.Centroid

    warnings.append(
        "  • [{}] \"{}\" — calcul du volume/centroïde échoué (natif + fallback mesh)".format(
            type_label, obj_name))
    return None, None

# ─────────────────────────────────────────────
# Récursion blocs + accumulation moments
# ─────────────────────────────────────────────

def calculate_moments_recursive(obj_id, xform, data_accum, warnings, scale_factor):
    """
    data_accum : liste mutable [total_mass, moment_x, moment_y, moment_z]
    """
    # ── Bloc imbriqué ──
    if rs.IsBlockInstance(obj_id):
        inst_xform  = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_name  = rs.BlockInstanceName(obj_id)
        block_objs  = rs.BlockObjects(block_name)
        if block_objs:
            for child in block_objs:
                calculate_moments_recursive(child, total_xform, data_accum, warnings, scale_factor)
        return

    # ── Classification ──
    has_vol, is_open, type_label, geo = classify_object(obj_id)

    if is_open:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — ignoré (géométrie ouverte)".format(
            type_label, obj_name))
        return

    if not has_vol:
        return  # Ignoré silencieusement

    # ── Densité ──
    rho = get_obj_density(obj_id)
    if rho <= 0:
        obj_name = rs.ObjectName(obj_id) or str(obj_id)
        warnings.append("  • [{}] \"{}\" — ignoré (aucune densité définie)".format(
            type_label, obj_name))
        return

    # ── Volume + centroïde ──
    obj_name = rs.ObjectName(obj_id) or str(obj_id)
    raw_vol, centroid = compute_volume_and_centroid(geo, type_label, obj_name, warnings)
    if raw_vol is None:
        return

    # Transformation du centroïde vers l'espace monde (blocs imbriqués)
    centroid.Transform(xform)

    det           = xform.Determinant
    vol_m3        = raw_vol * abs(det) * math.pow(scale_factor, 3)
    mass          = vol_m3 * rho

    data_accum[0] += mass
    data_accum[1] += mass * centroid.X
    data_accum[2] += mass * centroid.Y
    data_accum[3] += mass * centroid.Z

# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le Centre de Gravité", preselect=True)
    if not ids: return

    data           = [0.0, 0.0, 0.0, 0.0]  # [masse, Mx, My, Mz]
    warnings       = []
    scale_to_meter = get_doc_unit_scale_to_meter()
    identity       = Rhino.Geometry.Transform.Identity

    rs.EnableRedraw(False)
    for guid in ids:
        calculate_moments_recursive(guid, identity, data, warnings, scale_to_meter)
    rs.EnableRedraw(True)

    total_mass = data[0]

    # ── Avertissements ──
    if warnings:
        warn_msg = "⚠ Avertissements ({}) :\n".format(len(warnings))
        warn_msg += "\n".join(warnings)
        print(warn_msg)

    if total_mass <= 0:
        msg = "Masse totale nulle ou matériaux non définis."
        if warnings:
            msg += "\n\n" + warn_msg
        print(msg)
        rs.MessageBox(msg, 48, "COG — Erreur")
        return

    # ── Calcul COG ──
    cog_x = data[1] / total_mass
    cog_y = data[2] / total_mass
    cog_z = data[3] / total_mass
    cog_pt = Rhino.Geometry.Point3d(cog_x, cog_y, cog_z)

    # ── Insertion du point ──
    pt_id = sc.doc.Objects.AddPoint(cog_pt)
    rs.ObjectName(pt_id, "COG_Result")
    rs.ObjectColor(pt_id, (255, 0, 0))
    rs.UnselectAllObjects()
    rs.SelectObject(pt_id)
    sc.doc.Views.Redraw()

    # ── Résultat ──
    msg  = "Masse totale considérée : {:.3f} kg\n".format(total_mass)
    msg += "Centre de Gravité :\n"
    msg += "  X : {:.4f}\n  Y : {:.4f}\n  Z : {:.4f}\n".format(cog_x, cog_y, cog_z)
    if warnings:
        msg += "\n⚠ Avertissements ({}) :\n".format(len(warnings))
        msg += "\n".join(warnings)

    print(msg)
    rs.MessageBox(msg, 64, "COG Calculé")

if __name__ == "__main__":
    main()
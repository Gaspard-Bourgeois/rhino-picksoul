# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import math

KEY_NAME = "VolumicMass"
DENSITY_CACHE = {}

def get_material_density_cached(mat_name):
    if not mat_name or mat_name == "Non Defini": return 0.0
    if mat_name in DENSITY_CACHE: return DENSITY_CACHE[mat_name]
    
    density = 0.0
    for mat in sc.doc.Materials:
        if mat.Name == mat_name:
            s_val = mat.GetUserString(KEY_NAME)
            try: density = float(s_val) if s_val else 0.0
            except: density = 0.0
            break
    DENSITY_CACHE[mat_name] = density
    return density

def get_obj_info(obj_id):
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index == -1:
        layer_name = rs.ObjectLayer(obj_id)
        mat_index = rs.LayerMaterialIndex(layer_name)
    
    if mat_index > -1:
        mat = sc.doc.Materials[mat_index]
        if mat:
            name = mat.Name
            return name, get_material_density_cached(name)
    return "Non Defini", 0.0

def calculate_mass_recursive(obj_id, xform, stats_dict, scale_factor, errors, root_guid):
    otype = rs.ObjectType(obj_id)
    
    # 1. Gestion des blocs
    if otype == 4096: 
        inst_xform = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_objs = rs.BlockObjects(rs.BlockInstanceName(obj_id))
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, scale_factor, errors, root_guid)
        return

    # 2. Ignorer ce qui n'a pas de volume potentiel (courbes, points, etc.)
    # 8=Srf, 16=PolySrf, 32=Mesh, 1073741824=Extrusion
    if otype not in [8, 16, 32, 1073741824]: return

    # 3. Vérification si l'objet est "Solide" (Fermé)
    # Correction : rs.IsObjectSolid est plus fiable que l'accès direct à l'attribut .IsClosed
    if not rs.IsObjectSolid(obj_id):
        errors["open_objects"].add(root_guid)
        return

    # 4. Test Matériau et Densité
    mat_name, rho = get_obj_info(obj_id)
    if mat_name == "Non Defini":
        errors["no_material"].add(root_guid)
        return
    if rho <= 0:
        errors["no_density"].add(root_guid)
        return

    # 5. Calcul du volume via RhinoCommon
    geo = rs.coercegeometry(obj_id)
    if not geo: return
    
    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if mp:
        # Volume corrigé par l'échelle du bloc (déterminant)
        vol = mp.Volume * abs(xform.Determinant)
        # Conversion unités Rhino -> Mètres cubes puis x Densité
        mass = (vol * math.pow(scale_factor, 3)) * rho
        stats_dict[mat_name] = stats_dict.get(mat_name, 0.0) + mass
    else:
        errors["calc_failed"].add(root_guid)

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    DENSITY_CACHE.clear()
    stats = {}
    errors = {
        "open_objects": set(), 
        "no_material": set(),  
        "no_density": set(),   
        "calc_failed": set()
    }
    
    scale_to_meter = Rhino.RhinoMath.UnitScale(sc.doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    
    rs.EnableRedraw(False)
    identity = Rhino.Geometry.Transform.Identity
    for guid in ids:
        calculate_mass_recursive(guid, identity, stats, scale_to_meter, errors, guid)
    rs.EnableRedraw(True)

    # --- AFFICHAGE DES RÉSULTATS ---
    print("\n" + "="*40)
    print(" BILAN DU CALCUL DE MASSE")
    print("="*40)
    
    if stats:
        for name, mass in sorted(stats.items()):
            print(" • {}: {:.3f} kg".format(name.ljust(20), mass))
        print("-" * 40)
        print(" TOTAL : {:.3f} kg".format(sum(stats.values())))
    else:
        print(" Aucun objet valide trouvé.")

    # --- GESTION DES ERREURS ---
    err_lists = {
        "Objets OUVERTS (Masse non calculable)": list(errors["open_objects"]),
        "Objets SANS MATÉRIAU": list(errors["no_material"]),
        "MATÉRIAUX sans densité (VolumicMass)": list(errors["no_density"]),
        "ÉCHECS de calcul géométrique": list(errors["calc_failed"])
    }

    available_fixes = [k for k, v in err_lists.items() if len(v) > 0]

    if available_fixes:
        print("\n" + "!"*10 + " ALERTES " + "!"*10)
        for key in available_fixes:
            print(" [!] {} : {} objet(s)".format(key, len(err_lists[key])))
        
        choice = rs.ListBox(available_fixes, 
                           "Certains objets ont été ignorés.\nSélectionner les objets problématiques ?", 
                           "Correcteur de masse")
        
        if choice:
            rs.UnselectAllObjects()
            rs.SelectObjects(err_lists[choice])
            print("\n>>> Objets sélectionnés : " + choice)

if __name__ == "__main__":
    main()

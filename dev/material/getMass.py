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
    """
    root_guid : l'ID de l'objet sélectionné au départ (utile pour sélectionner 
                le bloc entier si une erreur est à l'intérieur).
    """
    otype = rs.ObjectType(obj_id)
    
    if otype == 4096: # Bloc
        inst_xform = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_objs = rs.BlockObjects(rs.BlockInstanceName(obj_id))
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, scale_factor, errors, root_guid)
        return

    if otype not in [8, 16, 32, 1073741824]: return

    # --- 1. TEST MATÉRIAU ---
    mat_name, rho = get_obj_info(obj_id)
    if mat_name == "Non Defini":
        errors["no_material"].add(root_guid)
        return
    if rho <= 0:
        errors["no_density"].add(root_guid)
        return

    # --- 2. TEST GÉOMÉTRIE ---
    geo = rs.coercegeometry(obj_id)
    if not geo: return
    if not geo.IsClosed:
        errors["open_objects"].add(root_guid)
        return

    # --- 3. CALCUL ---
    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if mp:
        vol = mp.Volume * abs(xform.Determinant)
        mass = (vol * math.pow(scale_factor, 3)) * rho
        stats_dict[mat_name] = stats_dict.get(mat_name, 0.0) + mass
    else:
        errors["calc_failed"].add(root_guid)

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    DENSITY_CACHE.clear()
    stats = {}
    # On utilise des 'set' pour éviter les doublons d'IDs
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

    # --- RAPPORT CONSOLE ---
    print("\n" + "="*40)
    print(" BILAN DU CALCUL")
    print("="*40)
    if stats:
        for name, mass in stats.items():
            print(" • {}: {:.3f} kg".format(name.ljust(20), mass))
        print("-" * 40)
        print(" TOTAL : {:.3f} kg".format(sum(stats.values())))
    else:
        print(" Aucun objet valide pour le calcul.")

    # --- GESTION DES ERREURS ET SÉLECTION ---
    err_lists = {
        "Objets OUVERTS (Volume impossible)": list(errors["open_objects"]),
        "Objets SANS MATÉRIAU": list(errors["no_material"]),
        "MATÉRIAUX sans densité (VolumicMass)": list(errors["no_density"]),
        "ÉCHECS de calcul géométrique": list(errors["calc_failed"])
    }

    # Filtrer uniquement les catégories qui ont des erreurs
    available_fixes = [k for k, v in err_lists.items() if len(v) > 0]

    if available_fixes:
        print("\n" + "!"*10 + " ERREURS DÉTECTÉES " + "!"*10)
        for key in available_fixes:
            print(" [!] {} : {} objet(s)".format(key, len(err_lists[key])))
        
        # Menu interactif pour l'utilisateur
        choice = rs.ListBox(available_fixes, 
                           "Des erreurs empêchent le calcul complet.\nChoisissez une catégorie à sélectionner :", 
                           "Correcteur de Masse")
        
        if choice:
            rs.UnselectAllObjects()
            rs.SelectObjects(err_lists[choice])
            print("\n>>> {} objets de type '{}' ont été sélectionnés.".format(len(err_lists[choice]), choice))

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
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

def calculate_mass_recursive(obj_id, xform, stats_dict, scale_factor, errors):
    """
    errors: dictionnaire pour stocker les types de problèmes rencontrés
    """
    
    # 1. Traitement des blocs
    if rs.IsBlockInstance(obj_id):
        inst_xform = rs.BlockInstanceXform(obj_id)
        total_xform = xform * inst_xform
        block_name = rs.BlockInstanceName(obj_id)
        block_objs = rs.BlockObjects(block_name)
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, scale_factor, errors)
        return

    # 2. Filtrage des types d'objets (ignorer courbes, points, texte...)
    # Types Rhino : 8=Surface, 16=Polysurface, 32=Mesh, 1073741824=Extrusion
    obj_type = rs.ObjectType(obj_id)
    valid_types = [8, 16, 32, 1073741824]
    
    if obj_type not in valid_types:
        return # On ignore silencieusement (courbes, points, etc.)

    # 3. Vérification si l'objet est fermé
    is_closed = False
    if rs.IsPolysurface(obj_id): is_closed = rs.IsPolysurfaceClosed(obj_id)
    elif rs.IsMesh(obj_id): is_closed = rs.IsMeshClosed(obj_id)
    elif rs.IsSurface(obj_id): is_closed = rs.IsSurfaceClosed(obj_id)
    
    if not is_closed:
        obj_name = rs.ObjectName(obj_id) or "Objet sans nom"
        errors["open_objects"].append("{} ({})".format(obj_name, obj_id))
        return

    # 4. Récupération densité
    rho, mat_name = get_obj_density(obj_id)
    
    if mat_name == "Non Defini":
        errors["no_material"].append(str(obj_id))
        return
    if rho <= 0:
        errors["no_density"].append(mat_name)
        return

    # 5. Calcul du volume
    geo = rs.coercegeometry(obj_id)
    if not geo: return
    
    mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
    if not mp: 
        errors["calc_failed"].append(str(obj_id))
        return
    
    # Prise en compte du scale du bloc via le déterminant
    det = xform.Determinant
    final_vol_rhino_units = mp.Volume * abs(det)
    
    # Conversion Mètre cube
    vol_m3 = final_vol_rhino_units * math.pow(scale_factor, 3)
    mass = vol_m3 * rho

    if mat_name not in stats_dict:
        stats_dict[mat_name] = 0.0
    stats_dict[mat_name] += mass

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    stats = {}
    errors = {
        "open_objects": [], # Polysurfaces ouvertes
        "no_material": [],  # Aucun matériau assigné
        "no_density": [],   # Matériau trouvé mais densité = 0 ou manquante
        "calc_failed": []   # Erreur géométrique rare
    }
    
    scale_to_meter = get_doc_unit_scale_to_meter()
    
    print("Calcul de masse en cours...")
    rs.EnableRedraw(False)
    
    identity = Rhino.Geometry.Transform.Identity
    for guid in ids:
        calculate_mass_recursive(guid, identity, stats, scale_to_meter, errors)
        
    rs.EnableRedraw(True)

    # --- AFFICHAGE DES RÉSULTATS ---
    
    output = []
    output.append("="*30)
    output.append(" RÉSULTATS DU CALCUL DE MASSE")
    output.append("="*30)

    if stats:
        total_mass = sum(stats.values())
        for name, mass in stats.items():
            output.append("- {}: {:.3f} kg".format(name.ljust(15), mass))
        output.append("-" * 30)
        output.append("MASSE TOTALE : {:.3f} kg".format(total_mass))
    else:
        output.append("Aucune masse calculée.")

    # --- SECTION ALERTES ---
    if errors["open_objects"] or errors["no_material"] or errors["no_density"]:
        output.append("\n" + "!"*10 + " ALERTES / OBJETS IGNORÉS " + "!"*10)
        
        if errors["open_objects"]:
            output.append("\n[!] OBJETS OUVERTS (Masse impossible à calculer) :")
            for item in errors["open_objects"][:10]: # Limite à 10 pour la lisibilité
                output.append("  • " + item)
            if len(errors["open_objects"]) > 10: output.append("  ... et {} autres.".format(len(errors["open_objects"])-10))

        if errors["no_material"]:
            output.append("\n[?] SANS MATÉRIAU (Objet ou Calque) :")
            output.append("  • {} objet(s) ignoré(s)".format(len(errors["no_material"])))

        if errors["no_density"]:
            output.append("\n[i] DENSITÉ NON DÉFINIE (UserString 'VolumicMass' manquant) :")
            unique_mats = list(set(errors["no_density"]))
            for m in unique_mats:
                output.append("  • Matériau : " + m)

    full_msg = "\n".join(output)
    print(full_msg)
    
    # Optionnel : Afficher un résumé simple en boite de dialogue si succès
    if stats:
        rs.MessageBox("Calcul terminé. Masse totale : {:.2f} kg. \nVoir la console pour le détail des erreurs.".format(total_mass), 64)

if __name__ == "__main__":
    main()

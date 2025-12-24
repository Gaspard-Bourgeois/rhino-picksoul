# -*- coding: utf-8 -*-
"""
Script calcul Masse Totale + Sous-totaux par matériau
Compatible avec la structure de données 'VolumicMass' (kg/m3)
Gère les blocs et les unités du document.
"""
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import math

KEY_NAME = "VolumicMass"

def get_doc_unit_scale_to_meter():
    """
    Renvoie le facteur pour convertir l'unité du fichier vers le Mètre.
    Ex: si fichier en mm, renvoie 0.001
    """
    us = sc.doc.ModelUnitSystem
    return Rhino.RhinoMath.UnitScale(us, Rhino.UnitSystem.Meters)

def get_material_density_by_name_logic(mat_name):
    """
    Retrouve la densité en cherchant le PREMIER matériau portant ce nom,
    pour rester cohérent avec le script d'entrée.
    """
    if not mat_name: return 0.0
    
    # On cherche le premier matériau qui porte ce nom dans la table
    for mat in sc.doc.Materials:
        if mat.Name == mat_name:
            s_val = mat.GetUserString(KEY_NAME)
            if s_val:
                try:
                    return float(s_val)
                except:
                    pass
            break # On arrête au premier trouvé comme dans le script d'entrée
    return 0.0

def get_obj_density(obj_id):
    """
    Récupère la densité (kg/m3) et le nom du matériau d'un objet
    en vérifiant Objet > Calque.
    """
    mat_name = None
    
    # 1. Matériau de l'objet
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index > -1:
        temp_mat = sc.doc.Materials[mat_index]
        if temp_mat: mat_name = temp_mat.Name
    
    # 2. Sinon Matériau du calque
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

def calculate_mass_recursive(obj_id, xform, stats_dict, scale_factor):
    """
    Parcourt récursivement les objets et blocs.
    xform : matrice de transformation accumulée (pour les blocs imbriqués)
    scale_factor : conversion unité rhino vers mètre
    """
    # Si c'est un bloc
    if rs.IsBlockInstance(obj_id):
        # Matrice de l'instance
        inst_xform = rs.BlockInstanceXform(obj_id)
        # Combinaison avec la transformation parente
        total_xform = xform * inst_xform
        
        block_name = rs.BlockInstanceName(obj_id)
        block_objs = rs.BlockObjects(block_name)
        
        if block_objs:
            for child in block_objs:
                calculate_mass_recursive(child, total_xform, stats_dict, scale_factor)
        return

    # Si c'est une géométrie valide pour le volume
    if rs.IsPolysurfaceClosed(obj_id) or rs.IsSurfaceClosed(obj_id) or rs.IsMeshClosed(obj_id):
        
        # Récupération densité
        rho, mat_name = get_obj_density(obj_id)
        
        if rho <= 0:
            return # Pas de masse si pas de densité

        # Calcul du volume géométrique brut
        # On utilise RhinoCommon pour appliquer la transformation (mise à l'échelle du bloc)
        geo = rs.coercegeometry(obj_id)
        if not geo: return
        
        # On ne transforme pas la géométrie 'physiquement', on calcule le volume
        # et on applique le déterminant de la matrice pour le scale
        mp = Rhino.Geometry.VolumeMassProperties.Compute(geo)
        if not mp: return
        
        raw_vol = mp.Volume
        
        # Facteur d'échelle du bloc (déterminant de la matrice)
        # Cela gère si le bloc a été agrandi x2, le volume est x8
        # On prend la valeur absolue car un miroir rendrait le déterminant négatif
        det = xform.Determinant
        final_vol_rhino_units = raw_vol * abs(det)
        
        # Conversion en mètres cubes
        # Si unité = mm, facteur = 0.001. Volume facteur = 0.001^3
        vol_m3 = final_vol_rhino_units * math.pow(scale_factor, 3)
        
        mass = vol_m3 * rho

        # Stockage dans le dictionnaire
        if mat_name not in stats_dict:
            stats_dict[mat_name] = 0.0
        stats_dict[mat_name] += mass

def main():
    ids = rs.GetObjects("Sélectionnez les objets pour le calcul de masse", preselect=True)
    if not ids: return

    # Dictionnaire { "NomMateriau": Masse_Totale }
    stats = {}
    
    # Facteur de conversion (ex: 0.001 pour mm)
    scale_to_meter = get_doc_unit_scale_to_meter()
    
    print("Calcul en cours...")
    rs.EnableRedraw(False)
    
    identity = Rhino.Geometry.Transform.Identity
    
    for guid in ids:
        calculate_mass_recursive(guid, identity, stats, scale_to_meter)
        
    rs.EnableRedraw(True)

    if not stats:
        rs.MessageBox("Aucun objet valide avec un matériau défini n'a été trouvé.", 48)
        return

    total_mass = sum(stats.values())
    
    # Construction du message
    msg = "MASSE TOTALE : {:.3f} kg\n\nDétails par matériau :\n".format(total_mass)
    msg += "-" * 30 + "\n"
    
    for name, mass in stats.items():
        msg += "{}: {:.3f} kg\n".format(name, mass)

    rs.MessageBox(msg, 64, "Résultats Masse")
    print(msg)

if __name__ == "__main__":
    main()
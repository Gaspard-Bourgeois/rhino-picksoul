"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
"""
Script pour gérer la masse volumique (VolumicMass) des matériaux
d'un objet sélectionné, de son calque et de ses définitions de bloc.
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino


def get_material_object(mat_index):
    """Récupère l'objet Material RhinoCommon via son index."""
    if mat_index < 0:
        return None
    return sc.doc.Materials[mat_index]


def analyze_object_materials(obj_id, source_description, materials_dict):
    """
    Analyse un objet pour trouver son matériau direct et celui de son calque.
    Remplit le dictionnaire materials_dict.
    """
    
    # 1. Matériau de l'objet (s'il est assigné spécifiquement)
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index > -1:
        mat = get_material_object(mat_index)
        if mat:
            if mat.Id not in materials_dict:
                materials_dict[mat.Id] = {'obj': mat, 'sources': []}
            materials_dict[mat.Id]['sources'].append("Matériau direct de {}".format(source_description))


    # 2. Matériau du calque de l'objet
    layer_name = rs.ObjectLayer(obj_id)
    layer_mat_index = rs.LayerMaterialIndex(layer_name)
    if layer_mat_index > -1:
        mat = get_material_object(layer_mat_index)
        if mat:
            if mat.Id not in materials_dict:
                materials_dict[mat.Id] = {'obj': mat, 'sources': []}
            materials_dict[mat.Id]['sources'].append("Matériau du calque '{}' de {}".format(layer_name, source_description))


def main():
    # 1. Sélectionner un objet
    guid = rs.GetObject("Sélectionnez un objet pour définir la masse volumique", preselect=True)
    if not guid:
        return


    # Dictionnaire pour stocker les matériaux uniques trouvés
    # Clé : ID du matériau, Valeur : { 'obj': RhinoMaterial, 'sources': [liste des origines] }
    found_materials = {}


    # 2. Analyser l'objet principal sélectionné
    analyze_object_materials(guid, "l'objet sélectionné", found_materials)


    # 3. Si c'est un bloc, itérer dans sa définition
    if rs.IsBlockInstance(guid):
        block_name = rs.BlockInstanceName(guid)
        block_objects = rs.BlockObjects(block_name)
        
        if block_objects:
            for block_obj in block_objects:
                # Nom de l'objet ou son ID pour l'affichage
                sub_name = rs.ObjectName(block_obj) or str(block_obj)
                origin_desc = "objet '{}' dans le bloc '{block_name}'"
                analyze_object_materials(block_obj, origin_desc, found_materials)


    # 4. Vérifier si on a trouvé des matériaux
    if not found_materials:
        rs.MessageBox("Aucun matériau spécifique trouvé sur cet objet, son calque ou dans le bloc (tout est en 'Par Défaut').", 64)
        return


    # 5. Boucle d'interaction avec l'utilisateur pour chaque matériau trouvé
    KEY_NAME = "VolumicMass"
    
    for mat_id, data in found_materials.items():
        mat = data['obj']
        sources = data['sources']
        mat_name = mat.Name
        
        # Récupération de la valeur actuelle (UserString)
        current_val = mat.GetUserString(KEY_NAME)
        display_val = current_val if current_val else "Non définie"
        
        # Création du message de justification
        msg_sources = "\n- ".join(sources)
        prompt_msg = (
            "Matériau : " + mat_name + "\n"
            "Trouvé via :\n- " + msg_sources + "\n\n"
            "Masse volumique actuelle : " + display_val + " kg/m3\n"
            "Entrez la nouvelle valeur (laisser vide pour ne pas changer) :"
        )


        # Demander à l'utilisateur
        new_val_str = rs.StringBox(prompt_msg, default_value=current_val if current_val else "", title="Config: {}".format(mat_name))


        # Si l'utilisateur annule ou laisse vide (et que ce n'est pas pour effacer), on passe
        if new_val_str is None:
            continue # Annulé
        
        if new_val_str.strip() == "":
             # Optionnel : Si l'utilisateur vide le champ, on pourrait vouloir supprimer la clé.
             # Ici, on choisit de ne rien faire si vide pour éviter les erreurs.
             continue


        # Validation numérique
        try:
            val_float = float(new_val_str)
            
            # Mise à jour
            mat.SetUserString(KEY_NAME, str(val_float))
            mat.CommitChanges() # Important pour sauvegarder dans RhinoCommon
            
            rs.Print("Succès : {} -> {} = {} kg/m3".format(mat_name, KEY_NAME, val_float))
            
        except ValueError:
            rs.MessageBox(f"Erreur : '{}' n'est pas un nombre valide. Modification ignorée pour {}.".format(new_val_str, mat_name), 48)


    rs.MessageBox("Traitement des matériaux terminé. Vérifiez la ligne de commande pour l'historique.", 64)


if __name__ == "__main__":
    main()

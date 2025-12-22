# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def get_material_from_index(mat_index):
    """
    Récupère l'objet Material RhinoCommon de manière sécurisée.
    """
    if mat_index < 0:
        return None
    
    # Vérification pour éviter les erreurs d'index hors limites
    if mat_index >= len(sc.doc.Materials):
        return None
        
    return sc.doc.Materials[mat_index]

def analyze_object_materials(obj_id, source_desc, materials_dict):
    """
    Cherche le matériau sur l'objet ET sur son calque.
    Met à jour le dictionnaire materials_dict.
    """
    
    # --- 1. Matériau assigné directement à l'objet ---
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index > -1:
        mat = get_material_from_index(mat_index)
        if mat:
            mat_id = mat.Id
            if mat_id not in materials_dict:
                materials_dict[mat_id] = {'obj': mat, 'sources': []}
            
            # Utilisation de .format() au lieu de f-string
            msg = "Materiau direct de {}".format(source_desc)
            materials_dict[mat_id]['sources'].append(msg)

    # --- 2. Matériau du calque de l'objet ---
    layer_name = rs.ObjectLayer(obj_id)
    layer_mat_index = rs.LayerMaterialIndex(layer_name)
    
    if layer_mat_index > -1:
        mat = get_material_from_index(layer_mat_index)
        if mat:
            mat_id = mat.Id
            if mat_id not in materials_dict:
                materials_dict[mat_id] = {'obj': mat, 'sources': []}
            
            # Utilisation de .format() au lieu de f-string
            msg = "Calque '{}' de {}".format(layer_name, source_desc)
            materials_dict[mat_id]['sources'].append(msg)

def main():
    # 1. Sélection de l'objet
    guid = rs.GetObject("Selectionnez un objet", preselect=True)
    if not guid:
        return

    # Dictionnaire de stockage : { ID_Materiau : { 'obj': Material, 'sources': [] } }
    found_materials = {}

    # 2. Analyse de l'objet principal
    analyze_object_materials(guid, "l'objet selectionne", found_materials)

    # 3. Gestion des Blocs (Block Instance)
    if rs.IsBlockInstance(guid):
        block_name = rs.BlockInstanceName(guid)
        # Récupère les objets qui composent le bloc
        block_objects = rs.BlockObjects(block_name)
        
        if block_objects:
            for block_obj in block_objects:
                # Tentative de récupérer le nom, sinon on utilise l'ID
                sub_name = rs.ObjectName(block_obj)
                if not sub_name:
                    sub_name = str(block_obj)
                
                # Description sans f-string
                desc = "objet '{}' dans le bloc '{}'".format(sub_name, block_name)
                analyze_object_materials(block_obj, desc, found_materials)

    # 4. Si aucun matériau n'est trouvé
    if not found_materials:
        rs.MessageBox("Aucun materiau specifique trouve (tout est en 'Par Defaut').", 64)
        return

    # 5. Itération sur les matériaux trouvés
    KEY_NAME = "VolumicMass"
    
    # On itère sur les clés du dictionnaire
    for mat_id in found_materials:
        entry = found_materials[mat_id]
        mat = entry['obj']
        sources_list = entry['sources']
        mat_name = mat.Name
        
        # Récupération UserString
        current_val = mat.GetUserString(KEY_NAME)
        
        if current_val:
            display_val = current_val
        else:
            display_val = "Non definie"
        
        # Construction du message pour l'utilisateur
        # On joint la liste des sources avec des retours à la ligne
        sources_str = "\n- ".join(sources_list)
        
        # Construction du message complet avec .format()
        prompt_msg = "Materiau : {}\nTrouve via :\n- {}\n\nMasse volumique actuelle : {} kg/m3\nEntrez la nouvelle valeur :".format(mat_name, sources_str, display_val)
        
        # Titre de la fenêtre
        title_msg = "Config: {}".format(mat_name)

        # Boîte de dialogue
        default_str = ""
        if current_val:
            default_str = current_val
            
        new_val_str = rs.StringBox(prompt_msg, default_value=default_str, title=title_msg)

        # Si Annuler est pressé ou si vide
        if new_val_str is None:
            continue
        
        if str(new_val_str).strip() == "":
            continue

        # Validation et Enregistrement
        try:
            val_float = float(new_val_str)
            
            # Mise à jour RhinoCommon
            mat.SetUserString(KEY_NAME, str(val_float))
            mat.CommitChanges() # Indispensable pour valider le changement
            
            print("Succes : Materiau '{}' mis a jour a {} kg/m3".format(mat_name, val_float))
            
        except ValueError:
            rs.MessageBox("Erreur : Valeur non numerique. Ignore.", 48)

    rs.MessageBox("Traitement termine.", 64)

if __name__ == "__main__":
    main()
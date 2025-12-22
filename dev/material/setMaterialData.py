# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def get_first_material_by_name(name):
    """
    Parcourt la table des materiaux et renvoie le premier 
    objet Material dont le nom correspond exactement.
    """
    if not name: return None
    for mat in sc.doc.Materials:
        if mat.Name == name:
            return mat
    return None

def analyze_object_material_names(obj_id, source_desc, names_dict):
    """
    Trouve les NOMS des materiaux (objet et calque) et les stocke
    dans names_dict avec leur justification.
    """
    
    # 1. Materiau de l'objet
    mat_index = rs.ObjectMaterialIndex(obj_id)
    if mat_index > -1:
        # On recupere le nom via l'index actuel
        temp_mat = sc.doc.Materials[mat_index]
        if temp_mat and temp_mat.Name:
            mat_name = temp_mat.Name
            if mat_name not in names_dict:
                names_dict[mat_name] = []
            msg = "Materiau direct de {}".format(source_desc)
            names_dict[mat_name].append(msg)

    # 2. Materiau du calque
    layer_name = rs.ObjectLayer(obj_id)
    layer_mat_index = rs.LayerMaterialIndex(layer_name)
    if layer_mat_index > -1:
        temp_mat = sc.doc.Materials[layer_mat_index]
        if temp_mat and temp_mat.Name:
            mat_name = temp_mat.Name
            if mat_name not in names_dict:
                names_dict[mat_name] = []
            msg = "Calque '{}' de {}".format(layer_name, source_desc)
            names_dict[mat_name].append(msg)

def main():
    guid = rs.GetObject("Selectionnez un objet", preselect=True)
    if not guid: return

    # names_dict : { "NomDuMateriau" : ["Source 1", "Source 2"] }
    names_dict = {}

    # Analyse de l'objet principal
    analyze_object_material_names(guid, "l'objet selectionne", names_dict)

    # Analyse du bloc
    if rs.IsBlockInstance(guid):
        block_name = rs.BlockInstanceName(guid)
        block_objects = rs.BlockObjects(block_name)
        if block_objects:
            for block_obj in block_objects:
                sub_name = rs.ObjectName(block_obj) or str(block_obj)
                desc = "objet '{}' dans le bloc '{}'".format(sub_name, block_name)
                analyze_object_material_names(block_obj, desc, names_dict)

    if not names_dict:
        rs.MessageBox("Aucun materiau nomme trouve.", 64)
        return

    KEY_NAME = "VolumicMass"
    
    # Parcourir chaque nom unique trouve
    for mat_name in names_dict:
        # Trouver la premiere occurrence reelle dans la base Rhino
        target_mat = get_first_material_by_name(mat_name)
        
        if not target_mat:
            continue
            
        sources_list = names_dict[mat_name]
        
        # Recuperation de la valeur existante sur cette occurrence
        current_val = target_mat.GetUserString(KEY_NAME)
        display_val = current_val if current_val else "Non definie"
        
        sources_str = "\n- ".join(sources_list)
        prompt_msg = "Materiau : {}\nOrigines :\n- {}\n\nMasse volumique : {} kg/m3\nNouvelle valeur :".format(mat_name, sources_str, display_val)
        
        new_val_str = rs.StringBox(prompt_msg, default_value=current_val or "", title="Masse Volumique")

        if new_val_str is None: continue
        if str(new_val_str).strip() == "": continue

        try:
            val_float = float(new_val_str)
            
            # Mise a jour de la PREMIERE occurrence trouvee
            target_mat.SetUserString(KEY_NAME, str(val_float))
            target_mat.CommitChanges()
            
            print("Succes : Materiau '{}' mis a jour ({} kg/m3)".format(mat_name, val_float))
        except ValueError:
            rs.MessageBox("Nombre invalide.", 48)

    rs.MessageBox("Mise a jour terminee.", 64)

if __name__ == "__main__":
    main()
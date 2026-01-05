"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 05/01/26
"""
import rhinoscriptsyntax as rs
import re

def select_next_elements():
    # Récupérer les objets actuellement sélectionnés
    selected_objects = rs.GetObjects("Sélectionnez les éléments actuels", preselect=True)
    
    if not selected_objects:
        print("Aucune sélection active.")
        return

    next_objects_to_select = []
    
    # On désélectionne tout pour préparer la nouvelle sélection
    rs.UnselectAllObjects()

    for obj_id in selected_objects:
        obj_name = rs.ObjectName(obj_id)
        obj_layer = rs.ObjectLayer(obj_id)
        
        if not obj_name:
            continue

        # --- CAS 1 : POSE (Nommé "3", "4"...) ---
        if obj_name.isdigit():
            target_idx = int(obj_name) + 1
            target_name = str(target_idx)
            
            layer_objs = rs.ObjectsByLayer(obj_layer)
            if layer_objs:
                for cand_id in layer_objs:
                    if rs.ObjectName(cand_id) == target_name:
                        next_objects_to_select.append(cand_id)

        # --- CAS 2 : COURBE (Nommé "... X-Y") ---
        else:
            match = re.search(r"(\d+)-(\d+)$", obj_name)
            if match:
                current_end = int(match.group(2))
                
                layer_objs = rs.ObjectsByLayer(obj_layer)
                if layer_objs:
                    for cand_id in layer_objs:
                        cand_name = rs.ObjectName(cand_id)
                        if cand_name and cand_name != obj_name:
                            cand_match = re.search(r"(\d+)-(\d+)$", cand_name)
                            if cand_match:
                                # Le début du suivant doit être la fin de l'actuel
                                if int(cand_match.group(1)) == current_end:
                                    next_objects_to_select.append(cand_id)

    if next_objects_to_select:
        rs.SelectObjects(next_objects_to_select)
        print("{} éléments suivants sélectionnés.".format(len(next_objects_to_select)))
    else:
        print("Aucun élément suivant trouvé.")

if __name__ == "__main__":
    select_next_elements()

import rhinoscriptsyntax as rs
import re

def select_previous_element():
    # Récupérer les objets actuellement sélectionnés
    selected_objects = rs.GetObjects("Sélectionnez les éléments actuels", preselect=True)
    
    if not selected_objects:
        print("Aucune sélection active.")
        return

    prev_objects_to_select = []
    
    # On désélectionne tout pour préparer la nouvelle sélection
    rs.UnselectAllObjects()

    for obj_id in selected_objects:
        obj_name = rs.ObjectName(obj_id)
        obj_layer = rs.ObjectLayer(obj_id)
        
        if not obj_name:
            continue

        # --- CAS 1 : C'est une POSE (Instance nommée "1", "8", "10"...) ---
        if obj_name.isdigit():
            current_idx = int(obj_name)
            target_idx = current_idx - 1 # On cherche le précédent
            target_name = str(target_idx)
            
            # Recherche sur le même calque
            layer_objs = rs.ObjectsByLayer(obj_layer)
            found = False
            if layer_objs:
                for cand_id in layer_objs:
                    if rs.ObjectName(cand_id) == target_name:
                        prev_objects_to_select.append(cand_id)
                        found = True
                        break 
            
            if not found:
                # C'est normal si on est à 0 et qu'on cherche -1
                print("Pose précédente '{}' introuvable (Début de séquence ?).".format(target_name))

        # --- CAS 2 : C'est une COURBE (Nommée "... X-Y") ---
        else:
            # On récupère le point de DEBUT de la courbe actuelle
            match = re.search(r"(\d+)-(\d+)$", obj_name)
            
            if match:
                current_start = int(match.group(1))
                # current_end = int(match.group(2)) # Pas utile pour le 'précédent'
                
                # La logique : La courbe PRÉCÉDENTE doit FINIR là où celle-ci COMMENCE.
                # On cherche donc une courbe dont le nom finit par "-current_start"
                # Ex: Si j'ai "3-4", je cherche "...-3"
                
                layer_objs = rs.ObjectsByLayer(obj_layer)
                found = False
                
                if layer_objs:
                    for cand_id in layer_objs:
                        cand_name = rs.ObjectName(cand_id)
                        if cand_name and cand_name != obj_name:
                            # On regarde la fin du nom du candidat
                            cand_match = re.search(r"-(\d+)$", cand_name)
                            if cand_match:
                                cand_end = int(cand_match.group(1))
                                
                                # Si la fin du candidat correspond au début de ma sélection
                                if cand_end == current_start:
                                    prev_objects_to_select.append(cand_id)
                                    found = True
                                    break
                
                if not found:
                    print("Courbe précédente finissant à l'index {} introuvable.".format(current_start))
            else:
                # Ignore les objets qui ne correspondent pas au pattern (comme le texte du programme)
                pass

    # Sélection finale
    if prev_objects_to_select:
        rs.SelectObjects(prev_objects_to_select)
        print("{} éléments précédents sélectionnés.".format(len(prev_objects_to_select)))
    else:
        print("Aucun élément précédent trouvé.")

if __name__ == "__main__":
    select_previous_element()
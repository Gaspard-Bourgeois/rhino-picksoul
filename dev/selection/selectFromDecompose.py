# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def get_hierarchy_data(obj_id):
    """Extrait les niveaux hiérarchiques d'un objet sous forme de dictionnaire {niveau: "nom#indice"}."""
    keys = rs.GetUserText(obj_id)
    data = {}
    if not keys: return data
    
    for key in keys:
        if key.startswith("BlockNameLevel_"):
            try:
                level = int(key.split("_")[-1])
                data[level] = rs.GetUserText(obj_id, key)
            except ValueError: continue
    return data

def select_by_hierarchy_value(search_value):
    """Sélectionne tous les objets ayant la valeur donnée dans n'importe quel niveau."""
    all_objs = rs.AllObjects()
    to_select = []
    
    for obj in all_objs:
        keys = rs.GetUserText(obj)
        if keys:
            for key in keys:
                if key.startswith("BlockNameLevel_"):
                    if rs.GetUserText(obj, key) == search_value:
                        to_select.append(obj)
                        break
    
    if to_select:
        rs.EnableRedraw(False)
        rs.UnselectAllObjects()
        rs.SelectObjects(to_select)
        rs.EnableRedraw(True)
        print("Selection de {} objets pour : {}".format(len(to_select), search_value))
    else:
        print("Aucun objet trouvé pour : {}".format(search_value))

def main():
    # Récupération de l'historique dans la session
    last_search = sc.sticky.get("last_hierarchy_search", None)
    
    # Tentative de sélection initiale
    selected = rs.SelectedObjects()
    
    target_value = None
    
    if selected:
        # On prend le premier objet sélectionné pour analyser sa hiérarchie
        obj_id = selected[0]
        hierarchy = get_hierarchy_data(obj_id)
        
        if not hierarchy:
            print("L'objet sélectionné n'a pas de données de hiérarchie.")
            return

        # Trouver le niveau le plus bas (le plus grand X)
        levels = sorted(hierarchy.keys(), reverse=True)
        lowest_level = levels[0]
        current_lowest_value = hierarchy[lowest_level]

        # LOGIQUE DE REMONTÉE :
        # Si la dernière recherche correspond à la valeur la plus basse de l'objet, 
        # on cherche le niveau immédiatement au-dessus.
        if last_search == current_lowest_value and len(levels) > 1:
            target_value = hierarchy[levels[1]]
            print("Remontée hiérarchique : Niveau supérieur détecté.")
        else:
            target_value = current_lowest_value
            
    else:
        # AUCUNE SÉLECTION : Entrée manuelle
        prompt = "Entrez la valeur à chercher (block_name#indice)"
        if last_search:
            prompt += " [Dernier: {}]".format(last_search)
        
        user_input = rs.GetString(prompt)
        
        if user_input is None: return # Annulation
        
        if user_input == "" and last_search:
            target_value = last_search
        elif user_input != "":
            target_value = user_input
        else:
            print("Aucune valeur saisie.")
            return

    if target_value:
        # Exécuter la sélection et mettre à jour l'historique
        select_by_hierarchy_value(target_value)
        sc.sticky["last_hierarchy_search"] = target_value

if __name__ == "__main__":
    main()

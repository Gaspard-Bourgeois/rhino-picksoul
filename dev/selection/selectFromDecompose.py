# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def get_hierarchy_data(obj_id):
    """Extrait les niveaux hiérarchiques {niveau_int: "nom#indice"}."""
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

def select_by_hierarchy_value(search_value, level_index):
    """Sélectionne tous les objets possédant la valeur exacte au niveau donné."""
    all_objs = rs.AllObjects()
    to_select = []
    key_to_find = "BlockNameLevel_{}".format(level_index)
    
    for obj in all_objs:
        if rs.GetUserText(obj, key_to_find) == search_value:
            to_select.append(obj)
    
    if to_select:
        rs.EnableRedraw(False)
        rs.UnselectAllObjects()
        rs.SelectObjects(to_select)
        rs.EnableRedraw(True)
        print("Sélection : {} (Niveau {}, {} objets)".format(search_value, level_index, len(to_select)))
        return True
    return False

def main():
    # Récupération de l'historique de la session
    last_search = sc.sticky.get("last_hierarchy_search", None)
    selected = rs.SelectedObjects()
    
    target_value = None
    target_level = None

    if selected:
        # Analyse du premier objet sélectionné
        obj_id = selected[0]
        hierarchy = get_hierarchy_data(obj_id)
        
        if not hierarchy:
            print("L'objet n'a pas de données de hiérarchie.")
            return

        levels = sorted(hierarchy.keys())
        
        # Trouver à quel niveau se trouve la valeur actuelle de l'objet
        # On part du principe que la valeur "actuelle" de l'objet est son niveau le plus bas
        lowest_level = levels[-1]
        lowest_value = hierarchy[lowest_level]

        # LOGIQUE STRICTE : 
        # On ne remonte que si l'objet sélectionné est le résultat de la recherche précédente
        if last_search and any(hierarchy[l] == last_search for l in levels):
            # Trouver l'index du niveau correspondant au dernier historique
            current_lvl_idx = -1
            for i, l in enumerate(levels):
                if hierarchy[l] == last_search:
                    current_lvl_idx = i
                    break
            
            # Si on a trouvé le match, on cherche le niveau immédiatement supérieur (index - 1)
            next_idx = current_lvl_idx - 1
            if next_idx >= 0:
                target_level = levels[next_idx]
                target_value = hierarchy[target_level]
                print("Remontée hiérarchique vers le parent...")
            else:
                # Si on est déjà au sommet (Niveau 0), on reboucle ou on reste au sommet
                target_level = levels[0]
                target_value = hierarchy[target_level]
                print("Niveau racine atteint.")
        else:
            # Cas : Nouvel objet ou pas de correspondance historique -> Niveau le plus bas
            target_level = lowest_level
            target_value = lowest_value

    else:
        # --- MODE RECHERCHE MANUELLE ---
        prompt = "Entrez valeur (Ex: Bloc#1)"
        if last_search: prompt += " [Dernier: {}]".format(last_search)
        
        user_input = rs.GetString(prompt)
        if user_input is None: return
        
        if user_input == "" and last_search:
            target_value = last_search
        elif user_input != "":
            target_value = user_input
        else: return

        # Trouver le niveau correspondant à la saisie manuelle
        for obj in rs.AllObjects():
            obj_data = get_hierarchy_data(obj)
            for lvl, val in obj_data.items():
                if val == target_value:
                    target_level = lvl
                    break
            if target_level is not None: break

    if target_value and target_level is not None:
        if select_by_hierarchy_value(target_value, target_level):
            sc.sticky["last_hierarchy_search"] = target_value
    else:
        print("Valeur introuvable.")

if __name__ == "__main__":
    main()

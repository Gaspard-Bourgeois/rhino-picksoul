# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def get_hierarchy_data(obj_id):
    """
    Extrait tous les niveaux hiérarchiques d'un objet.
    Retourne un dictionnaire {niveau_int: "nom#indice"}.
    """
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
    """Sélectionne tous les objets possédant la valeur à un niveau spécifique."""
    all_objs = rs.AllObjects()
    to_select = []
    key_to_find = "BlockNameLevel_{}".format(level_index)
    
    for obj in all_objs:
        val = rs.GetUserText(obj, key_to_find)
        if val == search_value:
            to_select.append(obj)
    
    if to_select:
        rs.EnableRedraw(False)
        rs.UnselectAllObjects()
        rs.SelectObjects(to_select)
        rs.EnableRedraw(True)
        print("Niveau {} sélectionné : {} ({} objets)".format(level_index, search_value, len(to_select)))
        return True
    return False

def main():
    # Récupération de l'historique de la session
    last_search = sc.sticky.get("last_hierarchy_search", None)
    
    selected = rs.SelectedObjects()
    target_value = None
    target_level = None

    if selected:
        # Analyse de l'objet de référence (le premier sélectionné)
        obj_id = selected[0]
        hierarchy = get_hierarchy_data(obj_id)
        
        if not hierarchy:
            print("L'objet n'a pas de données de hiérarchie.")
            return

        # Liste triée des niveaux (ex: [0, 1, 2, 3])
        available_levels = sorted(hierarchy.keys())
        
        # Identification du niveau de la dernière recherche dans cet objet
        current_idx_in_hierarchy = -1
        if last_search:
            for lvl in available_levels:
                if hierarchy[lvl] == last_search:
                    current_idx_in_hierarchy = available_levels.index(lvl)
                    break
        
        # LOGIQUE DE NAVIGATION MULTI-NIVEAUX
        # Si la dernière recherche est trouvée dans l'objet, on monte d'un cran
        if current_idx_in_hierarchy != -1:
            # On prend l'index précédent dans la liste triée (remontée vers le parent)
            next_idx = current_idx_in_hierarchy - 1
            
            # Si on dépasse le niveau 0 (racine), on reboucle vers le plus profond
            if next_idx < 0:
                print("Racine atteinte. Retour au niveau le plus bas.")
                next_idx = len(available_levels) - 1
            
            target_level = available_levels[next_idx]
            target_value = hierarchy[target_level]
        else:
            # Première fois qu'on traite cet objet : on prend le niveau le plus profond
            target_level = available_levels[-1]
            target_value = hierarchy[target_level]

    else:
        # --- MODE RECHERCHE MANUELLE ---
        prompt = "Valeur à chercher (Ex: Vis#4)"
        if last_search:
            prompt += " [Dernier: {}]".format(last_search)
        
        user_input = rs.GetString(prompt)
        if user_input is None: return
        
        if user_input == "" and last_search:
            target_value = last_search
        elif user_input != "":
            target_value = user_input
        else:
            return

        # En mode manuel, on doit scanner tous les niveaux pour trouver la clé correspondante
        all_objs = rs.AllObjects()
        for obj in all_objs:
            keys = rs.GetUserText(obj)
            if keys:
                for k in keys:
                    if rs.GetUserText(obj, k) == target_value:
                        target_level = int(k.split("_")[-1])
                        break
            if target_level is not None: break

    if target_value and target_level is not None:
        if select_by_hierarchy_value(target_value, target_level):
            sc.sticky["last_hierarchy_search"] = target_value
    else:
        print("Valeur '{}' introuvable dans le document.".format(target_value))

if __name__ == "__main__":
    main()

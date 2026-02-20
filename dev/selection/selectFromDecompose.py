# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def get_hierarchy_data(obj_id):
    """Extrait les niveaux {X: "Nom#Y"}."""
    keys = rs.GetUserText(obj_id)
    data = {}
    if not keys: return data
    for key in keys:
        if key.startswith("BlockNameLevel_"):
            try:
                lvl = int(key.split("_")[-1])
                data[lvl] = rs.GetUserText(obj_id, key)
            except: continue
    return data

def main():
    # 1. Récupérer l'historique de la session
    last_val = sc.sticky.get("last_hierarchy_value", None)
    last_lvl = sc.sticky.get("last_hierarchy_level", None)
    
    selected = rs.SelectedObjects()
    
    target_value = None
    target_level = None

    if selected:
        # On analyse le premier objet de la sélection actuelle
        obj_id = selected[0]
        hierarchy = get_hierarchy_data(obj_id)
        
        if not hierarchy:
            print("Aucune donnée hiérarchique sur cet objet.")
            return

        levels = sorted(hierarchy.keys()) # [0, 1, 2...]
        
        # --- LA LOGIQUE CRUCIALE ---
        # Est-ce que l'objet sélectionné possède la valeur du dernier historique 
        # AU NIVEAU où on s'était arrêté ?
        is_continuation = False
        if last_val and last_lvl is not None:
            if hierarchy.get(last_lvl) == last_val:
                is_continuation = True

        if is_continuation:
            # On cherche le niveau juste au-dessus (X - 1)
            idx_actuel = levels.index(last_lvl)
            if idx_actuel > 0:
                target_level = levels[idx_actuel - 1]
                target_value = hierarchy[target_level]
                print("Remontée : Niveau {} -> {}".format(last_lvl, target_level))
            else:
                # On est déjà à la racine (0), on y reste
                target_level = levels[0]
                target_value = hierarchy[target_level]
                print("Racine (Niveau 0) déjà atteinte.")
        else:
            # Nouvel objet ou sélection différente : on repart du plus bas
            target_level = levels[-1]
            target_value = hierarchy[target_level]
            print("Nouvelle sélection : départ du niveau le plus bas ({})".format(target_level))

    else:
        # --- MODE RECHERCHE MANUELLE (Vide + Entrée) ---
        prompt = "Valeur à chercher"
        if last_val: prompt += " [Dernier: {}]".format(last_val)
        
        user_input = rs.GetString(prompt)
        if user_input is None: return
        
        if user_input == "" and last_val:
            target_value = last_val
            target_level = last_lvl
        elif "#" in user_input:
            target_value = user_input
            # On cherche à quel niveau appartient cette valeur dans le doc
            for obj in rs.AllObjects():
                data = get_hierarchy_data(obj)
                for l, v in data.items():
                    if v == target_value:
                        target_level = l
                        break
                if target_level is not None: break
        else:
            print("Format invalide (attendu: Nom#Indice)")
            return

    # Exécution de la sélection
    if target_value and target_level is not None:
        all_objs = rs.AllObjects()
        to_select = []
        key_str = "BlockNameLevel_{}".format(target_level)
        
        for obj in all_objs:
            if rs.GetUserText(obj, key_str) == target_value:
                to_select.append(obj)
        
        if to_select:
            rs.EnableRedraw(False)
            rs.UnselectAllObjects()
            rs.SelectObjects(to_select)
            rs.EnableRedraw(True)
            
            # Mise à jour de l'historique pour le prochain clic
            sc.sticky["last_hierarchy_value"] = target_value
            sc.sticky["last_hierarchy_level"] = target_level
            print("Sélectionné : {} ({} objets)".format(target_value, len(to_select)))

if __name__ == "__main__":
    main()

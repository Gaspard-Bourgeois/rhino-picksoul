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
    # On récupère les objets sélectionnés en premier
    selected = rs.SelectedObjects()
    
    # TODO : Récupérer l'historique seulement si aucun objet n'est sélectionné
    # (Ou pour comparer avec la sélection actuelle)
    last_val = sc.sticky.get("last_hierarchy_value", None)
    last_lvl = sc.sticky.get("last_hierarchy_level", None)
    
    target_value = None
    target_level = None

    if selected:
        # On analyse le premier objet pour obtenir sa structure
        obj_id = selected[0]
        hierarchy = get_hierarchy_data(obj_id)
        
        if not hierarchy:
            print("Aucune donnée hiérarchique sur cet objet.")
            return

        levels = sorted(hierarchy.keys()) # [0, 1, 2...]
        
        # TODO : On cherche pour commencer les objets du niveau hiérarchique le plus bas
        # Mais avant, on vérifie si on doit monter en grade
        is_continuation = False
        
        if last_val and last_lvl is not None:
            # On vérifie si la sélection actuelle correspond au dernier résultat produit
            # 1. Est-ce que la valeur du niveau stocké correspond à l'objet ?
            if hierarchy.get(last_lvl) == last_val:
                # 2. TODO : Si le résultat est compris dans la sélection actuelle (tous les objets sélectionnés partagent cette valeur)
                # On vérifie si le nombre d'objets sélectionnés correspond à ce qu'on attendrait d'un filtre sur last_val
                # Pour simplifier et fiabiliser : on vérifie si la sélection est "le fruit" de la commande précédente
                is_continuation = True
                key_str = "BlockNameLevel_{}".format(last_lvl)
                for s_id in selected:
                    if rs.GetUserText(s_id, key_str) != last_val:
                        is_continuation = False
                        break

        if is_continuation:
            # TODO : On cherche le niveau hiérarchique supérieur
            try:
                idx_actuel = levels.index(last_lvl)
                if idx_actuel > 0:
                    target_level = levels[idx_actuel - 1]
                    target_value = hierarchy[target_level]
                    print("Remontée hiérarchique : Niveau {} -> {}".format(last_lvl, target_level))
                else:
                    target_level = levels[0]
                    target_value = hierarchy[target_level]
                    print("Racine atteinte.")
            except ValueError:
                # Si le niveau stocké n'existe plus dans cet objet, on repart du bas
                target_level = levels[-1]
                target_value = hierarchy[target_level]
        else:
            # Pas de correspondance avec l'historique ou nouvel objet : niveau le plus bas
            target_level = levels[-1]
            target_value = hierarchy[target_level]
            print("Niveau le plus bas sélectionné : {}".format(target_value))

    else:
        # --- MODE RECHERCHE MANUELLE ---
        # Ici on utilise l'historique pour proposer la complétion
        prompt = "Valeur à chercher"
        if last_val: prompt += " [Dernier: {}]".format(last_val)
        
        user_input = rs.GetString(prompt)
        if user_input is None: return
        
        if user_input == "" and last_val:
            target_value = last_val
            target_level = last_lvl
        elif "#" in user_input:
            target_value = user_input
            # On cherche le niveau correspondant dans le document
            for obj in rs.AllObjects():
                data = get_hierarchy_data(obj)
                for l, v in data.items():
                    if v == target_value:
                        target_level = l
                        break
                if target_level is not None: break
        else:
            print("Format invalide.")
            return

    # Exécution de la sélection finale
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
            
            # Mise à jour de l'historique
            sc.sticky["last_hierarchy_value"] = target_value
            sc.sticky["last_hierarchy_level"] = target_level
            print("Sélection : {} ({} objets)".format(target_value, len(to_select)))

if __name__ == "__main__":
    main()

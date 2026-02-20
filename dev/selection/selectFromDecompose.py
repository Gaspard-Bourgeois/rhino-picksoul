# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def get_hierarchy_data(obj_id):
    """Extrait les niveaux {X: "Nom#Y"} d'un objet."""
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
    selected = rs.SelectedObjects()
    
    # Historique de la session (sticky)
    last_val = sc.sticky.get("last_hierarchy_value")
    last_lvl = sc.sticky.get("last_hierarchy_level")
    
    target_value = None
    target_level = None

    if selected:
        # Analyse du premier objet pour la structure de référence
        obj_id = selected[0]
        hierarchy = get_hierarchy_data(obj_id)
        
        if not hierarchy:
            print("L'objet sélectionné ne possède pas de données hiérarchiques.")
            return

        # Niveaux triés (ex: [0, 1, 2] où 2 est le plus bas/profond)
        levels = sorted(hierarchy.keys())
        
        # --- LOGIQUE DE CONTINUATION ---
        # TODO : on parcours tous les levels dans l'ordre du plus bas au plus haut, on ne continue d'étendre la sélection que si tous les objets du niveau parcouru sont compris dans la selection initiale
        is_continuation = False
       
        if last_val and last_lvl is not None:
            # On vérifie si TOUS les objets sélectionnés correspondent au dernier critère
            match_count = 0
            for s_id in selected:
                if rs.GetUserText(s_id, "BlockNameLevel_{}".format(last_lvl)) == last_val:
                    match_count += 1
            
            if match_count == len(selected):
                is_continuation = True

        if is_continuation:
            try:
                current_idx = levels.index(last_lvl)
                if current_idx > 0:
                    target_level = levels[current_idx - 1]
                    target_value = hierarchy[target_level]
                    print("Remontée : Niveau {} -> {}".format(last_lvl, target_level))
                else:
                    # On est déjà à la racine (Niveau 0)
                    target_level = levels[0]
                    target_value = hierarchy[target_level]
                    print("Niveau racine (0) déjà atteint.")
            except ValueError:
                # Sécurité si l'index a sauté
                target_level = levels[-1]
                target_value = hierarchy[target_level]
        else:
            # TODO : Sinon (nouvelle sélection), on cherche le niveau le plus bas
            target_level = levels[-1]
            target_value = hierarchy[target_level]
            print("Départ au niveau le plus bas : {}".format(target_level))

    else:
        # --- MODE MANUEL (Aucun objet sélectionné) ---
        # L'historique est utilisé que pour aider la saisie utilisateur
        prompt = "Entrez la valeur à chercher (Nom#Indice)"
        if last_val:
            prompt += " [Dernier : {}]".format(last_val)
        
        user_input = rs.GetString(prompt)
        
        if user_input is None: return # Annulation
        
        # Si Entrée sans texte, on prend la dernière valeur
        if user_input == "" and last_val:
            target_value = last_val
            target_level = last_lvl
        elif "#" in user_input:
            target_value = user_input
            # On scanne le document pour trouver le niveau correspondant à cette valeur
            for obj in rs.AllObjects():
                data = get_hierarchy_data(obj)
                for l, v in data.items():
                    if v == target_value:
                        target_level = l
                        break
                if target_level is not None: break
        else:
            print("Format invalide ou aucune valeur en historique.")
            return

    # --- EXÉCUTION DE LA SÉLECTION ---
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
            
            # Mise à jour de l'historique pour le prochain appel
            sc.sticky["last_hierarchy_value"] = target_value
            sc.sticky["last_hierarchy_level"] = target_level
            print("Sélectionné : {} ({} objets)".format(target_value, len(to_select)))
        else:
            print("Aucun objet trouvé pour {} au niveau {}.".format(target_value, target_level))

if __name__ == "__main__":
    main()

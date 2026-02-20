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
    
    # Historique de la session (sticky) pour le mode manuel
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

        # Niveaux triés du plus haut (0) au plus bas (max)
        levels = sorted(hierarchy.keys())
        
        # --- LOGIQUE DE CONTINUATION (TODO corrigé) ---
        # On parcours tous les niveaux du plus bas au plus haut pour trouver l'état actuel
        current_detected_level = None
        all_objs = rs.AllObjects() # Pour compter les représentants dans le document
        
        # Inversion pour parcourir du plus bas au plus haut
        for lvl in reversed(levels):
            val = hierarchy[lvl]
            key_str = "BlockNameLevel_{}".format(lvl)
            
            # Compter combien d'objets dans le document ont cette valeur
            objs_in_doc = [o for o in all_objs if rs.GetUserText(o, key_str) == val]
            
            # Vérifier si TOUS ces objets sont présents dans la sélection actuelle
            all_contained = True
            for o_doc in objs_in_doc:
                if o_doc not in selected:
                    all_contained = False
                    break
            
            if all_contained:
                current_detected_level = lvl
            else:
                # Dès qu'un niveau n'est pas totalement sélectionné, on s'arrête
                break

        # TODO : Si un niveau est totalement sélectionné, on cherche le niveau supérieur
        if current_detected_level is not None:
            try:
                idx = levels.index(current_detected_level)
                if idx > 0:
                    target_level = levels[idx - 1]
                    target_value = hierarchy[target_level]
                    print("Remontée hiérarchique : Niveau {} -> {}".format(current_detected_level, target_level))
                else:
                    target_level = levels[0]
                    target_value = hierarchy[target_level]
                    print("Racine atteinte (Niveau 0).")
            except ValueError: pass
        
        # TODO : Sinon (nouvelle sélection / niveau partiel), on cherche le niveau le plus bas
        if target_level is None:
            target_level = levels[-1]
            target_value = hierarchy[target_level]
            print("Départ au niveau le plus bas : {}".format(target_level))

    else:
        # --- MODE MANUEL (Aucun objet sélectionné) ---
        # TODO : On n'utilise l'historique que si aucun objet n'est sélectionné
        prompt = "Entrez la valeur à chercher (Nom#Indice)"
        if last_val:
            prompt += " [Dernier : {}]".format(last_val)
        
        user_input = rs.GetString(prompt)
        
        if user_input is None: return 
        
        if user_input == "" and last_val:
            target_value = last_val
            target_level = last_lvl
        elif "#" in user_input:
            target_value = user_input
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
            
            # Mise à jour de l'historique
            sc.sticky["last_hierarchy_value"] = target_value
            sc.sticky["last_hierarchy_level"] = target_level
            print("Sélectionné : {} ({} objets)".format(target_value, len(to_select)))

if __name__ == "__main__":
    main()

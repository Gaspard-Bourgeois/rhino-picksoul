# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def update_annotations_with_options():
    # 1. Récupérer les styles et le style actuel
    styles = rs.DimStyleNames()
    if not styles:
        print("Aucun style d'annotation trouvé.")
        return

    current_default = rs.CurrentDimStyle()
    
    # Nettoyage des noms de styles pour l'affichage en options (Rhino n'aime pas les espaces dans les mots-clés)
    # On crée un dictionnaire pour faire la correspondance si besoin, 
    # mais rs.GetString accepte généralement les listes directes.
    options = [s.replace(" ", "_") for s in styles]

    # 2. Demander le style via la barre de commande
    msg = "Style actuel : {}. Choisir le nouveau style".format(current_default)
    res = rs.GetString(msg, current_default, options)

    if res is None: return # Annulation
    
    # Retrouver le nom original du style (si on a remplacé les espaces par des underscores)
    chosen_style = None
    if res in styles:
        chosen_style = res
    else:
        # Recherche de correspondance pour gérer les espaces/underscores
        for s in styles:
            if s.replace(" ", "_") == res or s == res:
                chosen_style = s
                break
    
    if not chosen_style:
        print("Style invalide.")
        return

    # 3. Traiter la sélection
    selected_objs = rs.SelectedObjects()
    
    if selected_objs:
        rs.EnableRedraw(False)
        anno_count = 0
        for obj_id in selected_objs:
            # 512 = Code pour tous les objets d'annotation (Cotes, Textes, Leaders)
            if rs.ObjectType(obj_id) == 512:
                rs.DimensionStyle(obj_id, chosen_style)
                anno_count += 1
        rs.EnableRedraw(True)
        
        if anno_count > 0:
            print("Succès : {} annotation(s) mise(s) à jour sur '{}'.".format(anno_count, chosen_style))
        else:
            print("Aucune annotation trouvée dans la sélection.")
    else:
        print("Aucune sélection. Modification du style par défaut uniquement.")

    # 4. Définir comme style par défaut
    rs.CurrentDimStyle(chosen_style)
    print("Style par défaut défini sur : {}".format(chosen_style))

if __name__ == "__main__":
    update_annotations_with_options()

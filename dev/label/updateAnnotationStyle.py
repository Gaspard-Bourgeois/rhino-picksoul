import rhinoscriptsyntax as rs

def update_all_annotation_styles():
    # 1. Récupérer tous les noms de styles d'annotation disponibles
    styles = rs.DimensionStyleNames()
    if not styles:
        print("Aucun style d'annotation trouvé dans le document.")
        return

    # 2. Demander à l'utilisateur de choisir un style
    chosen_style = rs.ListBox(styles, "Choisir le style pour toutes les annotations :", "Styles d'annotation")
    
    if not chosen_style:
        return

    # 3. Récupérer les objets sélectionnés
    selected_objs = rs.SelectedObjects()
    
    anno_count = 0

    if selected_objs:
        # On fige l'affichage pour gagner en performance si la sélection est grande
        rs.EnableRedraw(False)
        for obj_id in selected_objs:
            # IsAnnotation englobe : Cotes, Textes, Leaders, Hatches, etc.
            if rs.IsAnnotation(obj_id):
                # Appliquer le style
                rs.DimensionStyle(obj_id, chosen_style)
                anno_count += 1
        rs.EnableRedraw(True)
        
        if anno_count > 0:
            print("{} annotation(s) mise(s) à jour avec le style '{}'.".format(anno_count, chosen_style))
        else:
            print("Aucune annotation n'a été trouvée dans la sélection.")
    else:
        print("Aucune sélection. Le style par défaut a été mis à jour.")

    # 4. Définir le style choisi comme style actuel (pour les futures créations)
    rs.CurrentDimensionStyle(chosen_style)
    print("Le style '{}' est désormais le style par défaut.".format(chosen_style))

if __name__ == "__main__":
    update_all_annotation_styles()

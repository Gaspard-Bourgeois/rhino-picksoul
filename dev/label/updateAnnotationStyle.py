import rhinoscriptsyntax as rs

def update_all_annotation_styles():
    # 1. Récupérer tous les noms de styles (Correction : DimStyleNames)
    styles = rs.DimStyleNames()
    if not styles:
        print("Aucun style d'annotation trouvé.")
        return

    # 2. Demander à l'utilisateur de choisir un style
    chosen_style = rs.ListBox(styles, "Choisir le style :", "Styles d'annotation")
    
    if not chosen_style:
        return

    # 3. Traiter la sélection
    selected_objs = rs.SelectedObjects()
    anno_count = 0

    if selected_objs:
        rs.EnableRedraw(False)
        for obj_id in selected_objs:
            # Vérifie si c'est une annotation (Cote, Texte, Leader, etc.)
            if rs.IsAnnotation(obj_id):
                # Appliquer le style
                rs.DimensionStyle(obj_id, chosen_style)
                anno_count += 1
        rs.EnableRedraw(True)
        
        if anno_count > 0:
            print("{} annotation(s) mise(s) à jour sur '{}'.".format(anno_count, chosen_style))
        else:
            print("Aucune annotation dans la sélection.")
    else:
        print("Rien n'était sélectionné.")

    # 4. Définir comme style par défaut (Correction : CurrentDimStyle)
    rs.CurrentDimStyle(chosen_style)
    print("Le style '{}' est désormais le style par défaut.".format(chosen_style))

if __name__ == "__main__":
    update_all_annotation_styles()

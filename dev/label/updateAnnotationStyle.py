# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def update_annotations_v2():
    # 1. Récupérer les styles
    all_styles = rs.DimStyleNames()
    if not all_styles:
        print("Erreur : Aucun style trouvé dans le document.")
        return

    # 2. Préparation pour la ligne de commande (Rhino n'accepte pas d'espaces ici)
    # On crée un dictionnaire : { "Nom_Sans_Espace" : "Nom Réel" }
    style_map = {}
    options_list = []
    
    for s in all_styles:
        # Transformation manuelle pour éviter tout souci de compatibilité
        clean_name = "".join(c if c.isalnum() else "_" for c in s)
        style_map[clean_name] = s
        options_list.append(clean_name)

    current_style = rs.CurrentDimStyle()
    
    # 3. Demander le style via rs.GetString
    msg = "Style actuel: {}. Choisir nouveau style".format(current_style)
    # On affiche les options cliquables
    res = rs.GetString(msg, None, options_list)

    if res is None: 
        return # Utilisateur a fait Echap
    
    # Si l'utilisateur tape ou clique une option, on récupère le vrai nom
    if res in style_map:
        chosen_style = style_map[res]
    elif res == "":
        # Si l'utilisateur fait "Entrée" sans rien taper, on garde l'actuel ou on quitte
        chosen_style = current_style
    else:
        # Si l'utilisateur a tapé un nom manuellement qui n'est pas dans la liste
        if rs.IsDimStyle(res):
            chosen_style = res
        else:
            print("Le style '{}' n'existe pas.".format(res))
            return

    # 4. Traitement de la sélection
    selected_objs = rs.SelectedObjects()
    
    # On vérifie si selected_objs n'est pas None (car rs.SelectedObjects() renvoie None si vide)
    if selected_objs:
        rs.EnableRedraw(False)
        count = 0
        for obj_id in selected_objs:
            # 512 = Constante pour les Annotations (Dimensions, Textes, Leaders)
            if rs.ObjectType(obj_id) == 512:
                try:
                    rs.DimensionStyle(obj_id, chosen_style)
                    count += 1
                except:
                    pass
        rs.EnableRedraw(True)
        if count > 0:
            print("Succès : {} annotations mises à jour.".format(count))
    else:
        print("Aucune sélection : seul le style par défaut est mis à jour.")

    # 5. Définir comme style actuel
    rs.CurrentDimStyle(chosen_style)
    print("Style par défaut : {}".format(chosen_style))

if __name__ == "__main__":
    update_annotations_v2()

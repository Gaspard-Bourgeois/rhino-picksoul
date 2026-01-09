"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 09/01/26
"""
import rhinoscriptsyntax as rs

def copyBlockColor():
    # 1. Sélections
    ids_dst = rs.GetObjects("Sélectionnez les instances de bloc DESTINATION", 4096, preselect=True)
    if not ids_dst: return
    
    id_src = rs.GetObject("Sélectionnez l'instance de bloc SOURCE", 4096, preselect=False)
    if not id_src: return
    
    # Récupérer les noms des définitions de blocs
    # On utilise un set pour éviter de traiter 10 fois le même bloc si on a sélectionné 10 instances
    src_def_name = rs.BlockInstanceName(id_src)
    dst_def_names = list(set([rs.BlockInstanceName(i) for i in ids_dst]))
    
    # Dictionnaires pour l'affichage (cosmétique)
    dict_color_src = {
        0 : 'Color from layer',
        1 : 'Color from object',
        2 : 'Color from material',
        3 : 'Color from parent'
    }

    # ---------------------------------------------------------
    # ÉTAPE 1 : Analyser le bloc SOURCE (Récupérer une liste de styles)
    # ---------------------------------------------------------
    src_objects = rs.BlockObjects(src_def_name)
    src_styles = []

    print("--- Analyse de la source ---")
    for obj in src_objects:
        # On stocke les propriétés de chaque objet du bloc source dans un dictionnaire
        style = {
            'source': rs.ObjectColorSource(obj),
            'color': rs.ObjectColor(obj)
        }
        src_styles.append(style)
        
        # Debug info
        s_name = dict_color_src.get(style['source'], "Inconnu")
        print("Obj Source recupere : {} | {}".format(s_name, style['color']))

    if not src_styles:
        print("Erreur : Le bloc source est vide.")
        return

    # ---------------------------------------------------------
    # ÉTAPE 2 : Appliquer aux blocs DESTINATION
    # ---------------------------------------------------------
    rs.EnableRedraw(False) # Optimisation de vitesse
    
    for dst_name in dst_def_names:
        dst_objects = rs.BlockObjects(dst_name)
        
        if not dst_objects:
            continue

        # Boucle sur les objets de la destination
        for i, dst_obj in enumerate(dst_objects):
            
            # --- C'EST ICI QUE LA MAGIE OPÈRE (Boucle intelligente) ---
            # Si destination a plus d'objets que source, on utilise le modulo (%)
            # pour revenir au début de la liste source.
            # Ex: si src_styles a 2 éléments, l'index 2 devient 0, l'index 3 devient 1, etc.
            src_index = i % len(src_styles)
            
            target_style = src_styles[src_index]
            
            # Application des modifications
            rs.ObjectColorSource(dst_obj, target_style['source'])
            
            # On applique la couleur seulement si la source n'est pas "By Layer" ou "By Parent" 
            # (Bien que techniquement on peut l'appliquer tout le temps, c'est plus propre ainsi)
            if target_style['source'] == 1: # 1 = Color from Object
                rs.ObjectColor(dst_obj, target_style['color'])

    rs.EnableRedraw(True)
    print("Mise a jour terminee sur {} definitions de blocs.".format(len(dst_def_names)))

if __name__ == "__main__": 
    copyBlockColor()

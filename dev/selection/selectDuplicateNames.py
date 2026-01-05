"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 05/01/26
"""
import rhinoscriptsyntax as rs

def SelectDuplicateNames():
    selected = rs.SelectedObjects()
    if not selected: 
        selected = rs.AllObjects()

    name_map = {}
    for obj in selected:
        # Récupère le nom (soit du bloc, soit de l'objet courbe)
        name = rs.ObjectName(obj)
        if name:
            if name not in name_map: name_map[name] = []
            name_map[name].append(obj)

    rs.UnselectAllObjects()
    to_select = []
    count_map = 0
    for name in name_map:
        if len(name_map[name]) > 1: # S'il y a plus d'un objet avec ce nom
            to_select.extend(name_map[name])
            count_map += 1
    
    if to_select: 
        print("{} objet(s) dans {} groupe(s) de nom multiples".format(len(to_select), count_map))
        rs.SelectObjects(to_select)
    else: print("Aucun doublon de nom trouvé dans la sélection.")

SelectDuplicateNames()

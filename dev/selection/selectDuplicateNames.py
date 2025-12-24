import rhinoscriptsyntax as rs

def SelectDuplicateNames():
    selected = rs.SelectedObjects()
    if not selected: 
        print("Veuillez sélectionner des objets d'abord.")
        return

    name_map = {}
    for obj in selected:
        # Récupère le nom (soit du bloc, soit de l'objet courbe)
        name = rs.BlockInstanceName(obj) if rs.IsBlockInstance(obj) else rs.ObjectName(obj)
        if name:
            if name not in name_map: name_map[name] = []
            name_map[name].append(obj)

    rs.UnselectAllObjects()
    to_select = []
    for name in name_map:
        if len(name_map[name]) > 1: # S'il y a plus d'un objet avec ce nom
            to_select.extend(name_map[name])
    
    if to_select: rs.SelectObjects(to_select)
    else: print("Aucun doublon de nom trouvé dans la sélection.")

SelectDuplicateNames()

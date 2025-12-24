import rhinoscriptsyntax as rs

def BlockCountLabels():
    ids = rs.GetObjects("Sélectionnez les blocs pour compter leurs instances", rs.filter.instance)
    if not ids: return

    new_texts = []
    for id in ids:
        name = rs.BlockInstanceName(id)
        count = len(rs.BlockInstances(name)) # Compte total dans le doc
        point = rs.BlockInstanceInsertPoint(id)
        txt_id = rs.AddText(str(count), point, height=1.0)
        if txt_id: new_texts.append(txt_id)
    
    if new_texts: rs.SelectObjects(new_texts)

BlockCountLabels()

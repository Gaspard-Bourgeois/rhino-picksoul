import rhinoscriptsyntax as rs

def BlockNameLabels():
    ids = rs.GetObjects("Sélectionnez les instances de bloc", rs.filter.instance)
    if not ids: return

    new_texts = []
    for id in ids:
        point = rs.BlockInstanceInsertPoint(id)
        # Formule de champ dynamique pour le nom du bloc
        formula = "%<BlockName(\"" + str(id) + "\")>%"
        txt_id = rs.AddText(formula, point, height=1.0)
        if txt_id: new_texts.append(txt_id)
    
    if new_texts: rs.SelectObjects(new_texts)

BlockNameLabels()

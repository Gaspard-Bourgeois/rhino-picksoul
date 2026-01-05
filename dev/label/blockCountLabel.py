"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 05/01/26
"""
import rhinoscriptsyntax as rs

def BlockCountLabels():
    ids = rs.GetObjects("Sélectionnez les blocs pour compter leurs instances", rs.filter.instance, preselect=True)
    if not ids: return
    rs.UnselectAllObjects()
    
    new_texts = []
    for id in ids:
        point = rs.BlockInstanceInsertPoint(id)
        name = rs.BlockInstanceName(id)
        formula = "%<BlockInstanceCount(\"" + str(name) + "\")>%"
        txt_id = rs.AddText(formula, point, height=1.0)
        if txt_id: new_texts.append(txt_id)
    
    if new_texts: rs.SelectObjects(new_texts)

BlockCountLabels()

"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.1
Date: 16/06/2026
"""
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def update_annotations_with_options():
    styles = rs.DimStyleNames()
    if not styles:
        print("Aucun style d'annotation trouvé.")
        return

    current_default = rs.CurrentDimStyle()
    options = [s.replace(" ", "_") for s in styles if s is not None]

    msg = "Style actuel : {}. Choisir le nouveau style".format(current_default)
    res = rs.GetString(msg, current_default, options)
    if res is None:
        return

    chosen_style = None
    if res in styles:
        chosen_style = res
    else:
        for s in styles:
            if s.replace(" ", "_") == res or s == res:
                chosen_style = s
                break

    if not chosen_style:
        print("Style invalide.")
        return

    undo_was_enabled = sc.doc.UndoRecordingEnabled
    sc.doc.UndoRecordingEnabled = False

    try:
        selected_objs = rs.SelectedObjects()

        if selected_objs:
            rs.EnableRedraw(False)
            anno_count = 0
            for obj_id in selected_objs:
                if rs.ObjectType(obj_id) == 512:
                    rs.DimensionStyle(obj_id, chosen_style)
                    anno_count += 1
            rs.EnableRedraw(True)

            if anno_count > 0:
                print(u"Succès : {} annotation(s) mise(s) à jour sur '{}'.".format(anno_count, chosen_style))
            else:
                print(u"Aucune annotation trouvée dans la sélection.")
        else:
            print(u"Aucune sélection. Modification du style par défaut uniquement.")

        rs.CurrentDimStyle(chosen_style)
        print(u"Style par défaut défini sur : {}".format(chosen_style))

    finally:
        sc.doc.UndoRecordingEnabled = undo_was_enabled

if __name__ == "__main__":
    update_annotations_with_options()
"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.1
Date: 16/06/2026
"""
# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

def update_annotations():
    styles = rs.DimStyleNames()
    if not styles:
        print(u"Aucun style d'annotation trouv\xe9.")
        return

    current_default = rs.CurrentDimStyle()

    # Utilise le style passé par sc.sticky, sinon demande à l'utilisateur
    chosen_style = sc.sticky.get("dimstyle_target", None)
    sc.sticky["dimstyle_target"] = None  # reset immédiat pour ne pas polluer les appels suivants

    if not chosen_style:
        options = [s.replace(" ", "_") for s in styles if s is not None]
        msg = u"Style actuel : " + current_default + u". Choisir le nouveau style"
        res = rs.GetString(msg, current_default, options)
        if res is None:
            return

        if res in styles:
            chosen_style = res
        else:
            for s in styles:
                if s.replace(" ", "_") == res or s == res:
                    chosen_style = s
                    break

    if not chosen_style:
        print(u"Style invalide.")
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
                print(u"Succ\xe8s : %d annotation(s) mise(s) \xe0 jour sur '%s'." % (anno_count, chosen_style))
            else:
                print(u"Aucune annotation trouv\xe9e dans la s\xe9lection.")
        else:
            print(u"Aucune s\xe9lection. Modification du style par d\xe9faut uniquement.")

        rs.CurrentDimStyle(chosen_style)
        print(u"Style par d\xe9faut d\xe9fini sur : " + chosen_style)

    finally:
        sc.doc.UndoRecordingEnabled = undo_was_enabled

update_annotations()
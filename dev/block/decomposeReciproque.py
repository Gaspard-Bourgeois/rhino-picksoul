# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

def create_pose_block():
    """Crée le bloc 'Pose' (trièdre RVB) s'il n'existe pas."""
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        items = []
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
        rs.EnableRedraw(True)
    return "Pose"

def get_base_name(block_name):
    """
    Extrait le nom racine d'un bloc.
    Si le bloc se nomme 'toto#3', retourne 'toto'.
    Si le bloc se nomme 'toto',   retourne 'toto'.
    """
    if "#" in block_name:
        return block_name.split("#")[0]
    return block_name

def get_next_instance_index(base_name):
    """
    Trouve l'indice unique suivant pour un base_name donné dans le document.
    Parcourt tous les UserTexts BlockNameLevel_X et cherche les valeurs
    dont la partie racine (avant #) correspond à base_name.
    """
    max_index = 0
    all_objs = rs.AllObjects()
    if not all_objs:
        return 1
    for obj in all_objs:
        keys = rs.GetUserText(obj)
        if keys:
            for key in keys:
                if key.startswith("BlockNameLevel_"):
                    value = rs.GetUserText(obj, key)
                    if value and "#" in value:
                        try:
                            name_part, index_part = value.split("#", 1)
                            if name_part == base_name:
                                idx = int(index_part)
                                if idx > max_index:
                                    max_index = idx
                        except ValueError:
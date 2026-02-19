# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import uuid

def create_pose_block():
    if not rs.IsBlock("Pose"):
        items = [
            rs.AddLine([0,0,0], [1,0,0]),
            rs.AddLine([0,0,0], [0,1,0]),
            rs.AddLine([0,0,0], [0,0,1])
        ]
        rs.ObjectColor(items[0], [255,0,0])
        rs.ObjectColor(items[1], [0,255,0])
        rs.ObjectColor(items[2], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
    return "Pose"

def explode_any(obj_id):
    if rs.IsPolysurface(obj_id): return rs.ExplodePolysurfaces(obj_id, True)
    if rs.IsCurve(obj_id) and not rs.IsLine(obj_id): return rs.ExplodeCurves(obj_id, True)
    if rs.IsMesh(obj_id): return rs.ExplodeMesh(obj_id, True)
    return None

def decompose_reciproque():
    object_ids = rs.GetObjects("Sélectionnez les objets ou blocs à décomposer", preselect=True)
    if not object_ids: return

    create_pose_block()
    rs.EnableRedraw(False)
    
    decomp_id = str(uuid.uuid4()) # Identifiant unique pour cette décomposition
    all_results = []

    for obj_id in object_ids:
        if rs.IsBlockInstance(obj_id):
            block_name = rs.BlockInstanceName(obj_id)
            block_xform = rs.BlockInstanceXform(obj_id)
            
            # Récupérer le niveau actuel (si c'est déjà un bloc imbriqué décomposé)
            parent_level = rs.GetUserText(obj_id, "NestingLevel")
            current_level = int(parent_level) if parent_level else 0
            
            exploded_items = rs.ExplodeBlockInstance(obj_id)
            
            # Créer la Pose
            pose_id = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(pose_id, block_xform)
            
            # Marquer la Pose et les éléments décomposés
            for item in exploded_items + [pose_id]:
                rs.SetUserText(item, "ReciproqueID", decomp_id)
                rs.SetUserText(item, "OriginalBlockName", block_name)
                rs.SetUserText(item, "NestingLevel", str(current_level))
            
            all_results.extend(exploded_items + [pose_id])
        else:
            geo = explode_any(obj_id)
            if geo: all_results.extend(geo)
            else: all_results.append(obj_id)

    rs.UnselectAllObjects()
    rs.SelectObjects(all_results)
    rs.EnableRedraw(True)

if __name__ == "__main__":
    decompose_reciproque()

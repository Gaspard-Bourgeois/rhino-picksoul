# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc

def create_pose_block():
    """Crée le bloc 'Pose' s'il n'existe pas."""
    if not rs.IsBlock("Pose"):
        items = []
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
    return "Pose"

def generic_explode(obj_id):
    """
    Explose une géométrie de manière générique via Rhino.Geometry.
    """
    # 1. Récupérer la géométrie à partir du GUID
    geo = rs.coercegeometry(obj_id)
    if not geo: return None
    
    exploded_geos = []

    # 2. Vérifier si la géométrie possède une méthode Explode
    # Les Breps (polysurfaces) et les Curves ont cette méthode
    if hasattr(geo, "Explode"):
        exploded_geos = geo.Explode()
    
    # Cas particulier : Les maillages (Mesh) utilisent ExplodeAtUnweldedEdges ou similaire
    elif isinstance(geo, rg.Mesh):
        exploded_geos = geo.ExplodeAtUnweldedEdges()

    if not exploded_geos:
        return None

    # 3. Ajouter les nouvelles géométries au document et récupérer leurs nouveaux GUIDs
    new_ids = []
    for g in exploded_geos:
        new_id = sc.doc.Objects.Add(g)
        if new_id: new_ids.append(new_id)
    
    # Supprimer l'objet original si l'explosion a réussi
    if new_ids:
        rs.DeleteObject(obj_id)
        
    return new_ids

def decompose_reciproque():
    object_ids = rs.GetObjects("Sélectionnez les objets à décomposer", preselect=True)
    if not object_ids: return

    all_results = []
    create_pose_block()
    rs.EnableRedraw(False)
    
    for obj_id in object_ids:
        # TRAITEMENT DES BLOCS
        if rs.IsBlockInstance(obj_id):
            name = rs.BlockInstanceName(obj_id)
            xform = rs.BlockInstanceXform(obj_id)
            ins_pt = rs.BlockInstanceInsertPoint(obj_id)
            
            exploded_items = rs.ExplodeBlockInstance(obj_id)
            
            origin_obj = next((item for item in exploded_items if rs.IsBlockInstance(item) 
                              and rs.BlockInstanceInsertPoint(item) == ins_pt), None)
            
            if not origin_obj:
                origin_obj = rs.InsertBlock("Pose", [0,0,0])
                rs.TransformObject(origin_obj, xform)
                exploded_items.append(origin_obj)

            rs.SetUserText(origin_obj, "OriginalBlockName", name)
            
            group = rs.AddGroup()
            rs.AddObjectsToGroup(exploded_items, group)
            all_results.extend(exploded_items)

        # TRAITEMENT GÉNÉRIQUE (Polysurfaces, Courbes, etc.)
        else:
            new_parts = generic_explode(obj_id)
            if new_parts:
                group = rs.AddGroup()
                rs.AddObjectsToGroup(new_parts, group)
                all_results.extend(new_parts)
            else:
                all_results.append(obj_id)

    rs.UnselectAllObjects()
    if all_results: rs.SelectObjects(all_results)
    rs.EnableRedraw(True)

if __name__ == "__main__":
    decompose_reciproque()

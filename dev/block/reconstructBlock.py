# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc

# --- UTILS DE STABILISATION (Initialement dans editblockxform) ---

def update_block_def(block_name, objects, xform_to_origin):
    """Met à jour la définition en déplaçant les objets vers l'origine."""
    # Transformer les objets vers l'origine du bloc
    rs.TransformObjects(objects, xform_to_origin)
    # Redéfinir le bloc (écrase l'ancien)
    return rs.AddBlock(objects, [0,0,0], block_name, True)

def PropagateUpwardCompensation(block_name, xform_comp, visited=None):
    if visited is None: visited = set()
    parents = rs.BlockContainers(block_name)
    if not parents: return
    for p_name in parents:
        if p_name in visited: continue
        visited.add(p_name)
        # On compense chaque instance de l'enfant dans la def du parent
        p_def = sc.doc.InstanceDefinitions.Find(p_name, False)
        for obj in p_def.GetObjects():
            if rs.IsBlockInstance(obj.Id) and rs.BlockInstanceName(obj.Id) == block_name:
                # Accès direct RhinoCommon pour modifier la géométrie interne
                geom = obj.Geometry.Duplicate()
                geom.Transform(xform_comp)
                sc.doc.InstanceDefinitions.ModifyGeometry(p_def.Index, [geom], [obj.Attributes])
        PropagateUpwardCompensation(p_name, xform_comp, visited)

# --- FONCTION PRINCIPALE ---

def rebuild_reciproque():
    selected = rs.GetObjects("Sélectionnez les éléments à reconstruire", preselect=True)
    if not selected: return

    # 1. Identifier les Poses et les trier par NestingLevel décroissant
    poses = []
    for obj in selected:
        if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
            name = rs.GetUserText(obj, "OriginalBlockName")
            level = rs.GetUserText(obj, "NestingLevel")
            d_id = rs.GetUserText(obj, "ReciproqueID")
            if name and d_id:
                poses.append({"id": obj, "name": name, "level": int(level or 0), "decomp_id": d_id})

    if not poses:
        print("Aucun marqueur 'Pose' trouvé."); return

    poses.sort(key=lambda x: x["level"], reverse=True)
    rs.EnableRedraw(False)

    for p in poses:
        # Trouver les frères (objets ayant le même ReciproqueID)
        content = [obj for obj in selected if rs.GetUserText(obj, "ReciproqueID") == p["decomp_id"] and obj != p["id"]]
        
        # Calculer les matrices
        t_pose = rs.BlockInstanceXform(p["id"])
        x_def = rs.XformInverse(t_pose) # Vers l'origine
        x_comp = t_pose                # Compensation pour les autres instances

        # 2. Mettre à jour la définition
        update_block_def(p["name"], content, x_def)

        # 3. Stabiliser les Blocs Parents (Upward)
        PropagateUpwardCompensation(p["name"], x_comp)

        # 4. Stabiliser les Instances Sœurs dans le document
        sisters = rs.BlockInstances(p["name"])
        for s in sisters:
            t_old = rs.BlockInstanceXform(s)
            # Si c'est notre Pose actuelle, on la remplace par l'instance à l'identité
            if s == p["id"]:
                # (Techniquement la pose est déjà l'instance, mais on veut s'assurer du xform)
                rs.BlockInstanceXform(s, rs.XformIdentity()) 
            else:
                # Pour les autres, on applique la compensation
                new_t = rs.XformMultiply(t_old, x_comp)
                rs.BlockInstanceXform(s, new_t)

        # Nettoyage des UserText pour les objets réintégrés
        for obj in content:
            rs.SetUserText(obj, "ReciproqueID", "")
            rs.SetUserText(obj, "NestingLevel", "")

    rs.EnableRedraw(True)
    print("Reconstruction terminée avec stabilisation du document.")

if __name__ == "__main__":
    rebuild_reciproque()

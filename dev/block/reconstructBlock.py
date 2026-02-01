# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import re

def get_bbox_center(obj_id):
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return Rhino.Geometry.Point3d.Origin
    return (bbox[0] + bbox[6]) / 2.0

def ensure_layer(layer_name):
    if not rs.IsLayer(layer_name): rs.AddLayer(layer_name)
    return layer_name

def robust_update_block(name, base_point, ids):
    """
    Met à jour la définition du bloc sans supprimer les instances.
    """
    base_pt = Rhino.Geometry.Point3d(base_point[0], base_point[1], base_point[2])
    
    # 1. Préparer les géométries (Duplication réelle pour détacher du document)
    geoms = []
    attrs = []
    for g_id in ids:
        obj = sc.doc.Objects.Find(g_id)
        if obj:
            # Sécurité anti-circularité : on ne peut pas mettre le bloc dans lui-même
            if isinstance(obj, Rhino.DocObjects.InstanceObject):
                if obj.InstanceDefinition.Name == name:
                    continue
            geoms.append(obj.Geometry.Duplicate())
            attrs.append(obj.Attributes.Duplicate())

    if not geoms: return False

    # 2. Chercher la définition existante
    idef_index = sc.doc.InstanceDefinitions.Find(name, True)
    
    if idef_index >= 0:
        # EXISTE : On modifie la géométrie existante. 
        # Cela met à jour TOUTES les instances dans le document instantanément.
        return sc.doc.InstanceDefinitions.ModifyGeometry(idef_index, geoms, attrs)
    else:
        # NOUVEAU : On crée la définition
        return sc.doc.InstanceDefinitions.Add(name, "", base_pt, geoms, attrs) >= 0

def rebuild_reciproque():
    objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not objs: return

    origin_obj = None
    block_name = None
    xform = None
    needs_indexing = False

    # 1. Recherche du pivot et du nom via UserText
    for o in objs:
        val = rs.GetUserText(o, "OriginalBlockName")
        if val:
            origin_obj, block_name = o, val
            if rs.IsBlockInstance(o): xform = rs.BlockInstanceXform(o)
            break

    # 2. Gestion de l'origine si non trouvée
    if not origin_obj:
        ref = rs.GetObject("Origine non trouvée. Sélectionnez un pivot (Entrée pour Monde)")
        if ref:
            if rs.IsBlockInstance(ref):
                block_name = rs.BlockInstanceName(ref)
                xform = rs.BlockInstanceXform(ref)
                if block_name == "Pose": 
                    block_name, needs_indexing = "NouveauBloc", True
            else:
                block_name, needs_indexing = "NouveauBloc", True
                xform = rs.XformTranslation(get_bbox_center(ref))
        else:
            block_name, needs_indexing = "NouveauBloc", True
            xform = rs.XformIdentity()

        # Logique de nommage _base / _contain
        if "_base" in block_name.lower():
            block_name = re.sub('(?i)_base', '', block_name)
        elif not block_name.lower().endswith("_contain"):
            block_name += "_contain"

        # Vérification d'existence et indexation (Correction de la fonctionnalité cassée)
        if needs_indexing or rs.IsBlock(block_name):
            base_search_name = block_name
            # Si le nom existe déjà et qu'on a besoin d'un nouveau bloc indexé
            if rs.IsBlock(base_search_name) and needs_indexing:
                for i in range(1, 100):
                    temp = "{}_{:02d}".format(base_search_name, i)
                    if not rs.IsBlock(temp):
                        block_name = temp
                        break
    
    if not block_name: return

    # 3. Confirmation si le bloc existe déjà
    confirm = "Oui"
    if rs.IsBlock(block_name):
        # On demande confirmation car ModifyGeometry est irréversible (sauf via Undo)
        res = rs.MessageBox("Le bloc '{}' existe. Mettre à jour toutes ses occurrences ?".format(block_name), 4 + 32, "Mise à jour de bloc")
        confirm = "Oui" if res == 6 else "Non"

    if confirm == "Oui":
        layer = ensure_layer("Blocs")
        inv_xf = rs.XformInverse(xform)
        temp_ids = []
        
        rs.EnableRedraw(False)
        try:
            # Préparer les objets pour la définition (déplacer au 0,0,0 local)
            for o in objs:
                copy = rs.CopyObject(o)
                rs.ObjectLayer(copy, layer)
                rs.TransformObject(copy, inv_xf)
                temp_ids.append(copy)

            # Mise à jour de la définition (ModifyGeometry)
            if robust_update_block(block_name, [0,0,0], temp_ids):
                # Remplacer les objets sélectionnés par une instance du bloc mis à jour
                new_inst = rs.InsertBlock(block_name, [0,0,0])
                rs.TransformObject(new_inst, xform)
                
                # Nettoyage
                rs.DeleteObjects(objs)
                rs.SelectObject(new_inst)
                print("Succès : Bloc '{}' mis à jour dans tout le document.".format(block_name))
            else:
                print("Erreur : La mise à jour de la définition a échoué.")
        finally:
            # On supprime toujours les objets temporaires créés pour la définition
            if temp_ids: rs.DeleteObjects(temp_ids)
            rs.EnableRedraw(True)
    else:
        print("Opération annulée.")

if __name__ == "__main__":
    rebuild_reciproque()

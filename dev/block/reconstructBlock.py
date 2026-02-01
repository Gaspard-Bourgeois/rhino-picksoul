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

def safe_redefine_block(name, base_point, ids, delete_input):
    """
    Redéfinit ou crée un bloc de manière atomique.
    """
    # 1. Collecte des géométries
    geoms = []
    attrs = []
    for g_id in ids:
        obj = sc.doc.Objects.Find(g_id)
        if obj:
            # Sécurité anti-circularité : on ne peut pas mettre le bloc dans lui-même
            if isinstance(obj, Rhino.DocObjects.InstanceObject):
                if obj.InstanceDefinition.Name == name:
                    continue 
            geoms.append(obj.Geometry)
            attrs.append(obj.Attributes)
    
    if not geoms: return False

    base_pt = Rhino.Geometry.Point3d(base_point[0], base_point[1], base_point[2])
    
    # 2. Recherche de la définition existante
    idef_index = sc.doc.InstanceDefinitions.Find(name, True)
    
    if idef_index >= 0:
        # MISE À JOUR (Redéfinition sans casser les instances existantes)
        success = sc.doc.InstanceDefinitions.ModifyGeometry(idef_index, geoms, attrs)
    else:
        # CRÉATION
        new_idx = sc.doc.InstanceDefinitions.Add(name, "", base_pt, geoms, attrs)
        success = new_idx >= 0

    if success and delete_input:
        for g_id in ids: sc.doc.Objects.Delete(g_id, True)
    
    return success

def rebuild_reciproque():
    objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not objs: return

    origin_obj = None
    block_name = None
    xform = None
    needs_indexing = False

    # 1. Identification de l'origine (Pose ou Key)
    for o in objs:
        val = rs.GetUserText(o, "OriginalBlockName")
        if val:
            origin_obj, block_name = o, val
            if rs.IsBlockInstance(o): xform = rs.BlockInstanceXform(o)
            break

    # 2. Fallback si aucune Pose n'est trouvée
    if not origin_obj:
        ref = rs.GetObject("Origine non trouvée. Sélectionnez un pivot (ou Entrée pour Monde)")
        if ref:
            if rs.IsBlockInstance(ref):
                raw_name = rs.BlockInstanceName(ref)
                xform = rs.BlockInstanceXform(ref)
                if raw_name == "Pose":
                    block_name, needs_indexing = "NouveauBloc", True
                else:
                    block_name = raw_name
            else:
                block_name, needs_indexing = "NouveauBloc", True
                xform = rs.XformTranslation(get_bbox_center(ref))
        else:
            block_name, needs_indexing = "NouveauBloc", True
            xform = rs.XformIdentity()

        # Logique de nommage : _base / _contain
        if "_base" in block_name.lower():
            block_name = re.sub('(?i)_base', '', block_name)
        elif not block_name.lower().endswith("_contain"):
            block_name += "_contain"

        # Indexation (évite les doublons)
        if needs_indexing or rs.IsBlock(block_name):
            free_name = block_name
            for i in range(1, 100):
                temp = "{}_{:02d}".format(block_name, i)
                if not rs.IsBlock(temp):
                    free_name = temp
                    break
            block_name = free_name

    if not block_name: return

    # 3. Action
    confirm = "Oui"
    if rs.IsBlock(block_name):
        confirm = rs.GetString("Mettre à jour le bloc '{}' ?".format(block_name), "Oui", ["Oui", "Non"])

    if confirm == "Oui":
        layer = ensure_layer("Blocs")
        inv_xf = rs.XformInverse(xform)
        temp_ids = []
        
        rs.EnableRedraw(False)
        for o in objs:
            copy = rs.CopyObject(o)
            rs.ObjectLayer(copy, layer)
            rs.TransformObject(copy, inv_xf)
            temp_ids.append(copy)

        if safe_redefine_block(block_name, [0,0,0], temp_ids, delete_input=True):
            # On insère une nouvelle instance au point final
            new_inst = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            rs.DeleteObjects(objs)
            rs.SelectObject(new_inst)
            print("Succès : Bloc '{}' généré.".format(block_name))
        else:
            print("Erreur : La redéfinition a échoué (vérifiez si le bloc est verrouillé).")
            rs.DeleteObjects(temp_ids) # Nettoyage
        rs.EnableRedraw(True)

if __name__ == "__main__":
    rebuild_reciproque()

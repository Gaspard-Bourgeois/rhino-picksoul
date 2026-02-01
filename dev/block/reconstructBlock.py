# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import re
import time

def get_bbox_center(obj_id):
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return Rhino.Geometry.Point3d.Origin
    return (bbox[0] + bbox[6]) / 2.0

def ensure_layer(layer_name):
    if not rs.IsLayer(layer_name): rs.AddLayer(layer_name)
    return layer_name

def force_redefine_block(name, base_point, ids):
    """
    Approche radicale : Renomme l'existant pour libérer le nom, 
    puis crée une nouvelle définition propre.
    """
    base_pt = Rhino.Geometry.Point3d(base_point[0], base_point[1], base_point[2])
    
    # 1. Collecte des géométries réelles (pas les GUIDs)
    geoms = []
    attrs = []
    for g_id in ids:
        obj = sc.doc.Objects.Find(g_id)
        if obj:
            geoms.append(obj.Geometry.Duplicate()) # On duplique pour éviter les liens
            attrs.append(obj.Attributes.Duplicate())

    if not geoms: return False

    # 2. Libérer le nom si déjà utilisé
    old_def = sc.doc.InstanceDefinitions.Find(name, True)
    if old_def:
        # On renomme l'ancien bloc avec un timestamp pour éviter tout conflit
        temp_name = "OLD_{}_{}".format(name, int(time.time()))
        sc.doc.InstanceDefinitions.Modify(old_def.Index, temp_name, old_def.Description, True)

    # 3. Création de la nouvelle définition
    # On utilise la méthode Add de la table des définitions
    new_idx = sc.doc.InstanceDefinitions.Add(name, "Rebuilt via Python", base_pt, geoms, attrs)
    
    if new_idx >= 0:
        # On peut maintenant supprimer l'ancienne définition renommée (si elle existait)
        if old_def:
            sc.doc.InstanceDefinitions.Delete(old_def.Index, True, True)
        return True
    return False

def rebuild_reciproque():
    objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not objs: return

    origin_obj = None
    block_name = None
    xform = None
    needs_indexing = False

    # 1. Identification du pivot et du nom
    for o in objs:
        val = rs.GetUserText(o, "OriginalBlockName")
        if val:
            origin_obj, block_name = o, val
            if rs.IsBlockInstance(o): xform = rs.BlockInstanceXform(o)
            break

    # 2. Fallback (Point pivot manuel)
    if not origin_obj:
        ref = rs.GetObject("Origine non trouvée. Sélectionnez un pivot (Entrée pour Monde)")
        if ref:
            if rs.IsBlockInstance(ref):
                block_name, xform = rs.BlockInstanceName(ref), rs.BlockInstanceXform(ref)
                if block_name == "Pose": block_name, needs_indexing = "NouveauBloc", True
            else:
                block_name, needs_indexing = "NouveauBloc", True
                xform = rs.XformTranslation(get_bbox_center(ref))
        else:
            block_name, needs_indexing = "NouveauBloc", True
            xform = rs.XformIdentity()

        # Nettoyage du nom
        if "_base" in block_name.lower():
            block_name = re.sub('(?i)_base', '', block_name)
        elif not block_name.lower().endswith("_contain"):
            block_name += "_contain"

        # Gestion des doublons
        if needs_indexing or rs.IsBlock(block_name):
            temp_name = block_name
            for i in range(1, 100):
                check_name = "{}_{:02d}".format(block_name, i)
                if not rs.IsBlock(check_name):
                    temp_name = check_name
                    break
            block_name = temp_name

    if not block_name: return

    # 3. Exécution
    layer = ensure_layer("Blocs")
    inv_xf = rs.XformInverse(xform)
    temp_ids = []
    
    rs.EnableRedraw(False)
    
    # Création des copies locales pour le bloc
    for o in objs:
        copy = rs.CopyObject(o)
        rs.ObjectLayer(copy, layer)
        rs.TransformObject(copy, inv_xf)
        temp_ids.append(copy)

    # Appel de la fonction de création forcée
    if force_redefine_block(block_name, [0,0,0], temp_ids):
        # On insère le nouveau bloc
        new_inst = rs.InsertBlock(block_name, [0,0,0])
        rs.TransformObject(new_inst, xform)
        
        # Nettoyage
        rs.DeleteObjects(objs)
        rs.DeleteObjects(temp_ids)
        rs.SelectObject(new_inst)
        print("Bloc '{}' reconstruit avec succès (Table Reset).".format(block_name))
    else:
        print("ERREUR FATALE : Impossible de créer le bloc '{}'.".format(block_name))
        rs.DeleteObjects(temp_ids)
        
    rs.EnableRedraw(True)

if __name__ == "__main__":
    rebuild_reciproque()

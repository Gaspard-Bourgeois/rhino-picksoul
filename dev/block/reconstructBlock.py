# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

def get_bbox_center(obj_id):
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return [0,0,0]
    pt_min = bbox[0]
    pt_max = bbox[6]
    return [(pt_min[i] + pt_max[i]) / 2.0 for i in range(3)]

def ensure_layer(layer_name):
    if not rs.IsLayer(layer_name):
        rs.AddLayer(layer_name)
    return layer_name

def redefine_block(name, base_point, ids, delete_input):
    """
    Version robuste pour créer OU mettre à jour un bloc sans perdre les instances.
    """
    # Récupérer les géométries et leurs attributs
    geometries = []
    attributes = []
    for obj_id in ids:
        rh_obj = sc.doc.Objects.Find(obj_id)
        if rh_obj:
            geometries.append(rh_obj.Geometry)
            attributes.append(rh_obj.Attributes)

    # Trouver si le bloc existe déjà
    index = sc.doc.InstanceDefinitions.Find(name, True)
    
    if index < 0:
        # Le bloc n'existe pas, on le crée normalement
        return rs.AddBlock(ids, base_point, name, delete_input)
    else:
        # Le bloc existe, on modifie sa définition (Redéfinition)
        # On définit le point de base (0,0,0 local)
        base_point_rg = Rhino.Geometry.Point3d(base_point[0], base_point[1], base_point[2])
        
        success = sc.doc.InstanceDefinitions.ModifyGeometry(index, geometries, attributes)
        
        if success and delete_input:
            rs.DeleteObjects(ids)
        return success

def rebuild_reciproque():
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None
    xform = None
    needs_indexing = False

    # 1. Recherche de l'origine via UserText
    for obj in initial_objs:
        val = rs.GetUserText(obj, "OriginalBlockName")
        if val:
            origin_obj = obj
            block_name = val
            if rs.IsBlockInstance(obj):
                xform = rs.BlockInstanceXform(obj)
            break

    # 2. Gestion de l'absence d'origine automatique
    if not origin_obj:
        ref_id = rs.GetObject("Origine non trouvée. Sélectionnez une référence (ou Entrée pour Monde)")
        if ref_id:
            if rs.IsBlockInstance(ref_id):
                raw_name = rs.BlockInstanceName(ref_id)
                xform = rs.BlockInstanceXform(ref_id)
                if raw_name == "Pose":
                    block_name = "NouveauBloc"
                    needs_indexing = True
                else:
                    block_name = raw_name
            else:
                block_name = "NouveauBloc"
                xform = rs.XformTranslation(get_bbox_center(ref_id))
                needs_indexing = True
        else:
            block_name = "NouveauBloc"
            xform = rs.XformIdentity()
            needs_indexing = True

        # Logique de nommage _base / _contain
        if "_base" in block_name.lower():
            import re
            block_name = re.sub('(?i)_base', '', block_name)
        else:
            if not block_name.endswith("_contain"):
                block_name = block_name + "_contain"
        
        if needs_indexing:
            free_name = block_name
            if rs.IsBlock(free_name):
                for i in range(1, 100):
                    temp_name = "{}_{:02d}".format(block_name, i)
                    if not rs.IsBlock(temp_name):
                        free_name = temp_name
                        break
            block_name = free_name
    
    if not block_name: return

    # 3. Confirmation si redefinition
    confirm = "Oui"
    if rs.IsBlock(block_name):
        msg = "Le bloc '{}' existe déjà. Mettre à jour sa définition ?".format(block_name)
        confirm = rs.GetString(msg, "Oui", ["Oui", "Non"])
    
    if confirm == "Oui":
        target_layer = ensure_layer("Blocs")
        inv_xform = rs.XformInverse(xform)
        new_geometries = []
        
        rs.EnableRedraw(False)
        
        # Création des copies transformées pour le bloc
        for o in initial_objs:
            # On conserve tout (y compris l'instance Pose)
            copy = rs.CopyObject(o)
            rs.ObjectLayer(copy, target_layer)
            rs.TransformObject(copy, inv_xform)
            new_geometries.append(copy)

        # 4. Utilisation de la fonction de redéfinition robuste
        res = redefine_block(block_name, [0,0,0], new_geometries, delete_input=True)
        
        if res:
            # Remplacer les objets initiaux par une instance du bloc
            new_instance = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(new_instance, xform)
            
            rs.DeleteObjects(initial_objs)
            rs.UnselectAllObjects()
            rs.SelectObject(new_instance)
            print("Bloc '{}' reconstruit avec succès.".format(block_name))
        else:
            print("Erreur : La création/mise à jour du bloc a échoué.")
            
        rs.EnableRedraw(True)
    else:
        print("Opération annulée.")

if __name__ == "__main__":
    rebuild_reciproque()

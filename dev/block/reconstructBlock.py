# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def get_bbox_center(obj_id):
    """Calcule le centre d'une BoundingBox."""
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return [0,0,0]
    pt_min = bbox[0]
    pt_max = bbox[6]
    return [(pt_min[i] + pt_max[i]) / 2.0 for i in range(3)]

def ensure_layer(layer_name):
    """Vérifie si le calque existe, sinon le crée."""
    if not rs.IsLayer(layer_name):
        rs.AddLayer(layer_name)
    return layer_name

def rebuild_reciproque():
    # 1. Sélection des objets
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None
    xform = None
    block_names_in_doc = rs.BlockNames()
    needs_indexing = False

    # 2. Recherche de l'objet "Pose" ou origine via la clé UserText
    for obj in initial_objs:
        val = rs.GetUserText(obj, "OriginalBlockName")
        if val:
            origin_obj = obj
            block_name = val
            if rs.IsBlockInstance(obj):
                xform = rs.BlockInstanceXform(obj)
            break

    # 3. Gestion de l'origine si non trouvée automatiquement
    if not origin_obj:
        ref_id = rs.GetObject("Origine non trouvée. Sélectionnez une référence (ou Entrée pour Monde)")
        
        if ref_id:
            if rs.IsBlockInstance(ref_id):
                raw_name = rs.BlockInstanceName(ref_id)
                xform = rs.BlockInstanceXform(ref_id)
                
                # Si c'est un bloc "Pose" choisi manuellement sans UserText
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

        # --- LOGIQUE DE RENOMMAGE (Correction 3 & 4) ---
        # Retirer _base ou ajouter _contain
        if "_base" in block_name.lower():
            # Remplace toutes les occurrences de _base (insensible à la casse)
            import re
            block_name = re.sub('(?i)_base', '', block_name)
        else:
            block_name = block_name + "_contain"
        
        # Indexation seulement si nécessaire (Pose choisi sans nom prédéfini ou nouveau bloc)
        if needs_indexing:
            free_name = block_name
            if free_name in block_names_in_doc:
                for i in range(1, 100):
                    temp_name = "{}_{:02d}".format(block_name, i)
                    if temp_name not in block_names_in_doc:
                        free_name = temp_name
                        break
            block_name = free_name
    
    if not block_name: return

    # 4. Vérification et prévisualisation
    confirm = "Oui"
    temp_instance = None
    if rs.IsBlock(block_name):
        temp_instance = rs.InsertBlock(block_name, [0,0,0])
        rs.TransformObject(temp_instance, xform)
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        msg = "Le bloc '{}' existe déjà. Mettre à jour sa définition ?".format(block_name)
        confirm = rs.GetString(msg, "Oui", ["Oui", "Non"])
    
    if confirm == "Oui":
        # Préparation du calque cible (Correction 2)
        target_layer = ensure_layer("Blocs")
        
        # Préparation de la géométrie
        inv_xform = rs.XformInverse(xform)
        new_geometries = []
        
        rs.EnableRedraw(False)
        for o in initial_objs:
            # Note: On ne saute plus l'instance "Pose" (Correction 1)
            copy = rs.CopyObject(o)
            
            # Placer les éléments sur le calque "Blocs"
            rs.ObjectLayer(copy, target_layer)
            
            rs.TransformObject(copy, inv_xform)
            new_geometries.append(copy)

        # 5. Création/Mise à jour du bloc
        rs.AddBlock(new_geometries, [0,0,0], block_name, delete_input=True)
        
        if not temp_instance:
            temp_instance = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(temp_instance, xform)
        
        # 6. Nettoyage final
        rs.DeleteObjects(initial_objs)
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        rs.EnableRedraw(True)
        
        print("Bloc '{}' généré sur le calque 'Blocs'.".format(block_name))
    else:
        if temp_instance: rs.DeleteObject(temp_instance)
        print("Opération annulée.")

if __name__ == "__main__":
    rebuild_reciproque()

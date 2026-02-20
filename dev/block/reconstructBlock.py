# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def get_bbox_center(obj_id):
    """Calcule le centre d'une BoundingBox sans Rhino.Geometry."""
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return [0,0,0]
    # bbox[0] est le min, bbox[6] est le max
    pt_min = bbox[0]
    pt_max = bbox[6]
    return [
        (pt_min[0] + pt_max[0]) / 2.0,
        (pt_min[1] + pt_max[1]) / 2.0,
        (pt_min[2] + pt_max[2]) / 2.0
    ]

def rebuild_reciproque():
    # 1. Sélection des objets
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    origin_obj = None
    block_name = None
    xform = None
    block_names_in_doc = rs.BlockNames()

    # TODO : on classe les objets sélectionné à partir de la hierarchie de bloc contenu dans les UserTexts du type BlockNameLeve_X=block_name#Y, X le niveau hiérarchique et Y l'indice de l'instance, ceux qui n'ont pas d'usertext sont classé au niveau le plus haut
    # 2. Recherche de l'objet "Pose" ou origine via la clé UserText
    # TODO : on classe également tous les objets "Pose" de la selection
    for obj in initial_objs:
        val = rs.GetUserText(obj, "OriginalBlockName")
        if val:
            origin_obj = obj
            block_name = val
            if rs.IsBlockInstance(obj):
                xform = rs.BlockInstanceXform(obj)
            break

    # 3. Gestion de l'absence d'origine identifiée
    #TODO: si plusieurs niveau ne contiennent pas d'origine identifié, alors on sélectionne les objets du niveau le plus bas et on arrête le script, de manière à ce que l'on puisse le relancer pour définir l'origine.
    if not origin_obj:
        ref_id = rs.GetObject("Origine non trouvée. Sélectionnez une référence (ou Entrée pour Monde)")
        if ref_id:
            if rs.IsBlockInstance(ref_id):
                block_name = rs.BlockInstanceName(ref_id)
                xform = rs.BlockInstanceXform(ref_id)
            else:
                # Si c'est un objet normal, on prend son centre et on crée une translation
                block_name = "NouveauBloc"
                center = get_bbox_center(ref_id)
                xform = rs.XformTranslation(center)
        else:
            block_name = "NouveauBloc"
            xform = rs.XformIdentity()

        # Nettoyage du nom (suffixes _base ou _01)
        if block_name.lower().endswith("_base"):
            block_name = block_name[:-5]
        
        # Supprime le suffixe de copie type _01, _02
        if len(block_name) > 3 and block_name[-3] == "_" and block_name[-2:].isdigit():
            block_name = block_name[:-3]
        
        # Recherche d'un nom libre
        free_name = block_name
        if free_name in block_names_in_doc:
            for i in range(1, 100):
                temp_name = "{}_{:02d}".format(block_name, i)
                if temp_name not in block_names_in_doc:
                    free_name = temp_name
                    break
        block_name = free_name
    
    if not block_name: return

    # 4. Insertion préalable pour comparaison visuelle en cas de conflit de nom
    # TODO : Cette opération doit être répété de manière reccursive afin de reconstruire tous les niveau hiérarchiques des objets sélectionnés
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
        # Préparation de la géométrie (Inverse transformation pour revenir au 0,0,0 local)
        inv_xform = rs.XformInverse(xform)
        
        new_geometries = []
        for o in initial_objs:
            # Sécurité : on ne met pas l'objet "Pose" à l'intérieur de sa propre définition
            if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose":
                continue
                
            copy = rs.CopyObject(o)
            rs.TransformObject(copy, inv_xform)
            new_geometries.append(copy)

        # 5. Mise à jour ou création de la définition de bloc
        # rs.AddBlock redéfinit le bloc s'il existe déjà
        rs.AddBlock(new_geometries, [0,0,0], block_name, delete_input=True)
        
        # Si on n'avait pas d'instance de prévisualisation, on en crée une à l'emplacement final
        if not temp_instance:
            temp_instance = rs.InsertBlock(block_name, [0,0,0])
            rs.TransformObject(temp_instance, xform)
        
        # 6. Nettoyage
        rs.DeleteObjects(initial_objs)
        rs.DeleteObjects(new_geometries)
        rs.UnselectAllObjects()
        rs.SelectObject(temp_instance)
        
        print("Bloc '{}' généré avec succès au point d'origine.".format(block_name))
    else:
        if temp_instance: rs.DeleteObject(temp_instance)
        print("Opération annulée.")

if __name__ == "__main__":
    rebuild_reciproque()

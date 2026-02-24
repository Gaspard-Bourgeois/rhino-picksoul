# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import uuid


def _replace_block_definition_from_copies(block_name, copies):
    """Remplace la définition `block_name` en utilisant les géométries des objets `copies`.
    Utilise RhinoCommon InstanceDefinitions.ModifyGeometry pour garder les instances
    en place (évite de transformer/supprimer les instances existantes).
    Retourne True si succès, False sinon.
    """
    # Récupérer la définition existante
    parent_def = sc.doc.InstanceDefinitions.Find(block_name, False)
    if parent_def is None:
        return False

    idefIndex = parent_def.Index

    newGeometry = []
    newAttributes = []

    for c in copies:
        objref = rs.coercerhinoobject(c)
        if not objref:
            continue
        geom = objref.Geometry.DuplicateShallow()
        attr = objref.Attributes.Duplicate()
        newGeometry.append(geom)
        newAttributes.append(attr)

    if not newGeometry:
        return False

    try:
        InstanceDefinitionTable = sc.doc.InstanceDefinitions
        success = InstanceDefinitionTable.ModifyGeometry(idefIndex, newGeometry, newAttributes)
        return success
    except Exception as e:
        print("Erreur _replace_block_definition_from_copies: {}".format(e))
        return False


def get_bbox_center(obj_id):
    """Calcule le centre d'une BoundingBox."""
    bbox = rs.BoundingBox(obj_id)
    if not bbox:
        return [0, 0, 0]
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
    if not initial_objs:
        return

    origin_obj = None
    block_name = None
    xform = None
    block_names_in_doc = rs.BlockNames()
    nesting_level = 0

    # 2. Recherche de l'objet "Pose" ou origine via la clé UserText
    for obj in initial_objs:
        val = rs.GetUserText(obj, "OriginalBlockName")
        if val:
            origin_obj = obj
            block_name = val
            nesting_str = rs.GetUserText(obj, "NestingLevel")
            nesting_level = int(nesting_str) if nesting_str else 0
            if rs.IsBlockInstance(obj):
                xform = rs.BlockInstanceXform(obj)
            break

    # 3. Gestion de l'absence d'origine identifiée
    if not origin_obj:
        ref_id = rs.GetObject("Origine non trouvée. Sélectionnez une référence (ou Entrée pour Monde)")
        if ref_id:
            if rs.IsBlockInstance(ref_id):
                block_name = rs.BlockInstanceName(ref_id)
                xform = rs.BlockInstanceXform(ref_id)
                nesting_str = rs.GetUserText(ref_id, "NestingLevel")
                nesting_level = int(nesting_str) if nesting_str else 0
            else:
                block_name = "NouveauBloc"
                center = get_bbox_center(ref_id)
                xform = rs.XformTranslation(center)
                nesting_level = 0
        else:
            block_name = "NouveauBloc"
            xform = rs.XformIdentity()
            nesting_level = 0

        # Nettoyage du nom
        if block_name.lower().endswith("_base"):
            block_name = block_name[:-5]
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

    if not block_name:
        return

    if not xform:
        xform = rs.XformIdentity()

    # Calculer le centre des objets pour le point de base
    preview_base_point = [0, 0, 0]
    bbox = rs.BoundingBox(initial_objs)
    if bbox:
        pt_min = bbox[0]
        pt_max = bbox[6]
        preview_base_point = [
            (pt_min[0] + pt_max[0]) / 2.0,
            (pt_min[1] + pt_max[1]) / 2.0,
            (pt_min[2] + pt_max[2]) / 2.0
        ]

    # 4. Préparation de la prévisualisation
    confirm = "Oui"
    preview_objects = []
    existed = rs.IsBlock(block_name)

    if confirm == "Oui":
        # Copier les objets SANS transformation pour prévisualisation
        copies = []
        for o in initial_objs:
            if rs.IsBlockInstance(o):
                if rs.BlockInstanceName(o) == block_name:
                    print("Info: Instance '{}' exclue pour éviter une récursion.".format(block_name))
                    continue
                if rs.BlockInstanceName(o) == "Pose":
                    continue

            c = rs.CopyObject(o)
            if not c:
                continue
            copies.append(c)

        # 5. Prévisualisation
        if len(copies) > 0:
            preview_objects = list(copies)

            # Comparaison avec l'ancienne définition
            temp_existing = None
            if existed:
                temp_existing = rs.InsertBlock(block_name, preview_base_point)
                if temp_existing:
                    try:
                        rs.SelectObject(temp_existing)
                    except:
                        pass

            if existed:
                msg = "Le bloc '{}' existe déjà. Mettre à jour sa définition ?".format(block_name)
            else:
                msg = "Créer la définition de bloc '{}' ?".format(block_name)
            confirm = rs.GetString(msg, "Oui", ["Oui", "Non"])

            if confirm == "Oui":
                success = False

                # Supprimer les objets temporaires de prévisualisation
                for obj in preview_objects:
                    if rs.IsObject(obj):
                        rs.DeleteObject(obj)
                preview_objects = []

                # Supprimer l'instance existante
                if temp_existing and rs.IsObject(temp_existing):
                    rs.DeleteObject(temp_existing)
                    temp_existing = None

                # Préparer les copies pour la définition du bloc
                block_copies = []
                for o in initial_objs:
                    if rs.IsBlockInstance(o):
                        if rs.BlockInstanceName(o) == block_name:
                            continue
                        if rs.BlockInstanceName(o) == "Pose":
                            continue

                    c = rs.CopyObject(o)
                    if not c:
                        continue

                    # Obtenir la position et calculer la translation vers l'origine
                    current_pt = rs.PointCoordinates(c)
                    if current_pt:
                        translation = [
                            current_pt[0] - preview_base_point[0],
                            current_pt[1] - preview_base_point[1],
                            current_pt[2] - preview_base_point[2]
                        ]
                        inv_xform = rs.XformTranslation(translation)
                        rs.TransformObject(c, inv_xform)

                    block_copies.append(c)

                # Remplacer la définition existante ou créer une nouvelle
                if existed:
                    success = _replace_block_definition_from_copies(block_name, block_copies)

                if not success:
                    # Supprimer les copies si elles existent encore
                    for c in block_copies:
                        if rs.IsObject(c):
                            rs.DeleteObject(c)

                    # Recréer les copies pour AddBlock
                    block_copies = []
                    for o in initial_objs:
                        if rs.IsBlockInstance(o):
                            if rs.BlockInstanceName(o) == block_name:
                                continue
                            if rs.BlockInstanceName(o) == "Pose":
                                continue

                        c = rs.CopyObject(o)
                        if not c:
                            continue

                        current_pt = rs.PointCoordinates(c)
                        if current_pt:
                            translation = [
                                current_pt[0] - preview_base_point[0],
                                current_pt[1] - preview_base_point[1],
                                current_pt[2] - preview_base_point[2]
                            ]
                            inv_xform = rs.XformTranslation(translation)
                            rs.TransformObject(c, inv_xform)

                        block_copies.append(c)

                    block_def = rs.AddBlock(block_copies, [0, 0, 0], block_name, delete_input=False)
                    if not block_def:
                        print("Erreur : impossible de créer la définition de bloc.")
                        return

                # Rafraîchir le document
                sc.doc.Views.Redraw()
                rs.Redraw()

                # Insérer la nouvelle instance
                new_instance = rs.InsertBlock(block_name, preview_base_point)
                if new_instance:
                    new_nesting_level = nesting_level + 1
                    rs.SetUserText(new_instance, "NestingLevel", str(new_nesting_level))
                    reciproque_id = str(uuid.uuid4())
                    rs.SetUserText(new_instance, "ReciproqueID", reciproque_id)
                    rs.SetUserText(new_instance, "OriginalBlockName", block_name)

                # Nettoyer les objets originaux
                for obj in initial_objs:
                    if rs.IsObject(obj):
                        rs.DeleteObject(obj)

                sc.doc.Views.Redraw()
                rs.Redraw()

                rs.UnselectAllObjects()
                if new_instance and rs.IsObject(new_instance):
                    rs.SelectObject(new_instance)

                print("Bloc '{}' généré avec succès.".format(block_name))
            else:
                # Annulation
                for obj in preview_objects:
                    if rs.IsObject(obj):
                        rs.DeleteObject(obj)
                if temp_existing and rs.IsObject(temp_existing):
                    rs.DeleteObject(temp_existing)
                print("Opération annulée.")
        else:
            print("Erreur : Aucune géométrie valide à ajouter au bloc.")
            for obj in preview_objects:
                if rs.IsObject(obj):
                    rs.DeleteObject(obj)
    else:
        for obj in preview_objects:
            if rs.IsObject(obj):
                rs.DeleteObject(obj)
        print("Opération annulée.")


if __name__ == "__main__":
    rebuild_reciproque()

# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def get_bbox_center(obj_ids):
    bbox = rs.BoundingBox(obj_ids)
    if not bbox: return [0,0,0]
    return [(bbox[0][i] + bbox[6][i]) / 2.0 for i in range(3)]

def get_free_indexed_name():
    i = 1
    while True:
        name = "new_bloc_{:02d}".format(i)
        if not rs.IsBlock(name): return name
        i += 1

def ensure_pose_block():
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        p1 = [0,0,0]
        l1 = rs.AddLine(p1, [1,0,0]); rs.ObjectColor(l1, [255,0,0])
        l2 = rs.AddLine(p1, [0,1,0]); rs.ObjectColor(l2, [0,255,0])
        l3 = rs.AddLine(p1, [0,0,1]); rs.ObjectColor(l3, [0,0,255])
        rs.AddBlock([l1, l2, l3], p1, "Pose", True)
        rs.EnableRedraw(True)
    return "Pose"

def rebuild_reciproque():
    objs = rs.GetObjects("Sélectionnez les objets (simples ou hiérarchisés)", preselect=True)
    if not objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    
    # --- ETAPE 1 : CONVERSION DES OBJETS SIMPLES EN BLOCS TEMPORAIRES ---
    final_list = []
    simple_objs = []
    
    for o in objs:
        keys = rs.GetUserText(o)
        is_hierarchized = any(k.startswith("BlockNameLevel_") for k in keys) if keys else False
        if is_hierarchized:
            final_list.append(o)
        elif not (rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose"):
            simple_objs.append(o)
            
    if simple_objs:
        temp_name = get_free_indexed_name()
        center = get_bbox_center(simple_objs)
        
        # Création du bloc temporaire
        temp_geos = [rs.CopyObject(o) for o in simple_objs]
        # On déplace les copies à l'origine pour la définition du bloc
        xform_to_zero = rs.XformTranslation(rs.PointScale(center, -1))
        rs.TransformObjects(temp_geos, xform_to_zero)
        rs.AddBlock(temp_geos, [0,0,0], temp_name, delete_input=True)
        
        # Insertion de l'instance et de sa Pose
        new_inst = rs.InsertBlock(temp_name, center)
        new_pose = rs.InsertBlock("Pose", center)
        
        # Marquage UserText (Niveau 0 par défaut pour les nouveaux blocs)
        rs.SetUserText(new_inst, "BlockNameLevel_0", temp_name)
        rs.SetUserText(new_pose, "BlockNameLevel_0", temp_name)
        
        final_list.extend([new_inst, new_pose])
        rs.DeleteObjects(simple_objs)

    # --- ETAPE 2 : BOUCLE DE RECONSTRUCTION HABITUELLE ---
    def get_map(ids):
        mapping = {}
        for o in ids:
            if not rs.IsObject(o): continue
            keys = rs.GetUserText(o)
            if not keys: continue
            for k in keys:
                if k.startswith("BlockNameLevel_"):
                    sig = rs.GetUserText(o, k)
                    lvl = int(k.split("_")[-1])
                    if sig not in mapping: mapping[sig] = {"level": lvl, "objects": [], "pose": None}
                    if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose":
                        mapping[sig]["pose"] = o
                    else:
                        mapping[sig]["objects"].append(o)
        return mapping

    h_map = get_map(final_list)
    levels = sorted(list(set(d["level"] for d in h_map.values())), reverse=True)

    for current_lvl in levels:
        current_map = get_map(final_list)
        for sig, data in current_map.items():
            if data["level"] != current_lvl: continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            target_name = sig.split("#")[0] if "#" in sig else sig
            is_temp = "new_bloc_" in sig
            
            # --- INTERFACE DE RENOMMAGE ET ORIGINE ---
            rs.UnselectAllObjects()
            rs.SelectObjects(geometries)
            rs.SelectObject(pose_obj)
            rs.EnableRedraw(True)
            
            # Si c'est un nouveau bloc, on force le choix du nom et de l'origine
            if is_temp:
                target_name = rs.StringBox("Nom final pour ce bloc :", target_name, "Paramétrage Nouveau Bloc")
                if not target_name: return
                
                if rs.GetString("Changer l'origine du bloc ?", "Non", ["Oui", "Non"]) == "Oui":
                    new_origin_pt = rs.GetPoint("Désignez la nouvelle origine pour '{}'".format(target_name))
                    if new_origin_pt:
                        # On déplace la Pose à la nouvelle position
                        rs.MoveObject(pose_obj, new_origin_pt - rs.BlockInstanceInsertPoint(pose_obj))
            
            # Menu habituel pour les blocs déjà nommés
            else:
                action = rs.GetString("Bloc '{}' :".format(target_name), "Ecraser", ["Ecraser", "Renommer", "Conserver", "Annuler"])
                if action == "Annuler": return
                if action == "Renommer":
                    target_name = rs.StringBox("Nouveau nom :", target_name)
                elif action == "Conserver":
                    # On passe au suivant sans reconstruire
                    continue

            rs.EnableRedraw(False)

            # --- RECONSTRUCTION FINALE ---
            xform = rs.BlockInstanceXform(pose_obj)
            inv_xform = rs.XformInverse(xform)
            
            temp_geos = []
            for g in geometries:
                cp = rs.CopyObject(g)
                rs.TransformObject(cp, inv_xform)
                # Nettoyage des UserText pour les objets à l'intérieur
                for k in (rs.GetUserText(cp) or []):
                    if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, "")
                temp_geos.append(cp)

            # Si on écrase un bloc existant
            if rs.IsBlock(target_name):
                idef = sc.doc.InstanceDefinitions.Find(target_name)
                geos = [sc.doc.Objects.Find(g).Geometry for g in temp_geos]
                attrs = [sc.doc.Objects.Find(g).Attributes for g in temp_geos]
                sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geos, attrs)
                rs.DeleteObjects(temp_geos)
            else:
                rs.AddBlock(temp_geos, [0,0,0], target_name, delete_input=True)

            # Insertion de l'instance propre
            final_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(final_inst, xform)
            
            # Transmission UserText aux parents
            for k in (rs.GetUserText(geometries[0]) or []):
                if k.startswith("BlockNameLevel_"):
                    if int(k.split("_")[-1]) < current_lvl:
                        rs.SetUserText(final_inst, k, rs.GetUserText(geometries[0], k))

            # Nettoyage
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            final_list = [o for o in final_list if o not in geometries and o != pose_obj]
            final_list.append(final_inst)

    rs.EnableRedraw(True)
    print("Reconstruction terminée.")

if __name__ == "__main__":
    rebuild_reciproque()

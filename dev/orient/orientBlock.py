# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math
import re

def get_block_axes(block_id):
    """Extrait les vecteurs X, Y, Z d'une instance de bloc."""
    xform = rs.BlockInstanceXform(block_id)
    if not xform: return None, None, None
    x = rg.Vector3d(xform.M00, xform.M10, xform.M20)
    y = rg.Vector3d(xform.M01, xform.M11, xform.M21)
    z = rg.Vector3d(xform.M02, xform.M12, xform.M22)
    return x, y, z

def get_pose_info(objs):
    """
    Cherche un objet 'pivot' parmi une liste d'objets via la clé UserText.
    Retourne (point_origine, vecteur_x, vecteur_y, vecteur_z)
    """
    for obj in objs:
        # On vérifie les deux clés possibles (la précédente et la nouvelle demandée)
        if rs.GetUserText(obj, "OriginalBlockName") or rs.GetUserText(obj, "block origin"):
            if rs.IsBlockInstance(obj):
                pt = rs.BlockInstanceInsertPoint(obj)
                ax, ay, az = get_block_axes(obj)
                return pt, ax, ay, az
            else:
                # Si c'est un objet standard avec la clé, on prend sa BBox
                bbox = rs.BoundingBox(obj)
                if bbox:
                    return (bbox[0]+bbox[6])/2, rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis
    return None

def transform_smart_sets():
    # 1. SÉLECTION
    initial_selection = rs.GetObjects("Sélectionnez les objets ou groupes à transformer", preselect=True)
    if not initial_selection: return

    # -----------------------------------------------------------
    # 2. LOGIQUE DE PARSING HISTORIQUE (Inchangée mais nettoyée)
    # -----------------------------------------------------------
    tx, ty, tz = 10.0, 0.0, 0.0
    rz_deg, ry_deg, rx_deg = 45.0, 0.0, 0.0
    coordinate_system = "World"
    
    struct = r"Repère: (\S+). Paramètres: Tx=(\S+) Ty=(\S+) Tz=(\S+) \| Rotations \(Deg\): Rz=(\S+) Ry=(\S+) Rx=(\S+)"
    history = rs.CommandHistory().split('\n')
    for line in reversed(history):
        match = re.search(struct, line)
        if match:
            coordinate_system = match.group(1)
            tx, ty, tz, rz_deg, ry_deg, rx_deg = map(float, match.group(2,3,4,8,7,6)) # Note: Ordre regex
            break

    # -----------------------------------------------------------
    # 3. BOUCLE D'INTERFACE (GetString)
    # -----------------------------------------------------------
    while True:
        msg = "Repère: {}. Paramètres: Tx={:.2f} Ty={:.2f} Tz={:.2f} | Rotations (Deg): Rz={:.2f} Ry={:.2f} Rx={:.2f}. Entrée pour appliquer.".format(
            coordinate_system, tx, ty, tz, rz_deg, ry_deg, rx_deg)
        
        res = rs.GetString(msg, "", ["Repere", "Tx", "Ty", "Tz", "Rz", "Ry", "Rx", "SetAll"])
        if res is None: return
        if res == "": break
        
        if res == "Repere":
            coordinate_system = rs.GetString("Système?", coordinate_system, ["World", "CPlane", "Block"]) or coordinate_system
        elif res == "Tx": tx = rs.GetReal("Tx", tx) or tx
        elif res == "Ty": ty = rs.GetReal("Ty", ty) or ty
        elif res == "Tz": tz = rs.GetReal("Tz", tz) or tz
        elif res == "Rz": rz_deg = rs.GetReal("Rz", rz_deg) or rz_deg
        elif res == "Ry": ry_deg = rs.GetReal("Ry", ry_deg) or ry_deg
        elif res == "Rx": rx_deg = rs.GetReal("Rx", rx_deg) or rx_deg
        elif res == "SetAll":
            val = rs.GetString("X,Y,Z,Rz,Ry,Rx", "{},{},{},{},{},{}".format(tx,ty,tz,rz_deg,ry_deg,rx_deg))
            if val:
                try: tx, ty, tz, rz_deg, ry_deg, rx_deg = [float(x) for x in val.split(',')]
                except: print("Format invalide.")

    # -----------------------------------------------------------
    # 4. APPLICATION DE LA TRANSFORMATION
    # -----------------------------------------------------------
    rz, ry, rx = math.radians(rz_deg), math.radians(ry_deg), math.radians(rx_deg)
    rs.EnableRedraw(False)

    # On définit le plan de base pour la translation (World ou CPlane)
    ref_plane = rs.ViewCPlane() if coordinate_system == "CPlane" else rg.Plane.WorldXY
    
    # Identifier les "Paquets" d'objets (Regrouper par groupe Rhino si présent)
    objects_to_process = []
    processed_ids = set()

    for obj_id in initial_selection:
        if obj_id in processed_ids: continue
        
        group_names = rs.ObjectGroups(obj_id)
        if group_names:
            group_members = rs.ObjectsByGroup(group_names[0])
            objects_to_process.append(group_members)
            for m in group_members: processed_ids.add(m)
        else:
            objects_to_process.append([obj_id])
            processed_ids.add(obj_id)

    count = 0
    for subset in objects_to_process:
        # Trouver le pivot dans ce sous-ensemble
        pose_data = get_pose_info(subset)
        
        if pose_data:
            pivot_pt, axis_x, axis_y, axis_z = pose_data
        else:
            # Fallback : Centre de la sélection
            bbox = rs.BoundingBox(subset)
            pivot_pt = (bbox[0] + bbox[6]) / 2 if bbox else rg.Point3d(0,0,0)
            axis_x, axis_y, axis_z = rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # Choix des axes pour la rotation/translation locale
        if coordinate_system == "Block":
            target_x, target_y, target_z = axis_x, axis_y, axis_z
        elif coordinate_system == "CPlane":
            cp = rs.ViewCPlane()
            target_x, target_y, target_z = cp.XAxis, cp.YAxis, cp.ZAxis
        else:
            target_x, target_y, target_z = rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # Construction de la matrice
        # 1. Rotation
        xf_rz = rg.Transform.Rotation(rz, target_z, pivot_pt)
        xf_ry = rg.Transform.Rotation(ry, target_y, pivot_pt)
        xf_rx = rg.Transform.Rotation(rx, target_x, pivot_pt)
        rotation_final = xf_rx * xf_ry * xf_rz
        
        # 2. Translation
        vec_t = (target_x * tx) + (target_y * ty) + (target_z * tz)
        translation_final = rg.Transform.Translation(vec_t)
        
        # Transformation combinée
        full_xf = translation_final * rotation_final
        
        if rs.TransformObjects(subset, full_xf, copy=False):
            count += 1

    rs.EnableRedraw(True)
    print("Succès : {} groupe(s)/objet(s) transformés via leur pivot.".format(count))

if __name__ == "__main__":
    transform_smart_sets()

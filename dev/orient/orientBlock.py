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
    """Cherche un pivot via UserText ou BoundingBox."""
    for obj in objs:
        if rs.GetUserText(obj, "OriginalBlockName") or rs.GetUserText(obj, "block origin"):
            if rs.IsBlockInstance(obj):
                pt = rs.BlockInstanceInsertPoint(obj)
                ax, ay, az = get_block_axes(obj)
                return pt, ax, ay, az
            else:
                bbox = rs.BoundingBox(obj)
                if bbox:
                    return (bbox[0]+bbox[6])/2, rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis
    return None

def transform_smart_sets():
    # 1. SÉLECTION
    initial_selection = rs.GetObjects("Sélectionnez les objets ou groupes à transformer", preselect=True)
    if not initial_selection: return

    # -----------------------------------------------------------
    # 2. LOGIQUE DE PARSING HISTORIQUE (Version Robuste)
    # -----------------------------------------------------------
    tx, ty, tz = 10.0, 0.0, 0.0
    rz_deg, ry_deg, rx_deg = 0.0, 0.0, 0.0
    coordinate_system = "World"
    
    # Regex : Capture uniquement les structures de nombres valides
    # On utilise [-+]?\d*\.?\d+ pour éviter de capturer des caractères non-numériques
    num_pattern = r"([-+]?\d*\.?\d+)"
    struct = r"Repère: (\w+)\. Paramètres: Tx={0} Ty={0} Tz={0} \| Rotations \(Deg\): Rz={0} Ry={0} Rx={0}".format(num_pattern)
    
    history = rs.CommandHistory().split('\n')
    for line in reversed(history):
        match = re.search(struct, line)
        if match:
            try:
                coordinate_system = match.group(1)
                # Conversion sécurisée des 6 groupes numériques (index 2 à 7)
                vals = [float(match.group(i)) for i in range(2, 8)]
                tx, ty, tz, rz_deg, ry_deg, rx_deg = vals
                break 
            except (ValueError, IndexError):
                continue

    # -----------------------------------------------------------
    # 3. BOUCLE D'INTERFACE
    # -----------------------------------------------------------
    while True:
        msg = "Repère: {}. Paramètres: Tx={:.2f} Ty={:.2f} Tz={:.2f} | Rz={:.2f} Ry={:.2f} Rx={:.2f}".format(
            coordinate_system, tx, ty, tz, rz_deg, ry_deg, rx_deg)
        
        res = rs.GetString(msg, "Appliquer", ["Repere", "Tx", "Ty", "Tz", "Rz", "Ry", "Rx", "SetAll"])
        if res is None: return
        if res == "" or res == "Appliquer": break
        
        if res == "Repere":
            choice = rs.GetString("Système?", coordinate_system, ["World", "CPlane", "Block"])
            if choice: coordinate_system = choice
        elif res == "Tx": tx = rs.GetReal("Tx", tx) if rs.GetReal("Tx", tx) is not None else tx
        elif res == "Ty": ty = rs.GetReal("Ty", ty) if rs.GetReal("Ty", ty) is not None else ty
        elif res == "Tz": tz = rs.GetReal("Tz", tz) if rs.GetReal("Tz", tz) is not None else tz
        elif res == "Rz": rz_deg = rs.GetReal("Rz", rz_deg) if rs.GetReal("Rz", rz_deg) is not None else rz_deg
        elif res == "Ry": ry_deg = rs.GetReal("Ry", ry_deg) if rs.GetReal("Ry", ry_deg) is not None else ry_deg
        elif res == "Rx": rx_deg = rs.GetReal("Rx", rx_deg) if rs.GetReal("Rx", rx_deg) is not None else rx_deg
        elif res == "SetAll":
            val = rs.GetString("Format: Tx,Ty,Tz,Rz,Ry,Rx", "{},{},{},{},{},{}".format(tx,ty,tz,rz_deg,ry_deg,rx_deg))
            if val:
                try:
                    # Remplace les virgules par des points au cas où l'utilisateur tape à la française
                    clean_val = val.replace(',', '.')
                    # On split par n'importe quel séparateur non numérique (espace ou point-virgule résiduel)
                    parts = re.findall(r"[-+]?\d*\.?\d+", clean_val)
                    if len(parts) == 6:
                        tx, ty, tz, rz_deg, ry_deg, rx_deg = [float(p) for p in parts]
                except: print("Format invalide. Utilisez le point pour les décimales.")

    # -----------------------------------------------------------
    # 4. APPLICATION DE LA TRANSFORMATION
    # -----------------------------------------------------------
    rz, ry, rx = math.radians(rz_deg), math.radians(ry_deg), math.radians(rx_deg)
    rs.EnableRedraw(False)

    objects_to_process = []
    processed_ids = set()

    for obj_id in initial_selection:
        if obj_id in processed_ids: continue
        
        group_names = rs.ObjectGroups(obj_id)
        if group_names and rs.IsGroup(group_names[0]):
            group_members = rs.ObjectsByGroup(group_names[0])
            objects_to_process.append(group_members)
            for m in group_members: processed_ids.add(m)
        else:
            objects_to_process.append([obj_id])
            processed_ids.add(obj_id)

    count = 0
    for subset in objects_to_process:
        pose_data = get_pose_info(subset)
        
        if pose_data:
            pivot_pt, axis_x, axis_y, axis_z = pose_data
        else:
            bbox = rs.BoundingBox(subset)
            pivot_pt = (bbox[0] + bbox[6]) / 2 if bbox else rg.Point3d(0,0,0)
            axis_x, axis_y, axis_z = rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # Choix des axes
        if coordinate_system == "Block":
            tx_axis, ty_axis, tz_axis = axis_x, axis_y, axis_z
        elif coordinate_system == "CPlane":
            cp = rs.ViewCPlane()
            tx_axis, ty_axis, tz_axis = cp.XAxis, cp.YAxis, cp.ZAxis
        else:
            tx_axis, ty_axis, tz_axis = rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # Construction des matrices (Rotation puis Translation)
        xf_rz = rg.Transform.Rotation(rz, tz_axis, pivot_pt)
        xf_ry = rg.Transform.Rotation(ry, ty_axis, pivot_pt)
        xf_rx = rg.Transform.Rotation(rx, tx_axis, pivot_pt)
        
        vec_t = (tx_axis * tx) + (ty_axis * ty) + (tz_axis * tz)
        xf_trans = rg.Transform.Translation(vec_t)
        
        full_xf = xf_trans * xf_rx * xf_ry * xf_rz
        
        if rs.TransformObjects(subset, full_xf, copy=False):
            count += 1

    rs.EnableRedraw(True)
    # L'écriture exacte dans l'historique pour le prochain appel
    print("Repère: {}. Paramètres: Tx={:.2f} Ty={:.2f} Tz={:.2f} | Rotations (Deg): Rz={:.2f} Ry={:.2f} Rx={:.2f}".format(
        coordinate_system, tx, ty, tz, rz_deg, ry_deg, rx_deg))
    print("Succès : {} ensemble(s) transformé(s).".format(count))

if __name__ == "__main__":
    transform_smart_sets()

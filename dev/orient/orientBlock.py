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
    Cherche un pivot dans la liste d'objets. 
    Priorité : UserText > Objet Texte (Insertion Point) > Bloc > Bounding Box.
    """
    for obj in objs:
        # 1. Vérification UserText (Pivot personnalisé)
        if rs.GetUserText(obj, "OriginalBlockName") or rs.GetUserText(obj, "block origin"):
            if rs.IsBlockInstance(obj):
                pt = rs.BlockInstanceInsertPoint(obj)
                ax, ay, az = get_block_axes(obj)
                return pt, ax, ay, az
            else:
                bbox = rs.BoundingBox(obj)
                if bbox:
                    return (bbox[0]+bbox[6])/2, rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # 2. Cas spécifique des Objets TEXTE (Nouveau)
        if rs.IsText(obj):
            pt = rs.TextObjectPoint(obj)
            plane = rs.TextObjectPlane(obj)
            return pt, plane.XAxis, plane.YAxis, plane.ZAxis

        # 3. Cas des Blocs standards
        if rs.IsBlockInstance(obj):
            pt = rs.BlockInstanceInsertPoint(obj)
            ax, ay, az = get_block_axes(obj)
            return pt, ax, ay, az
            
    return None

def transform_smart_sets():
    # 1. SÉLECTION
    initial_selection = rs.GetObjects("Sélectionnez les objets (Textes, Blocs, Groupes) à transformer", preselect=True)
    if not initial_selection: return

    # -----------------------------------------------------------
    # 2. LOGIQUE DE PARSING HISTORIQUE
    # -----------------------------------------------------------
    tx, ty, tz = 0.0, 0.0, 0.0
    rz_deg, ry_deg, rx_deg = 0.0, 0.0, 0.0
    coordinate_system = "World"
    
    num_p = r"([-+]?\d*\.?\d+)"
    struct = r"Repère: (\w+)\. Paramètres: Tx={0} Ty={0} Tz={0} \| Rotations \(Deg\): Rz={0} Ry={0} Rx={0}".format(num_p)
    
    history = rs.CommandHistory().split('\n')
    for line in reversed(history):
        match = re.search(struct, line)
        if match:
            try:
                coordinate_system = match.group(1)
                vals = [float(match.group(i)) for i in range(2, 8)]
                tx, ty, tz, rz_deg, ry_deg, rx_deg = vals
                break 
            except: continue

    # -----------------------------------------------------------
    # 3. INTERFACE UTILISATEUR
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
            val = rs.GetString("Valeurs: Tx,Ty,Tz,Rz,Ry,Rx", "{},{},{},{},{},{}".format(tx,ty,tz,rz_deg,ry_deg,rx_deg))
            if val:
                try:
                    parts = re.findall(r"[-+]?\d*\.?\d+", val.replace(',', '.'))
                    if len(parts) == 6:
                        tx, ty, tz, rz_deg, ry_deg, rx_deg = [float(p) for p in parts]
                except: print("Format invalide.")

    # -----------------------------------------------------------
    # 4. APPLICATION
    # -----------------------------------------------------------
    rz, ry, rx = math.radians(rz_deg), math.radians(ry_deg), math.radians(rx_deg)
    rs.EnableRedraw(False)

    objects_to_process = []
    processed_ids = set()

    # Organisation des objets par groupes ou unités
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

        # Axes de référence
        if coordinate_system == "Block":
            tx_ax, ty_ax, tz_ax = axis_x, axis_y, axis_z
        elif coordinate_system == "CPlane":
            cp = rs.ViewCPlane()
            tx_ax, ty_ax, tz_ax = cp.XAxis, cp.YAxis, cp.ZAxis
        else:
            tx_ax, ty_ax, tz_ax = rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis

        # Calcul matriciel
        xf_rz = rg.Transform.Rotation(rz, tz_ax, pivot_pt)
        xf_ry = rg.Transform.Rotation(ry, ty_ax, pivot_pt)
        xf_rx = rg.Transform.Rotation(rx, tx_ax, pivot_pt)
        vec_t = (tx_ax * tx) + (ty_ax * ty) + (tz_ax * tz)
        xf_trans = rg.Transform.Translation(vec_t)
        
        full_xf = xf_trans * xf_rx * xf_ry * xf_rz
        
        if rs.TransformObjects(subset, full_xf, copy=False):
            count += 1

    rs.EnableRedraw(True)
    # Print pour l'historique
    print("Repère: {}. Paramètres: Tx={:.2f} Ty={:.2f} Tz={:.2f} | Rotations (Deg): Rz={:.2f} Ry={:.2f} Rx={:.2f}".format(
        coordinate_system, tx, ty, tz, rz_deg, ry_deg, rx_deg))
    print("Succès : {} ensemble(s) transformé(s).".format(count))

if __name__ == "__main__":
    transform_smart_sets()

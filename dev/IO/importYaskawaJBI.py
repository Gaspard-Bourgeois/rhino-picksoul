"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math
import re


def get_euler_from_plane(plane):
    """Calcule les angles Euler (Rx, Ry, Rz) pour affichage debug."""
    xaxis = plane.XAxis
    ry = math.asin(-xaxis.Z)
    if abs(math.cos(ry)) > 0.000001:
        rx = math.atan2(plane.YAxis.Z, plane.ZAxis.Z)
        rz = math.atan2(plane.XAxis.Y, xaxis.X)
    else:
        rx = 0
        rz = math.atan2(-plane.YAxis.X, plane.YAxis.Y)
    return math.degrees(rx), math.degrees(ry), math.degrees(rz)


def create_pose_block():
    if rs.IsBlock("Pose"): return
    prev_layer = rs.CurrentLayer()
    def_lyr = rs.AddLayer("_pose_def", (128,128,128))
    rs.CurrentLayer(def_lyr)
    p0 = [0,0,0]
    x = rs.AddLine(p0, [10,0,0]); rs.ObjectColor(x, (255,0,0))
    y = rs.AddLine(p0, [0,10,0]); rs.ObjectColor(y, (0,255,0))
    z = rs.AddLine(p0, [0,0,10]); rs.ObjectColor(z, (0,0,255))
    rs.AddBlock([x,y,z], p0, "Pose", True)
    rs.CurrentLayer(prev_layer)


def import_jbi_v4():
    filepath = rs.OpenFileName("Fichier JBI", "JBI Files (*.jbi)|*.jbi||")
    if not filepath: return
    with open(filepath, 'r') as f: lines = f.readlines()


    # 1. Parsing Header
    job_name = "NONAME"; folder_name = ""; user_id = None; pos_dict = {}
    for l in lines:
        l = l.strip()
        if l.startswith("//NAME"): job_name = l.split(" ")[1]
        elif l.startswith("///FOLDERNAME"): folder_name = l.split(" ")[1]
        elif l.startswith("///USER"): user_id = l.split(" ")[1]
        elif l.startswith("C") and "=" in l:
            parts = l.split("="); c_id = parts[0]
            pos_dict[c_id] = [float(v) for v in parts[1].split(",")]


    # 2. Calques
    base_path = "{}\\{}".format(folder_name, job_name) if folder_name else job_name
    if rs.IsLayer(base_path):
        rs.MessageBox("Le calque '{}' existe deja.".format(base_path), 16); return
    
    if folder_name:
        parent_lyr = rs.AddLayer(folder_name)
    main_lyr = rs.AddLayer(job_name, parent=folder_name if folder_name else None)
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    se_lyr = rs.AddLayer("start_end", parent=main_lyr)
    rs.CurrentLayer(main_lyr)


    # 3. Repere Origine
    origin_plane = rs.WorldXYPlane()
    if user_id:
        for np in rs.NamedCPlanes():
            if np.Name == user_id: origin_plane = np.Plane; break
    
    rx_o, ry_o, rz_o = get_euler_from_plane(origin_plane)
    print("DEBUG - ORIGIN USER {}: Pos{} Rot({:.2f},{:.2f},{:.2f})".format(user_id, origin_plane.Origin, rx_o, ry_o, rz_o))


    create_pose_block()
    rs.EnableRedraw(False)


    # 4. Traitement des points
    inst_data = []
    ctx = {'arcon': False}
    in_nop = False
    instance_idx = 0


    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue
        if "ARCON" in raw: ctx['arcon'] = True
        elif "ARCOF" in raw: ctx['arcon'] = False


        m = re.search(r"(MOVL|MOVJ|SMOVL)\s+(C\d+)", raw)
        if m and m.group(2) in pos_dict:
            c_id = m.group(2)
            p = pos_dict[c_id]
            
            # Calcul Position et Orientation
            target_pt = origin_plane.PointAt(p[0], p[1], p[2])
            pose_plane = rg.Plane(origin_plane)
            pose_plane.Origin = target_pt
            # Rotations Yaskawa intrinsèques
            pose_plane.Rotate(math.radians(p[5]), origin_plane.ZAxis, target_pt) # Rz
            pose_plane.Rotate(math.radians(p[4]), pose_plane.YAxis, target_pt) # Ry
            pose_plane.Rotate(math.radians(p[3]), pose_plane.XAxis, target_pt) # Rx


            # INSERTION ET TRANSFORMATION (Approche Matrix)
            inst_id = rs.InsertBlock("Pose", [0,0,0]) # Insérer à zéro pour transformer proprement
            xform = rg.Transform.PlaneToPlane(rg.Plane.WorldXY, pose_plane)
            rs.TransformObject(inst_id, xform)
            
            rs.ObjectName(inst_id, str(instance_idx))
            rs.ObjectLayer(inst_id, main_lyr)
            
            inst_data.append({'idx': str(instance_idx), 'pos': target_pt, 'arcon': ctx['arcon'], 'c_id': c_id})
            instance_idx += 1


    # 5. Courbes et Trajectoires
    rs.CurrentLayer(traj_lyr)
    if len(inst_data) > 1:
        seg = [inst_data[0]]
        last_st = inst_data[0]['arcon']
        
        def build_pl(data, st):
            pl = rs.AddPolyline([d['pos'] for d in data])
            pref = "ARCON" if st else "ARCOF"
            rs.ObjectName(pl, "{} {}-{}".format(pref, data[0]['c_id'], data[-1]['c_id']))
            rs.ObjectColor(pl, (255,0,0) if st else (150,150,150))
            for i, d in enumerate(data): rs.SetUserText(pl, "Pt_{}".format(i), d['idx'])


        for i in range(1, len(inst_data)):
            if inst_data[i]['arcon'] != last_st:
                build_pl(seg, last_st)
                seg = [inst_data[i-1], inst_data[i]]; last_st = inst_data[i]['arcon']
            else: seg.append(inst_data[i])
        build_pl(seg, last_st)


    # 6. Start & End
    if inst_data:
        rs.CurrentLayer(se_lyr)
        # Carré au début (Point 0)
        p_start = inst_data[0]['pos']
        rs.AddRectangle(rg.Plane(p_start, rg.Vector3d.ZAxis), 5, 5)
        # Sphère à la fin
        p_end = inst_data[-1]['pos']
        rs.AddSphere(p_end, 3)


    rs.AddText("".join(lines), [0,0,0], 10)
    rs.EnableRedraw(True)
    rs.Redraw()


if __name__ == "__main__":
    import_jbi_v4()

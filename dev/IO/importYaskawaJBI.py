import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math
import re

def get_euler_from_plane(plane):
    """Calcule les angles Euler (Rx, Ry, Rz) pour affichage debug par rapport au World."""
    xaxis = plane.XAxis
    ry = math.asin(-xaxis.Z)
    if abs(math.cos(ry)) > 0.000001:
        rx = math.atan2(plane.YAxis.Z, plane.ZAxis.Z)
        rz = math.atan2(plane.XAxis.Y, plane.XAxis.X)
    else:
        rx = 0
        rz = math.atan2(-plane.YAxis.X, plane.YAxis.Y)
    return math.degrees(rx), math.degrees(ry), math.degrees(rz)

def create_pose_block():
    """Crée le bloc 'Pose' avec axes XYZ colorés sur le calque dédié."""
    if rs.IsBlock("Pose"): return
    
    current_lyr = rs.CurrentLayer()
    if not rs.IsLayer("_pose_def"):
        rs.AddLayer("_pose_def", (128,128,128))
    
    rs.CurrentLayer("_pose_def")
    p0 = [0,0,0]
    # Axes : X=Rouge, Y=Vert, Z=Bleu
    line_x = rs.AddLine(p0, [10,0,0])
    rs.ObjectColor(line_x, (255,0,0))
    line_y = rs.AddLine(p0, [0,10,0])
    rs.ObjectColor(line_y, (0,255,0))
    line_z = rs.AddLine(p0, [0,0,10])
    rs.ObjectColor(line_z, (0,0,255))
    
    rs.AddBlock([line_x, line_y, line_z], p0, "Pose", delete_input=True)
    rs.CurrentLayer(current_lyr)

def import_jbi_final():
    # 1. Sélection et lecture du fichier
    filepath = rs.OpenFileName("Ouvrir fichier JBI", "JBI Files (*.jbi)|*.jbi||")
    if not filepath: return
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # --- 2. Parsing Initial (Positions et Header) ---
    job_name = "NONAME"
    folder_name = ""
    user_frame_id = None
    pos_dict = {}

    for line in lines:
        l = line.strip()
        if l.startswith("//NAME"): job_name = l.split(" ")[1]
        elif l.startswith("///FOLDERNAME"): folder_name = l.split(" ")[1]
        elif l.startswith("///USER"): user_frame_id = l.split(" ")[1]
        elif l.startswith("C") and "=" in l:
            parts = l.split("=")
            c_id = parts[0]
            coords = [float(v) for v in parts[1].split(",")]
            pos_dict[c_id] = coords

    # --- 3. Gestion des Calques (Correction de l'erreur Parent) ---
    # On vérifie d'abord si le calque final existerait déjà pour arrêter le script
    full_path = "{}::{}".format(folder_name, job_name) if folder_name else job_name
    if rs.IsLayer(full_path):
        rs.MessageBox("Erreur : Le programme '{}' existe déjà. Importation annulée.".format(full_path), 16)
        return

    # Création sécurisée de la hiérarchie
    if folder_name:
        if not rs.IsLayer(folder_name):
            rs.AddLayer(folder_name)
        main_lyr = rs.AddLayer(job_name, parent=folder_name)
    else:
        main_lyr = rs.AddLayer(job_name)
        
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    se_lyr = rs.AddLayer("start_end", parent=main_lyr)
    rs.CurrentLayer(main_lyr)

    # --- 4. Repère Origine (USER Frame) ---
    origin_plane = rs.WorldXYPlane()
    if user_frame_id:
        for np in rs.NamedCPlanes():
            if np.Name == user_frame_id:
                origin_plane = np.Plane
                break
    
    rx_o, ry_o, rz_o = get_euler_from_plane(origin_plane)
    print("--- REPERE ORIGINE UTILISE ---")
    print("Position World : X:{:.3f}, Y:{:.3f}, Z:{:.3f}".format(origin_plane.Origin.X, origin_plane.Origin.Y, origin_plane.Origin.Z))
    print("Rotation World : Rx:{:.3f}, Ry:{:.3f}, Rz:{:.3f}".format(rx_o, ry_o, rz_o))

    # --- 5. Préparation Géométrique ---
    create_pose_block()
    rs.EnableRedraw(False)

    inst_data = []
    ctx = {'arcon': False, 'macro': "", 'label': ""}
    in_nop = False
    instance_idx = 0

    # --- 6. Parsing des Instructions et Placement ---
    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue

        if raw.startswith("*"): ctx['label'] = raw
        elif "ARCON" in raw: ctx['arcon'] = True
        elif "ARCOF" in raw: ctx['arcon'] = False
        elif "MACRO1" in raw:
            m = re.search(r"ARGF(\d+)", raw)
            ctx['macro'] = m.group(1) if m else ""
        
        m_match = re.search(r"(MOVL|MOVJ|SMOVL)\s+(C\d+)", raw)
        if m_match:
            move_type, c_id = m_match.group(1), m_match.group(2)
            if c_id in pos_dict:
                p = pos_dict[c_id]
                target_pt = origin_plane.PointAt(p[0], p[1], p[2])
                pose_plane = rg.Plane(origin_plane)
                pose_plane.Origin = target_pt
                
                pose_plane.Rotate(math.radians(p[5]), origin_plane.ZAxis, target_pt)
                pose_plane.Rotate(math.radians(p[4]), pose_plane.YAxis, target_pt)
                pose_plane.Rotate(math.radians(p[3]), pose_plane.XAxis, target_pt)
                
                inst_id = rs.InsertBlock("Pose", [0,0,0])
                xform = rg.Transform.PlaneToPlane(rg.Plane.WorldXY, pose_plane)
                rs.TransformObject(inst_id, xform)
                
                rs.ObjectName(inst_id, str(instance_idx))
                
                # UserText Instance
                rs.SetUserText(inst_id, "uuid_origin", str(inst_id))
                rs.SetUserText(inst_id, "ID_C", c_id)
                rs.SetUserText(inst_id, "Type", move_type)
                
                inst_data.append({
                    'idx': str(instance_idx), 
                    'pos': target_pt, 
                    'arcon': ctx['arcon'], 
                    'uuid': str(inst_id),
                    'c_id': c_id
                })
                instance_idx += 1

    # --- 7. Polylignes (Layer trajs_arcon_arcof) ---
    rs.CurrentLayer(traj_lyr)
    if len(inst_data) > 1:
        segment = [inst_data[0]]
        last_state = inst_data[0]['arcon']

        def create_traj(data, state):
            if len(data) < 2: return
            pl_id = rs.AddPolyline([d['pos'] for d in data])
            prefix = "ARCON" if state else "ARCOF"
            rs.ObjectName(pl_id, "{} {}-{}".format(prefix, data[0]['idx'], data[-1]['idx']))
            rs.ObjectColor(pl_id, (255,0,0) if state else (150,150,150))
            
            # AJOUT DE L'UUID DE LA COURBE (Spécification demandée)
            rs.SetUserText(pl_id, "uuid_origin", str(pl_id))
            
            # Métadonnées par point
            for i, d in enumerate(data):
                rs.SetUserText(pl_id, "Pt_{}".format(i), d['idx'])
                rs.SetUserText(pl_id, "UUID_{}".format(i), d['uuid'])

        for i in range(1, len(inst_data)):
            if inst_data[i]['arcon'] != last_state:
                create_traj(segment, last_state)
                segment = [inst_data[i-1], inst_data[i]]
                last_state = inst_data[i]['arcon']
            else:
                segment.append(inst_data[i])
        create_traj(segment, last_state)

    # --- 8. Start & End (Layer start_end) ---
    if inst_data:
        rs.CurrentLayer(se_lyr)
        rs.AddRectangle(rg.Plane(inst_data[0]['pos'], rg.Vector3d.ZAxis), 5, 5)
        rs.AddSphere(inst_data[-1]['pos'], 3)

    # --- 9. Finalisation ---
    rs.CurrentLayer(main_lyr)
    rs.AddText("".join(lines), [0,0,0], height=10.0)
    rs.EnableRedraw(True)
    rs.Redraw()
    print("Importation terminée.")

if __name__ == "__main__":
    import_jbi_final()

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
        rz = math.atan2(plane.XAxis.Y, plane.XAxis.X)
    else:
        rx = 0
        rz = math.atan2(-plane.YAxis.X, plane.YAxis.Y)
    return math.degrees(rx), math.degrees(ry), math.degrees(rz)

def create_pose_block():
    """Crée le bloc 'Pose' avec axes XYZ colorés."""
    if rs.IsBlock("Pose"): return
    current_lyr = rs.CurrentLayer()
    if not rs.IsLayer("_pose_def"):
        rs.AddLayer("_pose_def", (128,128,128))
    rs.CurrentLayer("_pose_def")
    p0 = [0,0,0]
    lx = rs.AddLine(p0, [10,0,0]); rs.ObjectColor(lx, (255,0,0))
    ly = rs.AddLine(p0, [0,10,0]); rs.ObjectColor(ly, (0,255,0))
    lz = rs.AddLine(p0, [0,0,10]); rs.ObjectColor(lz, (0,0,255))
    rs.AddBlock([lx, ly, lz], p0, "Pose", delete_input=True)
    rs.CurrentLayer(current_lyr)

def import_jbi_final():
    filepath = rs.OpenFileName("Ouvrir fichier JBI", "JBI Files (*.jbi)|*.jbi||")
    if not filepath: return
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # --- 1. Parsing Initial ---
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
            pos_dict[parts[0]] = [float(v) for v in parts[1].split(",")]

    # --- 2. Gestion des Calques ---
    full_path = "{}::{}".format(folder_name, job_name) if folder_name else job_name
    if rs.IsLayer(full_path):
        rs.MessageBox("Erreur : Le programme '{}' existe déjà.".format(full_path), 16)
        return

    if folder_name:
        if not rs.IsLayer(folder_name): rs.AddLayer(folder_name)
        main_lyr = rs.AddLayer(job_name, parent=folder_name)
    else:
        main_lyr = rs.AddLayer(job_name)
        
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    se_lyr = rs.AddLayer("start_end", parent=main_lyr)
    rs.CurrentLayer(main_lyr)

    # --- 3. Repère ---
    origin_plane = rs.WorldXYPlane()
    if user_frame_id:
        for np in rs.NamedCPlanes():
            if np.Name == user_frame_id: origin_plane = np.Plane; break

    create_pose_block()
    rs.EnableRedraw(False)

    inst_data = []
    ctx = {'arcon': False, 'macro': "", 'label': ""}
    in_nop = False
    instance_idx = 0

    # --- 4. Placement des Instances ---
    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue
        if raw.startswith("*"): ctx['label'] = raw
        elif "ARCON" in raw: ctx['arcon'] = True
        elif "ARCOF" in raw: ctx['arcon'] = False
        
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
                
                rs.SetUserText(inst_id, "uuid_origin", str(inst_id))
                rs.SetUserText(inst_id, "ID_C", c_id)
                rs.SetUserText(inst_id, "Type", move_type)
                
                inst_data.append({'idx': str(instance_idx), 'pos': target_pt, 'arcon': ctx['arcon'], 'uuid': str(inst_id)})
                instance_idx += 1

    # --- 5. Création des Courbes et Collecte des UUIDs ---
    rs.CurrentLayer(traj_lyr)
    created_curves_uuids = []

    if len(inst_data) > 1:
        segment = [inst_data[0]]
        last_state = inst_data[0]['arcon']

        def create_traj(data, state):
            if len(data) < 2: return
            pl_id = rs.AddPolyline([d['pos'] for d in data])
            prefix = "ARCON" if state else "ARCOF"
            rs.ObjectName(pl_id, "{} {}-{}".format(prefix, data[0]['idx'], data[-1]['idx']))
            rs.ObjectColor(pl_id, (255,0,0) if state else (150,150,150))
            
            # Métadonnées Courbe
            rs.SetUserText(pl_id, "uuid_origin", str(pl_id))
            for i, d in enumerate(data):
                rs.SetUserText(pl_id, "Pt_{}".format(i), d['idx'])
                rs.SetUserText(pl_id, "UUID_{}".format(i), d['uuid'])
            
            created_curves_uuids.append(str(pl_id))

        for i in range(1, len(inst_data)):
            if inst_data[i]['arcon'] != last_state:
                create_traj(segment, last_state)
                segment = [inst_data[i-1], inst_data[i]]
                last_state = inst_data[i]['arcon']
            else:
                segment.append(inst_data[i])
        create_traj(segment, last_state)

    # --- 6. Start & End ---
    if inst_data:
        rs.CurrentLayer(se_lyr)
        rs.AddRectangle(rg.Plane(inst_data[0]['pos'], rg.Vector3d.ZAxis), 5, 5)
        rs.AddSphere(inst_data[-1]['pos'], 3)

    # --- 7. Création du Texte PROGRAM (L'objet de contrôle) ---
    rs.CurrentLayer(main_lyr)
    prog_text_id = rs.AddText("".join(lines), [0,0,0], height=10.0)
    rs.ObjectName(prog_text_id, job_name)
    
    # UserStrings critiques pour le script d'analyse suivant
    rs.SetUserText(prog_text_id, "type", "program")
    rs.SetUserText(prog_text_id, "uuid_origin", str(prog_text_id))
    
    # On stocke l'ordre des courbes
    for i, crv_uuid in enumerate(created_curves_uuids):
        rs.SetUserText(prog_text_id, "Crv_{}".format(i), crv_uuid)

    rs.EnableRedraw(True)
    rs.Redraw()
    print("Importation de {} terminée. {} courbes séquencées.".format(job_name, len(created_curves_uuids)))

if __name__ == "__main__":
    import_jbi_final()

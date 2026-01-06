import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math
import re

def create_pose_block():
    if rs.IsBlock("Pose"): return
    current_lyr = rs.CurrentLayer()
    if not rs.IsLayer("_pose_def"): rs.AddLayer("_pose_def", (128,128,128))
    rs.CurrentLayer("_pose_def")
    p0 = [0,0,0]
    lx = rs.AddLine(p0, [10,0,0]); rs.ObjectColor(lx, (255,0,0))
    ly = rs.AddLine(p0, [0,10,0]); rs.ObjectColor(ly, (0,255,0))
    lz = rs.AddLine(p0, [0,0,10]); rs.ObjectColor(lz, (0,0,255))
    rs.AddBlock([lx, ly, lz], p0, "Pose", delete_input=True)
    rs.CurrentLayer(current_lyr)

def create_start_end_blocks():
    """Crée les définitions de blocs pour le départ (Cube) et l'arrivée (Sphère)."""
    if not rs.IsLayer("_start_end_def"): rs.AddLayer("_start_end_def", (200,200,200))
    current_lyr = rs.CurrentLayer()
    rs.CurrentLayer("_start_end_def")
    
    if not rs.IsBlock("Start"):
        box = rs.AddBox([[-2.5,-2.5,-2.5],[2.5,-2.5,-2.5],[2.5,2.5,-2.5],[-2.5,2.5,-2.5],
                         [-2.5,-2.5,2.5],[2.5,-2.5,2.5],[2.5,2.5,2.5],[-2.5,2.5,2.5]])
        rs.AddBlock([box], [0,0,0], "Start", delete_input=True)
        
    if not rs.IsBlock("End"):
        sph = rs.AddSphere([0,0,0], 3)
        rs.AddBlock([sph], [0,0,0], "End", delete_input=True)
        
    rs.CurrentLayer(current_lyr)

def import_jbi_final():
    filepath = rs.OpenFileName("Ouvrir fichier JBI", "JBI Files (*.jbi)|*.jbi||")
    if not filepath: return
    with open(filepath, 'r') as f: lines = f.readlines()

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

    full_path = "{}::{}".format(folder_name, job_name) if folder_name else job_name
    if rs.IsLayer(full_path):
        rs.MessageBox("Erreur : Le calque '{}' existe déjà.".format(full_path), 16)
        return

    # Gestion Calques
    if folder_name:
        if not rs.IsLayer(folder_name): rs.AddLayer(folder_name)
        main_lyr = rs.AddLayer(job_name, parent=folder_name)
    else:
        main_lyr = rs.AddLayer(job_name)
    
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    se_lyr = rs.AddLayer("start_end", parent=main_lyr)

    create_pose_block()
    create_start_end_blocks()
    
    rs.EnableRedraw(False)
    origin_plane = rs.WorldXYPlane()
    inst_data = []
    ctx = {'arcon': False}
    in_nop = False
    instance_idx = 0

    # Parsing Instructions
    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue
        if "ARCON" in raw: ctx['arcon'] = True
        elif "ARCOF" in raw: ctx['arcon'] = False
        
        m_match = re.search(r"(MOVL|MOVJ|SMOVL)\s+(C\d+)", raw)
        if m_match:
            move_type, c_id = m_match.group(1), m_match.group(2)
            if c_id in pos_dict:
                p = pos_dict[c_id]
                target_pt = origin_plane.PointAt(p[0], p[1], p[2])
                
                # Placement Pose
                rs.CurrentLayer(main_lyr)
                inst_id = rs.InsertBlock("Pose", target_pt)
                rs.ObjectName(inst_id, str(instance_idx))
                rs.SetUserText(inst_id, "uuid_origin", str(inst_id))
                
                inst_data.append({'idx': str(instance_idx), 'pos': target_pt, 'arcon': ctx['arcon'], 'uuid': str(inst_id)})
                instance_idx += 1

    # Courbes
    rs.CurrentLayer(traj_lyr)
    created_curves_uuids = []
    if len(inst_data) > 1:
        def create_traj(data, state):
            pl_id = rs.AddPolyline([d['pos'] for d in data])
            rs.ObjectColor(pl_id, (255,0,0) if state else (150,150,150))
            rs.SetUserText(pl_id, "uuid_origin", str(pl_id))
            for i, d in enumerate(data):
                rs.SetUserText(pl_id, "Pt_{}".format(i), d['idx'])
            created_curves_uuids.append(str(pl_id))

        segment = [inst_data[0]]
        last_state = inst_data[0]['arcon']
        for i in range(1, len(inst_data)):
            if inst_data[i]['arcon'] != last_state:
                create_traj(segment, last_state)
                segment = [inst_data[i-1], inst_data[i]]
                last_state = inst_data[i]['arcon']
            else:
                segment.append(inst_data[i])
        create_traj(segment, last_state)

    # Start & End Instances
    if inst_data:
        rs.CurrentLayer(se_lyr)
        rs.InsertBlock("Start", inst_data[0]['pos'])
        rs.InsertBlock("End", inst_data[-1]['pos'])

    # Bloc Programme (Définition)
    def_layer = "_program_def"
    if not rs.IsLayer(def_layer): rs.AddLayer(def_layer, (100, 100, 100))
    rs.CurrentLayer(def_layer)
    txt_id = rs.AddText("".join(lines), [0,0,0], height=10.0)
    
    # On utilise un nom de bloc unique pour éviter les conflits
    block_name = "PROG_" + job_name
    if rs.IsBlock(block_name): rs.DeleteBlock(block_name)
    rs.AddBlock([txt_id], [0,0,0], block_name, delete_input=True)
    
    rs.CurrentLayer(main_lyr)
    instance_id = rs.InsertBlock(block_name, [0,0,0])
    rs.SetUserText(instance_id, "type", "program")
    for i, crv_uuid in enumerate(created_curves_uuids):
        rs.SetUserText(instance_id, "Crv_{}".format(i), crv_uuid)

    rs.EnableRedraw(True)
    print("Importation terminée.")

if __name__ == "__main__":
    import_jbi_final()

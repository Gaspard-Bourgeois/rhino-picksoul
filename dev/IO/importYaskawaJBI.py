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
    if not rs.IsLayer("_start_end_def"): rs.AddLayer("_start_end_def", (200,200,200))
    current_lyr = rs.CurrentLayer()
    rs.CurrentLayer("_start_end_def")
    if not rs.IsBlock("Start"):
        box = rs.AddBox([[-2.5,-2.5,-2.5],[2.5,-2.5,-2.5],[2.5,2.5,-2.5],[-2.5,2.5,-2.5],[-2.5,-2.5,2.5],[2.5,-2.5,2.5],[2.5,2.5,2.5],[-2.5,2.5,2.5]])
        rs.AddBlock([box], [0,0,0], "Start", delete_input=True)
    if not rs.IsBlock("End"):
        sph = rs.AddSphere([0,0,0], 3)
        rs.AddBlock([sph], [0,0,0], "End", delete_input=True)
    rs.CurrentLayer(current_lyr)

def import_jbi_final():
    filepath = rs.OpenFileName("Ouvrir fichier JBI", "JBI Files (*.jbi)|*.jbi||")
    if not filepath: return
    with open(filepath, 'r', encoding='utf-8') as f: lines = f.readlines()

    job_name = "NONAME"
    folder_name = ""
    user_frame_id = None
    pos_dict = {}

    # Parsing en-tête et positions
    for line in lines:
        l = line.strip()
        if l.startswith("//NAME"): job_name = l.split(" ")[1]
        elif l.startswith("///FOLDERNAME"): folder_name = l.split(" ")[1]
        elif l.startswith("///USER"): user_frame_id = l.split(" ")[1]
        elif l.startswith("C") and "=" in l:
            parts = l.split("=")
            pos_dict[parts[0]] = [float(v) for v in parts[1].split(",")]

    # Gestion des calques
    full_path = "{}::{}".format(folder_name, job_name) if folder_name else job_name
    if rs.IsLayer(full_path):
        rs.MessageBox("Le calque '{}' existe déjà.".format(full_path), 16)
        return

    main_lyr = rs.AddLayer(job_name, parent=folder_name if folder_name else None)
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    se_lyr = rs.AddLayer("start_end", parent=main_lyr)

    create_pose_block()
    create_start_end_blocks()
    
    rs.EnableRedraw(False)
    origin_plane = rs.WorldXYPlane() # À adapter si user_frame_id est géré
    inst_data = []
    ctx = {'arcon': False}
    in_nop = False
    idx = 0

    # Parsing Instructions avec paramètres étendus
    # Regex: (Type) (C) (BC optionnel) (V/VJ) (PL)
    pattern = r"(MOVL|MOVJ|SMOVL)\s+(C\d+)(?:\s+(BC\d+))?(?:\s+(V|VJ)=([\d\.]+))?(?:\s+PL=(\d+))?"

    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue
        if "ARCON" in raw: ctx['arcon'] = True
        elif "ARCOF" in raw: ctx['arcon'] = False
        
        match = re.search(pattern, raw)
        if match:
            m_type, c_id, bc_id, v_type, v_val, pl_val = match.groups()
            if c_id in pos_dict:
                p = pos_dict[c_id]
                target_pt = origin_plane.PointAt(p[0], p[1], p[2])
                
                rs.CurrentLayer(main_lyr)
                inst_id = rs.InsertBlock("Pose", target_pt)
                rs.ObjectName(inst_id, str(idx))
                
                # Stockage Meta sur la Pose
                rs.SetUserText(inst_id, "uuid_origin", str(inst_id))
                rs.SetUserText(inst_id, "ID_C", c_id)
                if bc_id: rs.SetUserText(inst_id, "ID_BC", bc_id)
                rs.SetUserText(inst_id, "Type", m_type)
                rs.SetUserText(inst_id, "V_Type", v_type or "")
                rs.SetUserText(inst_id, "V_Val", v_val or "")
                rs.SetUserText(inst_id, "PL", pl_val or "")
                rs.SetUserText(inst_id, "ArcState", "ARCON" if ctx['arcon'] else "ARCOF")

                inst_data.append({'idx': str(idx), 'pos': target_pt, 'arcon': ctx['arcon'], 'uuid': str(inst_id)})
                idx += 1

    # Création des trajectoires
    rs.CurrentLayer(traj_lyr)
    created_curves_uuids = []
    if len(inst_data) > 1:
        def create_traj(data, state):
            if len(data) < 2: return
            pl_id = rs.AddPolyline([d['pos'] for d in data])
            pref = "ARCON" if state else "ARCOF"
            rs.ObjectName(pl_id, "{} {}-{}".format(pref, data[0]['idx'], data[-1]['idx']))
            rs.ObjectColor(pl_id, (255,0,0) if state else (150,150,150))
            rs.SetUserText(pl_id, "uuid_origin", str(pl_id))
            rs.SetUserText(pl_id, "ArcState", pref)
            for i, d in enumerate(data):
                rs.SetUserText(pl_id, "Pt_{}".format(i), d['idx'])
                rs.SetUserText(pl_id, "UUID_{}".format(i), d['uuid'])
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

    # Start/End
    if inst_data:
        rs.CurrentLayer(se_lyr)
        rs.InsertBlock("Start", inst_data[0]['pos'])
        rs.InsertBlock("End", inst_data[-1]['pos'])

    # Bloc Programme de référence
    def_layer = "_program_def"
    if not rs.IsLayer(def_layer): rs.AddLayer(def_layer, (100, 100, 100))
    rs.CurrentLayer(def_layer)
    txt_id = rs.AddText("".join(lines), [0,0,0], height=10.0)
    
    b_name = "PROG_" + job_name
    if rs.IsBlock(b_name): rs.DeleteBlock(b_name)
    rs.AddBlock([txt_id], [0,0,0], b_name, delete_input=True)
    
    rs.CurrentLayer(main_lyr)
    prog_inst = rs.InsertBlock(b_name, [0,0,0])
    rs.SetUserText(prog_inst, "type", "program")
    for i, u in enumerate(created_curves_uuids):
        rs.SetUserText(prog_inst, "Crv_{}".format(i), u)

    rs.EnableRedraw(True)
    print("Import JBI réussi.")

if __name__ == "__main__":
    import_jbi_final()

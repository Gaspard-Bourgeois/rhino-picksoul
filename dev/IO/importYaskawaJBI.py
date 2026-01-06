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
    rs.AddBlock([lx, ly, lz], p0, "Pose", True)
    rs.CurrentLayer(current_lyr)

def create_start_end_blocks():
    if not rs.IsLayer("_start_end_def"): rs.AddLayer("_start_end_def", (200,200,200))
    current_lyr = rs.CurrentLayer()
    rs.CurrentLayer("_start_end_def")
    if not rs.IsBlock("Start"):
        box = rs.AddBox([[-2.5,-2.5,-2.5],[2.5,-2.5,-2.5],[2.5,2.5,-2.5],[-2.5,2.5,-2.5],[-2.5,-2.5,2.5],[2.5,-2.5,2.5],[2.5,2.5,2.5],[-2.5,2.5,2.5]])
        rs.AddBlock([box], [0,0,0], "Start", True)
    if not rs.IsBlock("End"):
        sph = rs.AddSphere([0,0,0], 3)
        rs.AddBlock([sph], [0,0,0], "End", True)
    rs.CurrentLayer(current_lyr)

def import_jbi_final():
    filepath = rs.OpenFileName("Ouvrir fichier JBI", "JBI Files (*.jbi)|*.jbi||")
    if not filepath: return
    f = open(filepath, 'r')
    lines = f.readlines()
    f.close()

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

    # Correction Hiérarchie Calques
    if folder_name:
        if not rs.IsLayer(folder_name): rs.AddLayer(folder_name)
        main_lyr = rs.AddLayer(job_name, parent=folder_name)
    else:
        main_lyr = rs.AddLayer(job_name)
    
    traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
    
    create_pose_block()
    create_start_end_blocks()
    rs.EnableRedraw(False)
    
    origin_plane = rs.WorldXYPlane()
    inst_data = []
    ctx = {'arcon': False}
    in_nop = False
    idx = 0

    # Regex modifiée pour inclure les commentaires (group 7)
    pattern = r"(MOVL|MOVJ|SMOVL)\s+(C\d+)(?:\s+(BC\d+))?(?:\s+(V|VJ)=([\d\.]+))?(?:\s+PL=(\d+))?(?:\s*//(.*))?"

    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue
        
        # Détection d'état avant le mouvement
        if "ARCON" in raw: ctx['arcon'] = True
        elif "ARCOF" in raw: ctx['arcon'] = False
        
        m = re.search(pattern, raw)
        if m:
            m_type, c_id, bc_id, v_type, v_val, pl_val, comment = m.groups()
            
            if c_id in pos_dict:
                p = pos_dict[c_id]
                pt = origin_plane.PointAt(p[0], p[1], p[2])
                rs.CurrentLayer(main_lyr)
                inst_id = rs.InsertBlock("Pose", pt)
                rs.ObjectName(inst_id, str(idx))
                
                # Restauration clés d'origine
                rs.SetUserText(inst_id, "uuid_origin", str(inst_id))
                rs.SetUserText(inst_id, "ID_C", c_id)
                if bc_id: rs.SetUserText(inst_id, "BC", bc_id)
                rs.SetUserText(inst_id, "Type", m_type)
                if v_val: rs.SetUserText(inst_id, v_type, v_val)
                if pl_val: rs.SetUserText(inst_id, "PL", pl_val)
                
                # NOUVEAU: Stockage du commentaire et de l'état
                if comment: rs.SetUserText(inst_id, "Comment", comment.strip())
                rs.SetUserText(inst_id, "State", "ARCON" if ctx['arcon'] else "ARCOF")
                
                inst_data.append({'idx': str(idx), 'pos': pt, 'arcon': ctx['arcon'], 'uuid': str(inst_id)})
                idx += 1

    # Trajectoires
    rs.CurrentLayer(traj_lyr)
    created_uuids = []
    if len(inst_data) > 1:
        def build_t(data, state):
            if len(data) < 2: return
            pid = rs.AddPolyline([d['pos'] for d in data])
            pref = "ARCON" if state else "ARCOF"
            rs.ObjectName(pid, "{} {}-{}".format(pref, data[0]['idx'], data[-1]['idx']))
            rs.ObjectColor(pid, (255,0,0) if state else (150,150,150))
            rs.SetUserText(pid, "uuid_origin", str(pid))
            for i, d in enumerate(data):
                rs.SetUserText(pid, "Pt_{}".format(i), d['idx'])
                rs.SetUserText(pid, "UUID_{}".format(i), d['uuid'])
            created_uuids.append(str(pid))

        seg = [inst_data[0]]
        last_s = inst_data[0]['arcon']
        for i in range(1, len(inst_data)):
            if inst_data[i]['arcon'] != last_s:
                build_t(seg, last_s)
                seg = [inst_data[i-1], inst_data[i]]
                last_s = inst_data[i]['arcon']
            else: seg.append(inst_data[i])
        build_t(seg, last_s)

    # Start/End sur Main Layer
    if inst_data:
        rs.CurrentLayer(main_lyr)
        rs.InsertBlock("Start", inst_data[0]['pos'])
        rs.InsertBlock("End", inst_data[-1]['pos'])

    # Definition Bloc Program
    def_lyr = "_program_def"
    if not rs.IsLayer(def_lyr): rs.AddLayer(def_lyr)
    rs.CurrentLayer(def_lyr)
    txt_id = rs.AddText("".join(lines), [0,0,0], 10.0)
    b_name = "PROG_" + job_name
    if rs.IsBlock(b_name): rs.DeleteBlock(b_name)
    rs.AddBlock([txt_id], [0,0,0], b_name, True)
    
    rs.CurrentLayer(main_lyr)
    prog_inst = rs.InsertBlock(b_name, [0,0,0])
    rs.SetUserText(prog_inst, "type", "program")
    # On stocke l'ordre des courbes originales
    for i, u in enumerate(created_uuids): rs.SetUserText(prog_inst, "Crv_{}".format(i), u)

    rs.EnableRedraw(True)

if __name__ == "__main__":
    import_jbi_final()

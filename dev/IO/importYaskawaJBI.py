import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
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
    
    with open(filepath, 'r') as f:
        lines = f.readlines()

    job_name = "NONAME"
    folder_name = ""
    pos_dict = {}

    # Lecture des définitions (Header)
    for line in lines:
        l = line.strip()
        if l.startswith("//NAME"): job_name = l.split(" ")[1]
        elif l.startswith("///FOLDERNAME"): folder_name = l.split(" ")[1]
        elif l.startswith("C") and "=" in l:
            parts = l.split("=")
            try:
                pos_dict[parts[0]] = [float(v) for v in parts[1].split(",")]
            except: pass

    # Création Calques
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
    
    # ETAT PAR DEFAUT = ARCOF (False)
    ctx = {'arcon': False} 
    in_nop = False
    idx = 0

    # Regex capture : Type, C_ID, BC_ID(opt), V_Type(opt), V_Val(opt), PL(opt), Comment(opt)
    pattern = r"(MOVL|MOVJ|SMOVL)\s+(C\d+)(?:\s+(BC\d+))?(?:\s+(V|VJ)=([\d\.]+))?(?:\s+PL=(\d+))?(?:.*//(.*))?"

    for line in lines:
        raw = line.strip()
        if raw == "NOP": in_nop = True; continue
        if not in_nop or raw == "END": continue
        
        # 1. Mise à jour de l'état AVANT de traiter la pose courante
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
                
                # UserText
                rs.SetUserText(

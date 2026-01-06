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

    # Parsing préliminaire (Header)
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
        
        # Mise à jour de l'état AVANT de traiter la pose courante
        # Si une ligne contient ARCON, l'état devient ARCON pour la suite
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
                rs.SetUserText(inst_id, "uuid_origin", str(inst_id))
                rs.SetUserText(inst_id, "ID_C", c_id)
                if bc_id: rs.SetUserText(inst_id, "BC", bc_id)
                rs.SetUserText(inst_id, "Type", m_type)
                if v_val: rs.SetUserText(inst_id, v_type, v_val)
                if pl_val: rs.SetUserText(inst_id, "PL", pl_val)
                if comment: rs.SetUserText(inst_id, "Comment", comment.strip())
                
                # STOCKAGE DE L'ÉTAT ACTUEL DANS LA POSE
                current_state = "ARCON" if ctx['arcon'] else "ARCOF"
                rs.SetUserText(inst_id, "State", current_state)
                
                inst_data.append({'idx': str(idx), 'pos': pt, 'state': current_state, 'uuid': str(inst_id)})
                idx += 1

    # Création des Trajectoires (Courbes)
    rs.CurrentLayer(traj_lyr)
    created_crv_uuids = []
    
    if len(inst_data) > 1:
        # On regroupe les points par segments de même état.
        # Règle : Le segment entre P(i-1) et P(i) prend la couleur de l'état de P(i).
        
        # Initialisation
        current_poly_pts = [inst_data[0]['pos']]
        current_poly_uuids = [inst_data[0]['uuid']]
        current_indices = [0]
        # L'état du premier segment dépend du 2ème point (le premier mouvement réel)
        last_seg_state = inst_data[1]['state'] 

        def commit_polyline(pts, uuids, state, indices):
            if len(pts) < 2: return
            pid = rs.AddPolyline(pts)
            start_i = indices[0]
            end_i = indices[-1]
            rs.ObjectName(pid, "{} {}-{}".format(state, start_i, end_i))
            rs.ObjectColor(pid, (255,0,0) if state == "ARCON" else (150,150,150))
            
            rs.SetUserText(pid, "uuid_origin", str(pid))
            # Stockage des UUIDs pour retrouver les poses lors du rebuild
            for k, u in enumerate(uuids):
                rs.SetUserText(pid, "UUID_{}".format(k), u)
                rs.SetUserText(pid, "Pt_{}".format(k), str(indices[k]))
            created_crv_uuids.append(str(pid))

        for i in range(1, len(inst_data)):
            curr_state = inst_data[i]['state']
            
            if curr_state != last_seg_state:
                # Changement d'état : on finit la courbe courante au point actuel
                current_poly_pts.append(inst_data[i]['pos'])
                current_poly_uuids.append(inst_data[i]['uuid'])
                current_indices.append(i)
                
                commit_polyline(current_poly_pts, current_poly_uuids, last_seg_state, current_indices)
                
                # On redémarre une nouvelle courbe à partir de ce point
                current_poly_pts = [inst_data[i]['pos']]
                current_poly_uuids = [inst_data[i]['uuid']]
                current_indices = [i]
                last_seg_state = curr_state
            else:
                current_poly_pts.append(inst_data[i]['pos'])
                current_poly_uuids.append(inst_data[i]['uuid'])
                current_indices.append(i)
        
        # Commit final
        commit_polyline(current_poly_pts, current_poly_uuids, last_seg_state, current_indices)

    # Start/End
    if inst_data:
        rs.CurrentLayer(main_lyr)
        rs.InsertBlock("Start", inst_data[0]['pos'])
        rs.InsertBlock("End", inst_data[-1]['pos'])

    # Bloc Program (pour garder l'ordre)
    def_lyr = "_program_def"
    if not rs.IsLayer(def_lyr): rs.AddLayer(def_lyr)
    rs.CurrentLayer(def_lyr)
    txt_id = rs.AddText("SOURCE_JBI", [0,0,0], 1.0) # Placeholder
    b_name = "PROG_" + job_name
    if rs.IsBlock(b_name): rs.DeleteBlock(b_name)
    rs.AddBlock([txt_id], [0,0,0], b_name, True)
    
    rs.CurrentLayer(main_lyr)
    prog_inst = rs.InsertBlock(b_name, [0,0,0])
    rs.SetUserText(prog_inst, "type", "program")
    # On stocke l'ordre des courbes pour le rebuild
    for i, u in enumerate(created_crv_uuids): rs.SetUserText(prog_inst, "Crv_{}".format(i), u)

    rs.EnableRedraw(True)

if __name__ == "__main__":
    import_jbi_final()

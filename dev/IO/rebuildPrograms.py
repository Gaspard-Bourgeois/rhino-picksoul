import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def analyze_and_rebuild_from_text():
    # 1. Sélection intelligente
    selected_objs = rs.GetObjects("Sélectionnez un programme ou un de ses éléments", preselect=True)
    if not selected_objs: return

    program_instances = []
    
    for obj in selected_objs:
        # Si c'est directement l'instance du programme
        if rs.IsBlockInstance(obj) and rs.GetUserText(obj, "type") == "program":
            if obj not in program_instances: program_instances.append(obj)
            continue
        
        # Sinon, on cherche si l'objet appartient à un calque de programme
        layer = rs.ObjectLayer(obj)
        # On remonte au calque parent qui contient l'instance "program"
        parent_layer = layer.split("::")[0] if "::" in layer else layer
        
        # On cherche l'instance de bloc "program" sur ce calque
        potential_progs = rs.ObjectsByLayer(parent_layer)
        for p in potential_progs:
            if rs.IsBlockInstance(p) and rs.GetUserText(p, "type") == "program":
                if p not in program_instances: program_instances.append(p)

    if not program_instances:
        rs.MessageBox("Aucun programme associé à la sélection n'a été trouvé.")
        return

    rs.EnableRedraw(False)

    for prog_inst in program_instances:
        main_lyr = rs.ObjectLayer(prog_inst)
        traj_lyr_name = main_lyr + "::trajs_arcon_arcof"
        se_lyr_name = main_lyr + "::start_end"
        
        # Collecte des données de reconstruction (Courbes -> Points)
        keys = sorted([k for k in rs.GetUserText(prog_inst) if k.startswith("Crv_")], 
                      key=lambda x: int(x.split("_")[1]))
        
        ordered_curve_origins = [rs.GetUserText(prog_inst, k) for k in keys]
        
        # On mappe les objets actuels par leur uuid_origin pour retrouver les copies
        all_objs = rs.AllObjects()
        obj_map = {}
        for o in all_objs:
            u_orig = rs.GetUserText(o, "uuid_origin")
            if u_orig:
                if u_orig not in obj_map: obj_map[u_orig] = []
                obj_map[u_orig].append(o)

        full_sequence = [] # Liste de {'pos', 'arcon'}
        
        for u_crv_orig in ordered_curve_origins:
            if u_crv_orig not in obj_map: continue
            
            # On prend la dernière instance de la courbe (la copie la plus récente)
            current_crv = obj_map[u_crv_orig][-1] 
            is_arcon = rs.ObjectColor(current_crv) == (255,0,0) or "ARCON" in (rs.ObjectName(current_crv) or "")
            
            vertices = rs.PolylineVertices(current_crv)
            if not vertices: continue
            
            # Pour chaque segment, on ajoute les points. 
            # Attention : pour éviter les doublons aux jointures, on gère l'overlap
            start_idx = 1 if len(full_sequence) > 0 else 0
            for i in range(start_idx, len(vertices)):
                full_sequence.append({'pos': vertices[i], 'arcon': is_arcon})

        if not full_sequence: continue

        # --- NETTOYAGE ET RECONSTRUCTION ---
        
        # 1. Nettoyer les anciennes poses et trajectoires
        old_poses = rs.ObjectsByLayer(main_lyr)
        for op in old_poses:
            if rs.IsBlockInstance(op) and rs.BlockInstanceName(op) == "Pose": rs.DeleteObject(op)
            
        if rs.IsLayer(traj_lyr_name):
            rs.DeleteObjects(rs.ObjectsByLayer(traj_lyr_name))
        else:
            rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)

        if rs.IsLayer(se_lyr_name):
            rs.DeleteObjects(rs.ObjectsByLayer(se_lyr_name))
        else:
            rs.AddLayer("start_end", parent=main_lyr)

        # 2. Nouvelles Poses
        rs.CurrentLayer(main_lyr)
        for i, data in enumerate(full_sequence):
            new_p = rs.InsertBlock("Pose", data['pos'])
            rs.ObjectName(new_p, str(i))
            rs.SetUserText(new_p, "uuid_origin", str(new_p))

        # 3. Nouvelles Trajectoires
        rs.CurrentLayer(traj_lyr_name)
        if len(full_sequence) > 1:
            temp_pts = [full_sequence[0]['pos']]
            last_state = full_sequence[0]['arcon']
            
            def build_pl(pts, state):
                if len(pts) < 2: return
                pid = rs.AddPolyline(pts)
                rs.ObjectColor(pid, (255,0,0) if state else (150,150,150))
                rs.SetUserText(pid, "uuid_origin", str(pid))

            for i in range(1, len(full_sequence)):
                if full_sequence[i]['arcon'] != last_state:
                    build_pl(temp_pts, last_state)
                    temp_pts = [full_sequence[i-1]['pos'], full_sequence[i]['pos']]
                    last_state = full_sequence[i]['arcon']
                else:
                    temp_pts.append(full_sequence[i]['pos'])
            build_pl(temp_pts, last_state)

        # 4. Start & End
        rs.CurrentLayer(se_lyr_name)
        rs.InsertBlock("Start", full_sequence[0]['pos'])
        rs.InsertBlock("End", full_sequence[-1]['pos'])

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée.")

if __name__ == "__main__":
    analyze_and_rebuild_from_text()

import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def analyze_and_rebuild_from_text():
    # 1. Sélection intelligente (Objet ou Calque)
    selection = rs.GetObjects("Sélectionnez le programme, une courbe ou une pose", preselect=True)
    if not selection: return

    program_instances = []
    for obj in selection:
        # Cas 1: Directement l'instance programme
        if rs.IsBlockInstance(obj) and rs.GetUserText(obj, "type") == "program":
            if obj not in program_instances: program_instances.append(obj)
        else:
            # Cas 2: Objet dans le calque du programme
            lyr = rs.ObjectLayer(obj)
            root_lyr = lyr.split("::")[0]
            objs_in_root = rs.ObjectsByLayer(root_lyr)
            for o in objs_in_root:
                if rs.IsBlockInstance(o) and rs.GetUserText(o, "type") == "program":
                    if o not in program_instances: program_instances.append(o)

    if not program_instances:
        rs.MessageBox("Impossible de trouver le bloc 'program' associé.")
        return

    rs.EnableRedraw(False)

    for prog_inst in program_instances:
        main_lyr = rs.ObjectLayer(prog_inst)
        traj_lyr = main_lyr + "::trajs_arcon_arcof"
        se_lyr = main_lyr + "::start_end"

        # 2. Récupération de l'ordre des courbes via le bloc program
        crv_keys = sorted([k for k in rs.GetUserText(prog_inst) if k.startswith("Crv_")], key=lambda x: int(x.split("_")[1]))
        ordered_uuids = [rs.GetUserText(prog_inst, k) for k in crv_keys]

        # 3. Collecte de la géométrie actuelle (incluant copies)
        all_objs = rs.AllObjects()
        obj_map = {} # { uuid_origin : [list of objects] }
        for o in all_objs:
            u_orig = rs.GetUserText(o, "uuid_origin")
            if u_orig:
                if u_orig not in obj_map: obj_map[u_orig] = []
                obj_map[u_orig].append(o)

        sequence_data = [] # {pos, meta_dict}
        
        for u_orig in ordered_uuids:
            if u_orig not in obj_map: continue
            
            # On prend la dernière instance trouvée (si copie, c'est la plus récente)
            target_crv = obj_map[u_orig][-1]
            verts = rs.PolylineVertices(target_crv)
            if not verts: continue
            
            # On récupère les UserStrings de la courbe originale ou du bloc Pose d'origine
            # pour restaurer V, PL, BC etc.
            arc_state = rs.GetUserText(target_crv, "ArcState") or "ARCOF"
            
            for i in range(len(verts)):
                # Éviter les doublons aux points de jonction des courbes
                if i == 0 and len(sequence_data) > 0: continue
                
                # Récupérer les métadonnées de la pose d'origine associée à ce point
                u_pose_orig = rs.GetUserText(target_crv, "UUID_{}".format(i))
                meta = {}
                if u_pose_orig and u_pose_orig in obj_map:
                    pose_ref = obj_map[u_pose_orig][0]
                    keys = ["ID_C", "ID_BC", "Type", "V_Type", "V_Val", "PL"]
                    for k in keys: meta[k] = rs.GetUserText(pose_ref, k)
                
                sequence_data.append({
                    'pos': verts[i],
                    'arc': arc_state,
                    'meta': meta
                })

        # 4. Nettoyage In-Place
        # Supprimer les poses existantes sur le calque principal
        for o in rs.ObjectsByLayer(main_lyr):
            if rs.IsBlockInstance(o) and rs.BlockInstanceName(o) == "Pose": rs.DeleteObject(o)
        
        # Supprimer courbes et start/end
        if rs.IsLayer(traj_lyr): rs.DeleteObjects(rs.ObjectsByLayer(traj_lyr))
        if rs.IsLayer(se_lyr): rs.DeleteObjects(rs.ObjectsByLayer(se_lyr))

        # 5. Reconstruction
        new_poses_uuids = []
        rs.CurrentLayer(main_lyr)
        for i, data in enumerate(sequence_data):
            p_id = rs.InsertBlock("Pose", data['pos'])
            rs.ObjectName(p_id, str(i))
            rs.SetUserText(p_id, "uuid_origin", str(p_id))
            # Restaurer les métadonnées
            for k, v in data['meta'].items(): 
                if v: rs.SetUserText(p_id, k, v)
            rs.SetUserText(p_id, "ArcState", data['arc'])
            new_poses_uuids.append(str(p_id))

        # Reconstruction des courbes avec noms corrects
        if not rs.IsLayer(traj_lyr): rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
        rs.CurrentLayer(traj_lyr)
        
        if len(sequence_data) > 1:
            temp_pts = [sequence_data[0]['pos']]
            temp_uuids = [new_poses_uuids[0]]
            last_arc = sequence_data[0]['arc']
            start_idx = 0

            def build(pts, arc, s_i, e_i, uids):
                if len(pts) < 2: return
                pid = rs.AddPolyline(pts)
                rs.ObjectName(pid, "{} {}-{}".format(arc, s_i, e_i))
                rs.ObjectColor(pid, (255,0,0) if arc == "ARCON" else (150,150,150))
                rs.SetUserText(pid, "uuid_origin", str(pid))
                rs.SetUserText(pid, "ArcState", arc)
                for j, u in enumerate(uids):
                    rs.SetUserText(pid, "UUID_{}".format(j), u)
                    rs.SetUserText(pid, "Pt_{}".format(j), str(s_i + j))

            for i in range(1, len(sequence_data)):
                if sequence_data[i]['arc'] != last_arc:
                    build(temp_pts, last_arc, start_idx, i-1, temp_uuids)
                    temp_pts = [sequence_data[i-1]['pos'], sequence_data[i]['pos']]
                    temp_uuids = [new_poses_uuids[i-1], new_poses_uuids[i]]
                    start_idx = i - 1
                    last_arc = sequence_data[i]['arc']
                else:
                    temp_pts.append(sequence_data[i]['pos'])
                    temp_uuids.append(new_poses_uuids[i])
            build(temp_pts, last_arc, start_idx, len(sequence_data)-1, temp_uuids)

        # Start/End
        if not rs.IsLayer(se_lyr): rs.AddLayer("start_end", parent=main_lyr)
        rs.CurrentLayer(se_lyr)
        rs.InsertBlock("Start", sequence_data[0]['pos'])
        rs.InsertBlock("End", sequence_data[-1]['pos'])

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée avec succès (Métadonnées préservées).")

if __name__ == "__main__":
    analyze_and_rebuild_from_text()

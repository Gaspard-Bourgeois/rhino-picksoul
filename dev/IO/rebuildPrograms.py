import rhinoscriptsyntax as rs

def find_program_in_hierarchy(obj):
    """Remonte les calques pour trouver le bloc program."""
    curr_lyr = rs.ObjectLayer(obj)
    while curr_lyr:
        objs = rs.ObjectsByLayer(curr_lyr)
        for o in objs:
            if rs.IsBlockInstance(o) and rs.GetUserText(o, "type") == "program":
                return o
        # Remonte au parent
        curr_lyr = rs.ParentLayer(curr_lyr)
    return None

def analyze_and_rebuild_from_text():
    selection = rs.GetObjects("Sélectionnez un élément du programme", preselect=True)
    if not selection:
        rs.MessageBox("Aucune sélection effectuée.", 64)
        return

    progs = []
    for s in selection:
        p = find_program_in_hierarchy(s)
        if p and p not in progs: progs.append(p)

    if not progs:
        rs.MessageBox("Aucun bloc de type 'program' trouvé dans la hiérarchie.", 16)
        return

    rs.EnableRedraw(False)
    all_objs = rs.AllObjects()
    obj_map = {}
    for o in all_objs:
        u = rs.GetUserText(o, "uuid_origin")
        if u:
            if u not in obj_map: obj_map[u] = []
            obj_map[u].append(o)

    for prog in progs:
        main_lyr = rs.ObjectLayer(prog)
        traj_lyr = main_lyr + "::trajs_arcon_arcof"
        
        keys = sorted([k for k in rs.GetUserText(prog) if k.startswith("Crv_")], key=lambda x: int(x.split("_")[1]))
        ordered_uuids = [rs.GetUserText(prog, k) for k in keys]

        seq = []
        for u in ordered_uuids:
            if u not in obj_map: continue
            target = obj_map[u][-1] # Prend la copie la plus récente
            verts = rs.PolylineVertices(target)
            if not verts: continue
            
            arc = "ARCON" if "ARCON" in (rs.ObjectName(target) or "") else "ARCOF"
            for i in range(len(verts)):
                if i == 0 and len(seq) > 0: continue
                u_pose = rs.GetUserText(target, "UUID_{}".format(i))
                meta = {}
                if u_pose and u_pose in obj_map:
                    ref = obj_map[u_pose][0]
                    # Récupération de toutes les clés d'origine
                    for k in ["ID_C", "BC", "Type", "V", "VJ", "PL"]:
                        val = rs.GetUserText(ref, k)
                        if val: meta[k] = val
                seq.append({'pos': verts[i], 'arc': arc, 'meta': meta})

        if not seq: continue

        # Nettoyage In-Place
        to_del = []
        for o in rs.ObjectsByLayer(main_lyr):
            if rs.IsBlockInstance(o):
                name = rs.BlockInstanceName(o)
                if name in ["Pose", "Start", "End"]: to_del.append(o)
        if rs.IsLayer(traj_lyr): to_del.extend(rs.ObjectsByLayer(traj_lyr))
        rs.DeleteObjects(to_del)

        # Reconstruction
        new_uids = []
        rs.CurrentLayer(main_lyr)
        for i, d in enumerate(seq):
            nid = rs.InsertBlock("Pose", d['pos'])
            rs.ObjectName(nid, str(i))
            rs.SetUserText(nid, "uuid_origin", str(nid))
            for k, v in d['meta'].items(): rs.SetUserText(nid, k, v)
            new_uids.append(str(nid))

        # Start/End
        rs.InsertBlock("Start", seq[0]['pos'])
        rs.InsertBlock("End", seq[-1]['pos'])

        # Courbes
        if not rs.IsLayer(traj_lyr): rs.AddLayer("trajs_arcon_arcof", parent=main_lyr)
        rs.CurrentLayer(traj_lyr)
        
        if len(seq) > 1:
            pts, uids = [seq[0]['pos']], [new_uids[0]]
            last_a = seq[0]['arc']
            s_idx = 0
            
            def build_final(p, a, si, ui):
                if len(p) < 2: return
                pid = rs.AddPolyline(p)
                rs.ObjectName(pid, "{} {}-{}".format(a, si, si+len(p)-1))
                rs.ObjectColor(pid, (255,0,0) if a == "ARCON" else (150,150,150))
                rs.SetUserText(pid, "uuid_origin", str(pid))
                for j, uid in enumerate(ui):
                    rs.SetUserText(pid, "UUID_{}".format(j), uid)
                    rs.SetUserText(pid, "Pt_{}".format(j), str(si+j))

            for i in range(1, len(seq)):
                if seq[i]['arc'] != last_a:
                    build_final(pts, last_a, s_idx, uids)
                    pts, uids = [seq[i-1]['pos'], seq[i]['pos']], [new_uids[i-1], new_uids[i]]
                    s_idx, last_a = i-1, seq[i]['arc']
                else:
                    pts.append(seq[i]['pos'])
                    uids.append(new_uids[i])
            build_final(pts, last_a, s_idx, uids)

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée.")

if __name__ == "__main__":
    analyze_and_rebuild_from_text()

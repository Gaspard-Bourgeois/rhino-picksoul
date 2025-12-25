import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math

def solve_ik_v2():
    # --- 1. SÉLECTION ET ANALYSE DU BLOC ---
    all_blocks = rs.BlockNames()
    robot_defs = [b for b in all_blocks if "robot" in b.lower() and len(rs.BlockObjects(b)) == 6]

    if not robot_defs:
        print("Aucun bloc 'robot' valide trouvé.")
        return

    target_def = robot_defs[0]
    if len(robot_defs) > 1:
        target_def = rs.ListBox(robot_defs, "Choisissez le robot", "IK Robot")
    if not target_def: return

    # Ordonner les axes et extraire les limites (UserStrings dans la définition)
    parts = rs.BlockObjects(target_def)
    axis_order_keys = ["S", "L", "U", "R", "B", "T"]
    sorted_parts = [None] * 6
    limits = [] # Liste de tuples (min, max)

    for i, key in enumerate(axis_order_keys):
        for p_id in parts:
            name = rs.BlockInstanceName(p_id).upper()
            if key in name or str(i+1) in name:
                sorted_parts[i] = p_id
                # Lecture des limites (ex: S_min, S_max)
                try:
                    p_min = float(rs.GetUserString(p_id, key + "_min") or -360)
                    p_max = float(rs.GetUserString(p_id, key + "_max") or 360)
                except:
                    p_min, p_max = -360.0, 360.0
                limits.append((p_min, p_max))
                break

    if None in sorted_parts:
        print("Erreur d'indexation des axes.")
        return

    # --- 2. MATRICE D'INSERTION (BASE) ---
    base_matrix = rg.Transform.Identity
    named_planes = rs.NamedCPlanes()
    found_cp = next((cp for cp in named_planes if cp.Name == target_def), None)
    
    if found_cp:
        base_matrix = rg.Transform.PlaneToPlane(rg.Plane.WorldXY, found_cp.Plane)
    else:
        obj = rs.GetObject("Sélectionnez la base du robot (Enter pour CPlane actuel)", rs.filter.instance)
        if obj:
            base_matrix = rs.BlockInstanceMatrix(obj)
        else:
            base_matrix = rg.Transform.PlaneToPlane(rg.Plane.WorldXY, rs.ViewCPlane())

    # --- 3. POSITION ARTICULAIRE DE DÉPART (Lecture UserStrings) ---
    start_angles = [0.0] * 6
    ref_group = rs.GetObjects("Sélectionnez le groupe robot source (Enter pour pose 0)", rs.filter.instance)
    if ref_group and len(ref_group) == 6:
        # On cherche les UserStrings S, L, U, R, B, T sur les instances sélectionnées
        for i, key in enumerate(axis_order_keys):
            for obj in ref_group:
                val = rs.GetUserString(obj, key)
                if val:
                    start_angles[i] = float(val)
                    break

    # --- 4. CIBLES ---
    target_objs = rs.GetObjects("Sélectionnez les instances objectifs", rs.filter.instance)
    if not target_objs: return

    # --- 5. SOLVEUR CINÉMATIQUE (Position + Orientation + Limites) ---

    def get_fk_matrices(angles, base_xf, part_ids):
        current_xf = base_xf
        mats = []
        for i in range(6):
            local_xf = rs.BlockInstanceMatrix(part_ids[i])
            rotation = rg.Transform.Rotation(math.radians(angles[i]), rg.Vector3d.ZAxis, rg.Point3d.Origin)
            current_xf = current_xf * local_xf * rotation
            mats.append(current_xf)
        return mats

    def solve_ik_numerical(target_xf, start_angs, part_ids, base_xf, lims):
        curr_angs = list(start_angs)
        learning_rate = 0.1
        iterations = 200
        
        target_plane = rg.Plane.WorldXY
        target_plane.Transform(target_xf)

        for _ in range(iterations):
            fks = get_fk_matrices(curr_angs, base_xf, part_ids)
            tcp_xf = fks[5]
            tcp_plane = rg.Plane.WorldXY
            tcp_plane.Transform(tcp_xf)

            # Vecteur erreur Position
            delta_pos = target_plane.Origin - tcp_plane.Origin
            
            # Erreur Orientation (différence vectorielle des axes X, Y, Z)
            delta_rot = (target_plane.XAxis - tcp_plane.XAxis) + \
                        (target_plane.YAxis - tcp_plane.YAxis) + \
                        (target_plane.ZAxis - tcp_plane.ZAxis)

            error = delta_pos.Length + delta_rot.Length
            if error < 0.001: break

            # Descente de gradient simplifiée sur les 6 axes
            for i in range(6):
                # On teste une petite variation pour voir si l'erreur diminue
                curr_angs[i] += 0.01
                test_fks = get_fk_matrices(curr_angs, base_xf, part_ids)
                test_p = rg.Plane.WorldXY
                test_p.Transform(test_fks[5])
                
                test_err = target_plane.Origin.DistanceTo(test_p.Origin) + \
                           (target_plane.XAxis - test_p.XAxis).Length
                
                gradient = (test_err - error) / 0.01
                curr_angs[i] -= 0.01 # Reset
                
                # Mise à jour avec contraintes (Limites)
                new_val = curr_angs[i] - gradient * learning_rate * 100
                curr_angs[i] = max(min(new_val, lims[i][1]), lims[i][0])

        return curr_angs, error

    # --- 6. GÉNÉRATION DES RÉSULTATS ---
    for t_obj in target_objs:
        t_matrix = rs.BlockInstanceMatrix(t_obj)
        final_angs, final_err = solve_ik_numerical(t_matrix, start_angles, sorted_parts, base_matrix, limits)

        if final_err < 0.5: # Seuil de réussite
            results_fks = get_fk_matrices(final_angs, base_matrix, sorted_parts)
            group_ids = []
            for i in range(6):
                name = rs.BlockInstanceName(sorted_parts[i])
                new_id = rs.InsertBlock(name, rg.Point3d.Origin)
                rs.TransformObject(new_id, results_fks[i])
                # UserString de sortie (Section 6)
                rs.SetUserString(new_id, axis_order_keys[i], str(round(final_angs[i], 3)))
                group_ids.append(new_id)
            rs.GroupObjects(group_ids)
        else:
            print("Cible hors de portée ou contraintes trop strictes.")

solve_ik_v2()

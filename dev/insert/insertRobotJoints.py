# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 1. Résolution des entrées
    robot_name, instance_index, group = resolve_input()
    if robot_name is None:
        return

    # 2. Angles et limites stockés
    stored_angles = read_stored_angles(group)
    joint_limits  = read_joint_limits(group)

    # 3. Capture des poses de repos UNE SEULE FOIS
    T0_rest = {}
    for i in range(NB_JOINTS):
        rest_str = rs.GetUserText(group[i], KEY_REST_XFORM)
        xf = str_to_xform(rest_str) if rest_str else None
        if xf is None:
            xf = get_instance_xform(group[i])
            if xf is None:
                rs.MessageBox(
                    "Transformée illisible pour le segment {}.".format(i),
                    0, "Erreur")
                return
            rs.SetUserText(group[i], KEY_REST_XFORM, xform_to_str(xf))
        T0_rest[i] = xf

    # 3b. Capture de l'état courant avant édition (pour restauration en cas d'annulation)
    T0_before = {}
    for i in range(NB_JOINTS):
        xf = get_instance_xform(group[i])
        if xf is None:
            rs.MessageBox(
                "Transformée courante illisible pour le segment {}.".format(i),
                0, "Erreur")
            return
        T0_before[i] = xf

    angles_before = list(stored_angles.get(i, 0.0) for i in range(NB_JOINTS))

    # 4. Formulaire Eto
    dlg = RobotPoseDialog(
        group, stored_angles, joint_limits,
        T0_rest, robot_name, instance_index)

    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

    # 5. Résultat après fermeture
    if dlg.validated:
        rs.EnableRedraw(False)
        ok = compute_and_apply(
            group, dlg.angles, T0_rest, robot_name, instance_index)
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

        if ok:
            rs.UnselectAllObjects()
            # Sélection : joints + instances Pose de même KEY_LEVEL0
            target_lv0 = "{}#{}".format(robot_name, instance_index)
            all_selected = list(group.values())
            all_objs = rs.AllObjects()
            if all_objs:
                for obj in all_objs:
                    if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
                        if rs.GetUserText(obj, KEY_LEVEL0) == target_lv0:
                            all_selected.append(obj)
            rs.SelectObjects(all_selected)
            print("Robot '{}#{}' positionné. Angles : {}".format(
                robot_name, instance_index,
                [round(a, 1) for a in dlg.angles]))
    else:
        # Annulation : restaurer la position ET les angles avant édition
        rs.EnableRedraw(False)
        for i in range(NB_JOINTS):
            obj_id = group[i]
            xf_cur = get_instance_xform(obj_id)
            if xf_cur is not None:
                inv_cur = try_invert(xf_cur)
                if inv_cur is not None:
                    reset = mul(T0_before[i], inv_cur)
                    rs.TransformObject(obj_id, xform_to_list(reset))
            # Restauration des UserTexts d'angle
            rs.SetUserText(obj_id, KEY_ANGLE, str(angles_before[i]))
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Annulé – état avant édition restauré.")


if __name__ == "__main__":
    main()
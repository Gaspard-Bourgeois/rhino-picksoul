"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 08/01/26
"""
import rhinoscriptsyntax as rs
import re

def get_program_from_selection(selected_ids):
    """Retrouve les programmes liés aux éléments sélectionnés"""
    target_layers = set()
    for s_id in selected_ids:
        lyr = rs.ObjectLayer(s_id)
        if lyr:
            target_layers.add(lyr)
            parent = rs.ParentLayer(lyr)
            if parent: target_layers.add(parent)
    
    all_objs = rs.ObjectsByType(4096) # Instances de blocs
    programs = []
    if all_objs:
        for obj in all_objs:
            if rs.GetUserText(obj, "type") == "program":
                if rs.ObjectLayer(obj) in target_layers:
                    programs.append(obj)
    return list(set(programs))


def select_next_program_element():
    # Récupérer les objets actuellement sélectionnés
    selected = rs.GetObjects("Sélectionnez les éléments actuels", preselect=True)
    
    if not selected:
        print("Aucune sélection active.")
        return

    next_objects_to_select = []
    
    # On désélectionne tout pour préparer la nouvelle sélection
    rs.UnselectAllObjects()
    
    curve_selected = set()
    pose_selected = set()
    for obj_id in selected:
        obj_type = rs.ObjectType(obj_id)
        if obj_type == rs.filter.instance and rs.BlockInstanceName(obj_id) == "Pose":
            pose_selected.add(str(obj_id))
        else:
            curve_selected.add(str(obj_id))
    
    print(pose_selected, curve_selected)
    
    print("Analyse de la selection utilisateur ({} objets)...".format(len(selected)))
    target_programs = get_program_from_selection(selected)
    if not target_programs:
        print("ERREUR: Aucun programme associe a la selection.")
        return
    
    next_curves = []
    next_poses = []
    for prog_id in target_programs:
        prog_layer = rs.ObjectLayer(prog_id)
        print("\n>>> TRAITEMENT PROGRAMME: {}".format(prog_layer))
    
        # --- Identification des courbes via UserStrings ---
        original_crv_uuids = []
        select_next_curve = False
        i = 0
        while True:
            # Attention: Utilisation stricte du formatage Crv_0000
            key = "Crv_{:04d}".format(i)
            u = rs.GetUserText(prog_id, key)
            if not u: break
            if rs.IsObject(u):
                original_crv_uuids.append(u)
            else:
                print("DEBUG: Courbe referencee {} introuvable (supprimee?).".format(u))
            if select_next_curve:
                select_next_curve = False
                next_curves.append(u)
                curve_selected.remove(u)
            if u in curve_selected:
                select_next_curve = True
            if  not len(pose_selected) and not len(curve_selected) and not select_next_curve:
                return
            i += 1
        

        # --- Identification des poses via UserStrings ---
        last_pose = None
        select_next_pose = False
        for curve_uuid in original_crv_uuids:
            p_idx = 0
            while True:
                orig_pose_uuid = rs.GetUserText(curve_uuid, "UUID_{:04d}".format(p_idx))
                if not orig_pose_uuid: break                   
                p_idx += 1
                if orig_pose_uuid == last_pose:
                    continue
                last_pose = orig_pose_uuid
                print(orig_pose_uuid)
                if select_next_pose:
                    select_next_pose = False
                    next_poses.append(orig_pose_uuid)
                if orig_pose_uuid in pose_selected:
                    select_next_pose = True
                    pose_selected.remove(orig_pose_uuid)
                if  not len(pose_selected) and not len(curve_selected) and not select_next_pose:
                    break
    next_objects_to_select = next_curves + next_poses
    
    if next_objects_to_select:
        rs.SelectObjects(next_objects_to_select)
        print("{} éléments suivants sélectionnés.".format(len(next_objects_to_select)))
    else:
        print("Aucun élément suivant trouvé.")

if __name__ == "__main__":
    select_next_program_element()

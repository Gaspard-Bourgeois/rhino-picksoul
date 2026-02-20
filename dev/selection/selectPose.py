# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def filter_or_select_pose_instances():
    # 1. Récupérer la sélection actuelle
    selected_ids = rs.SelectedObjects()
    
    pose_instances = []
    
    if selected_ids:
        # MODE FILTRE : On cherche les blocs "Pose" parmi la sélection
        for obj_id in selected_ids:
            if rs.IsBlockInstance(obj_id):
                if rs.BlockInstanceName(obj_id) == "Pose":
                    pose_instances.append(obj_id)
        
        if pose_instances:
            rs.UnselectAllObjects()
            rs.SelectObjects(pose_instances)
            print("{} instance(s) de 'Pose' filtrée(s) dans la sélection.".format(len(pose_instances)))
        else:
            print("Aucune instance de 'Pose' dans la sélection actuelle.")
            rs.UnselectAllObjects()
            
    else:
        # MODE GLOBAL : Rien n'est sélectionné, on cherche dans tout le document
        all_objs = rs.AllObjects()
        for obj_id in all_objs:
            if rs.IsBlockInstance(obj_id):
                if rs.BlockInstanceName(obj_id) == "Pose":
                    pose_instances.append(obj_id)
        
        if pose_instances:
            rs.SelectObjects(pose_instances)
            print("{} instance(s) de 'Pose' sélectionnée(s) globalement.".format(len(pose_instances)))
        else:
            print("Aucune instance du bloc 'Pose' n'existe dans le document.")

if __name__ == "__main__":
    filter_or_select_pose_instances()

# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import System.Drawing
import re

def get_block_definition(block_name):
    if not rs.IsBlock(block_name):
        pt = rs.AddPoint([0,0,0])
        rs.AddBlock([pt], [0,0,0], block_name, delete_input=True)
    return block_name

def update_pose_geometry(block_name, viz_type, size):
    new_objs = []
    origin = [0,0,0]
    
    if viz_type == "frame":
        line_x = rs.AddLine(origin, [size, 0, 0])
        rs.ObjectColor(line_x, System.Drawing.Color.Red)
        line_y = rs.AddLine(origin, [0, size, 0])
        rs.ObjectColor(line_y, System.Drawing.Color.Lime) 
        line_z = rs.AddLine(origin, [0, 0, size])
        rs.ObjectColor(line_z, System.Drawing.Color.Blue)
        new_objs = [line_x, line_y, line_z]
    else: # point
        pt = rs.AddPoint(origin)
        rs.ObjectColor(pt, System.Drawing.Color.Red)
        new_objs = [pt]
        
    # Redéfinition du bloc (écrase l'ancienne définition)
    rs.AddBlock(new_objs, [0,0,0], block_name, delete_input=True)

def reset_instances_scale(block_name):
    instances = rs.BlockInstances(block_name)
    if not instances: return 0
    
    count = 0
    for inst in instances:
        # Récupérer la matrice actuelle
        xform = rs.BlockInstanceXform(inst)
        
        # Extraire les vecteurs colonnes (axes locaux)
        vX = rg.Vector3d(xform.M00, xform.M10, xform.M20)
        vY = rg.Vector3d(xform.M01, xform.M11, xform.M21)
        vZ = rg.Vector3d(xform.M02, xform.M12, xform.M22)
        
        # Calculer les facteurs d'échelle actuels
        sX = vX.Length
        sY = vY.Length
        sZ = vZ.Length
        
        # Si l'échelle n'est pas de 1 (avec une petite tolérance)
        if abs(sX-1.0) > 1e-6 or abs(sY-1.0) > 1e-6 or abs(sZ-1.0) > 1e-6:
            # Créer une matrice de compensation d'échelle inverse
            # On scale par 1/s autour du point d'insertion
            plane = rs.WorldXYPlane()
            pivot = rs.BlockInstanceInsertPoint(inst)
            plane = rs.MovePlane(plane, pivot)
            scaling_matrix = rg.Transform.Scale(plane, 1.0/sX, 1.0/sY, 1.0/sZ)
            
            # Appliquer la transformation à l'objet
            rs.TransformObject(inst, scaling_matrix)
            count += 1
    return count

def main():
    block_name = "Pose"
    
    # --- 1. VALEURS PAR DÉFAUT ---
    p_type = "frame"
    p_size = 25
    p_reset = "Off"
    
    # --- 2. HISTORIQUE ---
    structure_requete = "Pose_Config: Type=%s Size=%s ResetScale=%s"
    pattern = "Pose_Config: Type=(\S+) Size=(\S+) ResetScale=(\S+)"
    
    cmd_hist = rs.CommandHistory().split('\n')
    cmd_hist.reverse()
    for line in cmd_hist:
        match = re.search(pattern, line)
        if match:
            p_type = match.group(1)
            p_size = int(match.group(2))
            p_reset = match.group(3)
            break

    # --- 3. BOUCLE D'OPTIONS ---
    while True:
        # On définit les options SANS le signe "=" pour garantir la sélection
        options = ["Type", "Size", "ResetScale"]
        
        # On construit un message clair avec les valeurs actuelles
        prompt = "Paramètres Pose [ Type=%s  Size=%d  ResetScale=%s ]" % (p_type, p_size, p_reset)
        
        res = rs.GetString(prompt, "Valider", options)
        
        if res is None: return # Annulation
        
        if res == "Valider" or res == "": 
            break
            
        elif res == "Type":
            p_type = "point" if p_type == "frame" else "frame"
            
        elif res == "Size":
            new_val = rs.GetInteger("Nouvelle taille (0-100)", p_size, 0, 100)
            if new_val is not None: p_size = new_val
            
        elif res == "ResetScale":
            p_reset = "On" if p_reset == "Off" else "Off"

    # --- 4. EXÉCUTION ---
    rs.EnableRedraw(False)
    
    get_block_definition(block_name)
    update_pose_geometry(block_name, p_type, p_size)
    
    if p_reset == "On":
        num = reset_instances_scale(block_name)
        print("%d instances corrigées." % num)
    
    # Print final pour l'historique
    print(structure_requete % (p_type, p_size, p_reset))
    
    rs.EnableRedraw(True)

if __name__ == "__main__":
    main()

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
    else:
        pt = rs.AddPoint(origin)
        rs.ObjectColor(pt, System.Drawing.Color.Red)
        new_objs = [pt]
    rs.AddBlock(new_objs, [0,0,0], block_name, delete_input=True)

def reset_instances_scale(block_name):
    instances = rs.BlockInstances(block_name)
    if not instances: return 0
    
    count = 0
    tol = 1e-8 # Tolérance serrée pour la comparaison
    
    for inst in instances:
        m_old = rs.BlockInstanceXform(inst)
        
        # --- Reconstruction de la cible (Orthonormée) ---
        vX = rg.Vector3d(m_old.M00, m_old.M10, m_old.M20)
        vY = rg.Vector3d(m_old.M01, m_old.M11, m_old.M21)
        
        vX.Unitize()
        vZ = rg.Vector3d.CrossProduct(vX, vY)
        vZ.Unitize()
        vY = rg.Vector3d.CrossProduct(vZ, vX)
        vY.Unitize()
        
        m_new = rg.Transform(1.0)
        m_new.M00, m_new.M10, m_new.M20 = vX.X, vX.Y, vX.Z
        m_new.M01, m_new.M11, m_new.M21 = vY.X, vY.Y, vY.Z
        m_new.M02, m_new.M12, m_new.M22 = vZ.X, vZ.Y, vZ.Z
        m_new.M03, m_new.M13, m_new.M23 = m_old.M03, m_old.M13, m_old.M23
        
        # --- Test de différence avant action API ---
        # On compare les composantes clés des matrices
        is_different = False
        for i in range(3):
            for j in range(3): # On ne teste que la rotation/échelle (3x3)
                if abs(m_new[i,j] - m_old[i,j]) > tol:
                    is_different = True
                    break
            if is_different: break
            
        if is_different:
            rc, m_old_inv = m_old.TryGetInverse()
            if rc:
                m_comp = m_new * m_old_inv
                rs.TransformObject(inst, m_comp)
                count += 1
    return count

def main():
    block_name = "Pose"
    p_type, p_size, p_reset = "frame", 25, "Off"
    
    # Historique
    structure_requete = "Pose_Config: Type=%s Size=%s ResetScale=%s"
    pattern = "Pose_Config: Type=(\S+) Size=(\S+) ResetScale=(\S+)"
    cmd_hist = rs.CommandHistory().split('\n')
    for line in reversed(cmd_hist):
        match = re.search(pattern, line)
        if match:
            p_type, p_size, p_reset = match.group(1), int(match.group(2)), match.group(3)
            break

    # Menu
    while True:
        res = rs.GetString("Paramètres Pose [ Type=%s  Size=%d  ResetScale=%s ]" % (p_type, p_size, p_reset), "Valider", ["Type", "Size", "ResetScale"])
        if res is None: return
        if res == "Valider" or res == "": break
        elif res == "Type": p_type = "point" if p_type == "frame" else "frame"
        elif res == "Size":
            new_val = rs.GetInteger("Taille", p_size, 0, 100)
            if new_val is not None: p_size = new_val
        elif res == "ResetScale": p_reset = "On" if p_reset == "Off" else "Off"

    rs.EnableRedraw(False)
    get_block_definition(block_name)
    update_pose_geometry(block_name, p_type, p_size)
    if p_reset == "On":
        num = reset_instances_scale(block_name)
        if num > 0: print("%d instances corrigées." % num)
    
    print(structure_requete % (p_type, p_size, p_reset))
    rs.EnableRedraw(True)

if __name__ == "__main__":
    main()

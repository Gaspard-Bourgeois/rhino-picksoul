# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import System.Drawing
import re

def get_block_definition(block_name):
    if not rs.IsBlock(block_name):
        # Création d'un point temporaire pour définir le bloc s'il n'existe pas
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
        
    # Redéfinition du bloc (écrase l'ancienne définition géométrique)
    rs.AddBlock(new_objs, [0,0,0], block_name, delete_input=True)

def reset_instances_scale(block_name):
    """
    Réinitialise l'échelle et supprime le cisaillement des instances.
    Calcule la matrice de compensation : M_correction = M_cible * inverse(M_actuelle)
    """
    instances = rs.BlockInstances(block_name)
    if not instances: return 0
    
    count = 0
    for inst in instances:
        # 1. Obtenir la matrice de transformation actuelle (M_old)
        m_old = rs.BlockInstanceXform(inst)
        
        # 2. Extraire les vecteurs colonnes actuels
        vX = rg.Vector3d(m_old.M00, m_old.M10, m_old.M20)
        vY = rg.Vector3d(m_old.M01, m_old.M11, m_old.M21)
        
        # 3. Construire une base orthonormée (sans échelle ni cisaillement)
        # On garde la direction X comme référence
        vX.Unitize()
        # On calcule Z par produit vectoriel pour garantir la perpendicularité
        vZ = rg.Vector3d.CrossProduct(vX, vY)
        vZ.Unitize()
        # On recalcule Y pour fermer la base orthonormée
        vY = rg.Vector3d.CrossProduct(vZ, vX)
        vY.Unitize()
        
        # 4. Créer la matrice cible (M_new) : Rotation pure + Translation d'origine
        m_new = rg.Transform(1.0)
        m_new.M00, m_new.M10, m_new.M20 = vX.X, vX.Y, vX.Z
        m_new.M01, m_new.M11, m_new.M21 = vY.X, vY.Y, vY.Z
        m_new.M02, m_new.M12, m_new.M22 = vZ.X, vZ.Y, vZ.Z
        # On préserve la position (4ème colonne)
        m_new.M03, m_new.M13, m_new.M23 = m_old.M03, m_old.M13, m_old.M23
        
        # 5. Calculer la transformation de compensation
        # Mathématiquement : M_new = M_comp * M_old  =>  M_comp = M_new * inverse(M_old)
        rc, m_old_inv = m_old.TryGetInverse()
        
        if rc:
            m_comp = m_new * m_old_inv
            # On vérifie si une correction est réellement nécessaire (différence de matrice)
            if not m_comp.IsIdentity:
                rs.TransformObject(inst, m_comp)
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
            try:
                p_type = match.group(1)
                p_size = int(match.group(2))
                p_reset = match.group(3)
                break
            except: pass

    # --- 3. BOUCLE D'OPTIONS ---
    while True:
        options = ["Type", "Size", "ResetScale"]
        prompt = "Paramètres Pose [ Type=%s  Size=%d  ResetScale=%s ]" % (p_type, p_size, p_reset)
        res = rs.GetString(prompt, "Valider", options)
        
        if res is None: return 
        if res == "Valider" or res == "": break
            
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
        if num > 0:
            print("%d instances corrigées (Echelle & Cisaillement)." % num)
    
    print(structure_requete % (p_type, p_size, p_reset))
    rs.EnableRedraw(True)

if __name__ == "__main__":
    main()

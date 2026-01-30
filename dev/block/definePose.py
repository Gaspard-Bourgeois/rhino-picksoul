# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import System.Drawing
import re
import math

def get_block_definition(block_name):
    """Vérifie si le bloc existe, sinon le crée."""
    if not rs.IsBlock(block_name):
        # Création d'un bloc vide temporaire si inexistant
        pt = rs.AddPoint([0,0,0])
        rs.AddBlock([pt], [0,0,0], block_name, delete_input=True)
    return block_name

def update_pose_geometry(block_name, viz_type, size):
    """
    Redéfinit la géométrie interne du bloc 'Pose'.
    Type 'frame': Trièdre RGB.
    Type 'point': Point Rouge.
    """
    # 1. Nettoyer la géométrie existante du bloc
    block_objects = rs.BlockObjects(block_name)
    if block_objects:
        rs.DeleteObjects(block_objects)
    
    new_objs = []
    origin = [0,0,0]
    
    if viz_type == "frame":
        # Création des lignes X, Y, Z
        # Axe X (Rouge)
        line_x = rs.AddLine(origin, [size, 0, 0])
        rs.ObjectColor(line_x, System.Drawing.Color.Red)
        
        # Axe Y (Vert)
        line_y = rs.AddLine(origin, [0, size, 0])
        rs.ObjectColor(line_y, System.Drawing.Color.Lime) # Lime est le vert standard pur
        
        # Axe Z (Bleu)
        line_z = rs.AddLine(origin, [0, 0, size])
        rs.ObjectColor(line_z, System.Drawing.Color.Blue)
        
        new_objs = [line_x, line_y, line_z]
        
    elif viz_type == "point":
        # Création d'un point rouge
        pt = rs.AddPoint(origin)
        rs.ObjectColor(pt, System.Drawing.Color.Red)
        new_objs = [pt]
        
    # 2. Ajouter les nouveaux objets au bloc
    rs.AddObjectsToBlock(new_objs, block_name, delete_input=True)
    print("Bloc '%s' mis à jour (Type: %s, Size: %s)." % (block_name, viz_type, size))

def reset_instances_scale(block_name):
    """
    Parcourt toutes les instances de 'Pose' et réinitialise leur scale à 1,1,1
    tout en conservant la rotation et la position.
    """
    instances = rs.BlockInstances(block_name)
    if not instances:
        return 0
        
    count = 0
    for inst in instances:
        # Récupération de la matrice de transformation actuelle (4x4)
        xform = rs.BlockInstanceXform(inst)
        
        # Extraction des vecteurs de base (colonnes de la matrice)
        # M00, M10, M20 correspond au vecteur X local transformé
        vx = rg.Vector3d(xform.M00, xform.M10, xform.M20)
        vy = rg.Vector3d(xform.M01, xform.M11, xform.M21)
        vz = rg.Vector3d(xform.M02, xform.M12, xform.M22)
        
        # Extraction de la translation (M03, M13, M23) - Point d'insertion
        trans = rg.Vector3d(xform.M03, xform.M13, xform.M23)
        
        # Normalisation des vecteurs (ceci remet l'échelle à 1 tout en gardant la direction/rotation)
        if vx.Length > 0: vx.Unitize()
        if vy.Length > 0: vy.Unitize()
        if vz.Length > 0: vz.Unitize()
        
        # Reconstruction de la matrice propre (Scale = 1)
        new_xform = rg.Transform(1.0) # Identité par défaut
        
        # Réassignation des axes
        new_xform.M00, new_xform.M10, new_xform.M20 = vx.X, vx.Y, vx.Z
        new_xform.M01, new_xform.M11, new_xform.M21 = vy.X, vy.Y, vy.Z
        new_xform.M02, new_xform.M12, new_xform.M22 = vz.X, vz.Y, vz.Z
        
        # Réassignation de la translation (pour ne pas bouger le point d'insertion)
        new_xform.M03, new_xform.M13, new_xform.M23 = trans.X, trans.Y, trans.Z
        
        # Application
        rs.BlockInstanceXform(inst, new_xform)
        count += 1
        
    return count

def main():
    block_name = "Pose"
    
    # -----------------------------------------------
    # 1. PARAMÈTRES PAR DÉFAUT
    # -----------------------------------------------
    p_type = "frame"
    p_size = 25
    p_reset = "Off"
    
    # Chaîne de format pour l'historique et l'affichage
    # Ex: Pose Config: Type=frame Size=25 Reset=Off
    structure_requete = r"Pose Config: Type=%s Size=%s Reset=%s. Entrée pour valider."
    
    # -----------------------------------------------
    # 2. RECHERCHE DANS L'HISTORIQUE
    # -----------------------------------------------
    pattern = structure_requete.replace('.', '\.')
    pattern = pattern.replace('%s', '(\S+)')
    
    cmd_hist = rs.CommandHistory().split('\n')
    cmd_hist.reverse()
    
    for line in cmd_hist:
        match = re.search(pattern, line)
        if match:
            # Groupes trouvés : (Type, Size, Reset)
            found_vals = match.groups()
            p_type = found_vals[0]
            try:
                p_size = int(found_vals[1])
            except:
                p_size = 25
            p_reset = found_vals[2]
            break

    # -----------------------------------------------
    # 3. BOUCLE INTERACTIVE
    # -----------------------------------------------
    while True:
        # Construction des options
        opt_type = "Type=%s" % p_type
        opt_size = "Size=%d" % p_size
        opt_reset = "Reset_scale=%s" % p_reset
        
        options_list = [
            opt_type.split('=')[0],
            opt_size.split('=')[0],
            opt_reset.split('=')[0]
        ]
        
        msg = structure_requete % (p_type, str(p_size), p_reset)
        
        result = rs.GetString(msg, defaultString="", strings=options_list)
        
        if result is None:
            print("Annulé.")
            return
            
        if result == "":
            break # L'utilisateur a appuyé sur Entrée pour valider
            
        # Gestion des clics sur les options
        elif result == "Type":
            # Bascule frame <-> point
            if p_type == "frame": p_type = "point"
            else: p_type = "frame"
            
        elif result == "Size":
            new_size = rs.GetInteger("Taille du repère (0-100)", p_size, 0, 100)
            if new_size is not None:
                p_size = new_size
                
        elif result == "Reset_scale":
            # Bascule On <-> Off
            if p_reset == "Off": p_reset = "On"
            else: p_reset = "Off"

    # -----------------------------------------------
    # 4. EXÉCUTION
    # -----------------------------------------------
    rs.EnableRedraw(False)
    
    # Vérification / Création du bloc
    get_block_definition(block_name)
    
    # Mise à jour géométrie
    update_pose_geometry(block_name, p_type, p_size)
    
    # Mise à jour échelle si demandé
    if p_reset == "On":
        count = reset_instances_scale(block_name)
        print("Echelle réinitialisée pour %d instance(s) de Pose." % count)
    
    rs.EnableRedraw(True)
    
    # Impression finale pour l'historique (afin que le regex le retrouve la prochaine fois)
    print("--------------------------------------------------")
    print(structure_requete % (p_type, str(p_size), p_reset))
    print("Script terminé avec succès.")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
import System.Drawing
import re

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
    # 1. Nettoyer la géométrie existante du bloc (si nécessaire, via AddBlock delete_input=True le gère souvent, 
    # mais pour être propre on peut supprimer les anciens objets si on recree tout).
    # Ici, rs.AddBlock redéfinit le bloc s'il existe déjà avec le même nom.
    
    new_objs = []
    origin = [0,0,0]
    
    if viz_type == "frame":
        # Création des lignes X, Y, Z
        # Axe X (Rouge)
        line_x = rs.AddLine(origin, [size, 0, 0])
        rs.ObjectColor(line_x, System.Drawing.Color.Red)
        
        # Axe Y (Vert)
        line_y = rs.AddLine(origin, [0, size, 0])
        rs.ObjectColor(line_y, System.Drawing.Color.Lime) 
        
        # Axe Z (Bleu)
        line_z = rs.AddLine(origin, [0, 0, size])
        rs.ObjectColor(line_z, System.Drawing.Color.Blue)
        
        new_objs = [line_x, line_y, line_z]
        
    elif viz_type == "point":
        # Création d'un point rouge
        pt = rs.AddPoint(origin)
        rs.ObjectColor(pt, System.Drawing.Color.Red)
        new_objs = [pt]
        
    # 2. Redéfinir le bloc
    rs.AddBlock(new_objs, [0,0,0], block_name, delete_input=True)
    print("Bloc '%s' mis à jour (Type: %s, Size: %s)." % (block_name, viz_type, size))

def reset_instances_scale(block_name):
    """
    Parcourt toutes les instances de 'Pose' et réinitialise leur scale à 1,1,1
    tout en conservant la rotation et la position.
    Utilise RhinoCommon pour modifier la transformation directement.
    """
    instances = rs.BlockInstances(block_name)
    if not instances:
        return 0
        
    count = 0
    for inst_guid in instances:
        # Récupération de l'objet Rhino via RhinoCommon
        rhino_obj = sc.doc.Objects.FindId(inst_guid)
        if rhino_obj is None:
            continue
            
        # On travaille sur la géométrie de référence (InstanceReferenceGeometry)
        iref_geo = rhino_obj.Geometry
        xform = iref_geo.Xform # Matrice actuelle
        
        # Extraction des vecteurs de base (colonnes de la matrice)
        vx = rg.Vector3d(xform.M00, xform.M10, xform.M20)
        vy = rg.Vector3d(xform.M01, xform.M11, xform.M21)
        vz = rg.Vector3d(xform.M02, xform.M12, xform.M22)
        trans = rg.Vector3d(xform.M03, xform.M13, xform.M23)
        
        # Normalisation des vecteurs (Scale = 1)
        if vx.Length > 0: vx.Unitize()
        if vy.Length > 0: vy.Unitize()
        if vz.Length > 0: vz.Unitize()
        
        # Reconstruction de la matrice propre
        new_xform = rg.Transform(1.0)
        new_xform.M00, new_xform.M10, new_xform.M20 = vx.X, vx.Y, vx.Z
        new_xform.M01, new_xform.M11, new_xform.M21 = vy.X, vy.Y, vy.Z
        new_xform.M02, new_xform.M12, new_xform.M22 = vz.X, vz.Y, vz.Z
        new_xform.M03, new_xform.M13, new_xform.M23 = trans.X, trans.Y, trans.Z
        
        # APPLICATION via RhinoCommon (Setter)
        iref_geo.Xform = new_xform
        rhino_obj.CommitChanges()
        
        count += 1
        
    return count

def main():
    block_name = "Pose"
    
    # 1. PARAMÈTRES PAR DÉFAUT
    p_type = "frame"
    p_size = 25
    p_reset = "Off"
    
    structure_requete = r"Pose Config: Type=%s Size=%s Reset=%s. Entrée pour valider."
    
    # 2. RECHERCHE DANS L'HISTORIQUE
    pattern = structure_requete.replace('.', '\.')
    pattern = pattern.replace('%s', '(\S+)')
    
    cmd_hist = rs.CommandHistory().split('\n')
    cmd_hist.reverse()
    
    for line in cmd_hist:
        match = re.search(pattern, line)
        if match:
            found_vals = match.groups()
            p_type = found_vals[0]
            try: p_size = int(found_vals[1])
            except: p_size = 25
            p_reset = found_vals[2]
            break

    # 3. BOUCLE INTERACTIVE
    while True:
        # Construction des chaînes complètes pour l'affichage ET la sélection
        opt_type_str = "Type=%s" % p_type
        opt_size_str = "Size=%d" % p_size
        opt_reset_str = "Reset_scale=%s" % p_reset
        
        # Liste des options cliquables (affiche "Type=frame", "Size=25", etc.)
        options_list = [opt_type_str, opt_size_str, opt_reset_str]
        
        msg = structure_requete % (p_type, str(p_size), p_reset)
        
        # rs.GetString renvoie la chaîne exacte cliquée ou tapée
        result = rs.GetString(msg, defaultString="", strings=options_list)
        
        if result is None:
            print("Annulé.")
            return
            
        if result == "":
            break 
            
        # Comparaison directe avec les chaînes générées
        if result == opt_type_str:
            if p_type == "frame": p_type = "point"
            else: p_type = "frame"
            
        elif result == opt_size_str:
            new_size = rs.GetInteger("Taille du repère (0-100)", p_size, 0, 100)
            if new_size is not None:
                p_size = new_size
                
        elif result == opt_reset_str:
            if p_reset == "Off": p_reset = "On"
            else: p_reset = "Off"

    # 4. EXÉCUTION
    rs.EnableRedraw(False)
    
    get_block_definition(block_name)
    update_pose_geometry(block_name, p_type, p_size)
    
    if p_reset == "On":
        count = reset_instances_scale(block_name)
        if count > 0:
            print("Echelle réinitialisée pour %d instance(s)." % count)
    
    rs.EnableRedraw(True)
    
    print("--------------------------------------------------")
    print(structure_requete % (p_type, str(p_size), p_reset))
    print("Script terminé.")

if __name__ == "__main__":
    main()

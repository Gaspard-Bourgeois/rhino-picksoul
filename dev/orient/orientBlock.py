"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 05/01/26
"""
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math
import re

def get_block_axes(block_id):
    """
    Extrait les axes locaux X, Y, Z (en tant que vecteurs World) d'une instance de bloc.
    :param block_id: GUID de l'instance de bloc.
    :return: Tuple (x_axis, y_axis, z_axis) ou (None, None, None) si erreur.
    """
    xform_current = rs.BlockInstanceXform(block_id)
    if xform_current is None:
        return None, None, None
        
    # Les axes sont les vecteurs de base de la matrice de transformation.
    # M00, M10, M20 est l'axe X (colonne 0)
    x_axis = rg.Vector3d(xform_current.M00, xform_current.M10, xform_current.M20)
    # M01, M11, M21 est l'axe Y (colonne 1)
    y_axis = rg.Vector3d(xform_current.M01, xform_current.M11, xform_current.M21)
    # M02, M12, M22 est l'axe Z (colonne 2)
    z_axis = rg.Vector3d(xform_current.M02, xform_current.M12, xform_current.M22)
    
    return x_axis, y_axis, z_axis




def transform_blocks_with_interactive_options():
    """
    Définit les paramètres de transformation (Translation et Euler) et l'applique.
    La rotation en mode 'Block' utilise les axes locaux de chaque bloc.
    """
    
    
    block_ids = rs.GetObjects("Sélectionnez les blocs d'objets à transformer", filter=4096, preselect=True)
    
    if not block_ids:
        print("Aucun bloc sélectionné. Transformation annulée.")
        return
    
    # -----------------------------------------------
    # 1. VALEURS PAR DÉFAUT et RENOMMAGE
    # -----------------------------------------------
    tx = 10.0
    ty = 0.0
    tz = 0.0
    rz_deg = 45.0 # Rz (Rotation Z, anciennement Yaw)
    ry_deg = 0.0 # Ry (Rotation Y, anciennement Pitch)
    rx_deg = 0.0 # Rx (Rotation X, anciennement Roll)
    
    coordinate_system = "World" 


    structure_requete = r"Repère: %s. Paramètres: %s %s %s | Rotations (Deg): %s %s %s. Ou utilisez {SetAll}. Entrée pour sélectionner."
    
    # -----------------------------------------------
    # 2. Recherche valeurs dans l'historique
    # -----------------------------------------------

    #Repère: World. Paramètres: Tx=10.00 Ty=0.00 Tz=0.00 | Rotations (Deg): Rz=45.00 Ry=0.00 Rx=0.00. Ou utilisez {SetAll}. Entrée pour sélectionner. ( Repere  Tx  Ty  Tz  Rz  Ry  Rx  SetAll )

    pattern = structure_requete
    pattern = pattern.replace('(', '\(')
    pattern = pattern.replace(')', '\)')
    pattern = pattern.replace('{', '\{')
    pattern = pattern.replace('}', '\}')
    pattern = pattern.replace('|', "\|")
    pattern = pattern.replace('%s', '(\S+)')
    # print(pattern)

    commandHistory = rs.CommandHistory()    
    commandHistory = commandHistory.split('\n')
    commandHistory.reverse()

    for command in commandHistory:
        result = re.search(pattern, command)
        # print(result)
        if result:
            value = result.groups() # tuple converted to list
            opt_flt = [v.split('=')[1] for v in value[1:]]
            coordinate_system = str(value[0])
            tx = float(opt_flt[0])
            ty = float(opt_flt[1])
            tz = float(opt_flt[2])
            rx_deg = float(opt_flt[3])
            ry_deg = float(opt_flt[4])
            rz_deg = float(opt_flt[5])
            break

    
    # -----------------------------------------------
    # 2. BOUCLE DE SAISIE DES PARAMÈTRES
    # -----------------------------------------------
    
    while True:
        
        # --- Construire les options affichées et cliquables ---
        opt_repere = "Repere=%s" % coordinate_system
        opt_tx = "Tx=%.2f" % tx
        opt_ty = "Ty=%.2f" % ty
        opt_tz = "Tz=%.2f" % tz
        # Utilisation des nouveaux noms
        opt_rx = "Rx=%.2f" % rx_deg 
        opt_ry = "Ry=%.2f" % ry_deg
        opt_rz = "Rz=%.2f" % rz_deg
        opt_set_all = "SetAll"
        
        options_list = [
            opt_repere.split('=')[0], # Repere en premier
            opt_tx.split('=')[0], 
            opt_ty.split('=')[0], 
            opt_tz.split('=')[0], 
            opt_rz.split('=')[0], 
            opt_ry.split('=')[0], 
            opt_rx.split('=')[0],
            opt_set_all
        ]
        
        message = structure_requete % (
            coordinate_system, opt_tx, opt_ty, opt_tz, opt_rz, opt_ry, opt_rx
        )
        
        command_result = rs.GetString(
            message, 
            defaultString="", 
            strings=options_list
        )
        
        if command_result is None:
            print("Script annulé.")
            return


        if command_result == "":
            break 
            
        else:
            option_name = command_result
            
            # --- Logique Repere ---
            if option_name == "Repere":
                new_cs = rs.GetString("Choisissez le repère de travail (World, CPlane, Block)", coordinate_system, ["World", "CPlane", "Block"])
                if new_cs is not None:
                    coordinate_system = new_cs
                    print("Repère de travail défini sur %s." % coordinate_system)
                        
            # --- Logique SetAll (Parsing de X, Y, Z, Rz, Ry, Rx) ---
            elif option_name == "SetAll":
                # Mise à jour de la chaîne par défaut pour refléter Rz, Ry, Rx
                default_string = "%.2f, %.2f, %.2f, %.2f, %.2f, %.2f" % (tx, ty, tz, rz_deg, ry_deg, rx_deg)
                input_str = rs.GetString("Entrez (X, Y, Z, Rz, Ry, Rx) séparés par des virgules", defaultString=default_string)
                
                if input_str is not None:
                    try:
                        values = [float(s.strip()) for s in input_str.split(',')]
                        
                        if len(values) == 6:
                            # Assigner dans l'ordre de la saisie (X, Y, Z, Rz, Ry, Rx)
                            tx, ty, tz, rz_deg, ry_deg, rx_deg = values
                            print("Nouvelles valeurs appliquées.")
                        else:
                            print("Erreur de parsing: 6 valeurs attendues, %d trouvées." % len(values))
                    except ValueError:
                        print("Erreur de format: Les valeurs doivent être des nombres.")
                        
            # --- Logique pour les options individuelles ---
            elif option_name == "Tx":
                new_tx = rs.GetReal("Nouvelle valeur de Translation X", tx)
                if new_tx is not None: tx = new_tx
            elif option_name == "Ty":
                new_ty = rs.GetReal("Nouvelle valeur de Translation Y", ty)
                if new_ty is not None: ty = new_ty
            elif option_name == "Tz":
                new_tz = rs.GetReal("Nouvelle valeur de Translation Z", tz)
                if new_tz is not None: tz = new_tz
            elif option_name == "Rz": # Rotation Z (Yaw)
                new_rz = rs.GetReal("Nouvelle valeur de Rz (Rotation Z) en degrés", rz_deg)
                if new_rz is not None: rz_deg = new_rz
            elif option_name == "Ry": # Rotation Y (Pitch)
                new_ry = rs.GetReal("Nouvelle valeur de Ry (Rotation Y) en degrés", ry_deg)
                if new_ry is not None: ry_deg = new_ry
            elif option_name == "Rx": # Rotation X (Roll)
                new_rx = rs.GetReal("Nouvelle valeur de Rx (Rotation X) en degrés", rx_deg)
                if new_rx is not None: rx_deg = new_rx


    # -----------------------------------------------
    # 3. SÉLECTION ET APPLICATION
    # -----------------------------------------------
    


    # Conversions
    rz = math.radians(rz_deg)
    ry = math.radians(ry_deg)
    rx = math.radians(rx_deg)
    
    # 3.1. DÉFINITION DU REPERE ET DU VECTEUR DE TRANSLATION
    
    # Récupérer le plan de référence pour la translation
    base_plane = rg.Plane.WorldXY # Par défaut
    if coordinate_system == "CPlane":
        base_plane = rs.ViewCPlane()
    # Note: En mode "Block" pour la translation, on utilise le repère World pour une 
    # cohérence et simplicité par défaut, la rotation étant le point clé.


    # Calcul du vecteur de translation en coordonnées World
    if coordinate_system == "World":
        translation_vector_world = rg.Vector3d(tx, ty, tz)
    else: # CPlane ou Block (traité comme CPlane si différent de World)
        x_axis = base_plane.XAxis
        y_axis = base_plane.YAxis
        z_axis = base_plane.ZAxis
        
        # Le vecteur de translation est la somme des composantes multipliées par les axes du repère
        translation_vector_world = x_axis * tx + y_axis * ty + z_axis * tz
    
    xform_t_base = rg.Transform.Translation(translation_vector_world)
    
    rs.EnableRedraw(False) 
    count = 0
    
    # 3.2. APPLICATION DE LA TRANSFORMATION À CHAQUE BLOC
    for block_id in block_ids:
        
        insertion_point = rs.BlockInstanceInsertPoint(block_id)
        if insertion_point is None: continue
        
        # Définition des axes de rotation et du centre
        rotation_center = insertion_point
        
        if coordinate_system == "Block":
            # Repère Block: Utilise les axes locaux du bloc (CORRECTION)
            x_axis_r, y_axis_r, z_axis_r = get_block_axes(block_id)
            if x_axis_r is None: continue
            
        elif coordinate_system == "CPlane":
            # Repère CPlane: Utilise les axes du CPlane actuel
            cplane = rs.ViewCPlane()
            x_axis_r = cplane.XAxis
            y_axis_r = cplane.YAxis
            z_axis_r = cplane.ZAxis
            
        else: # World
            # Repère World: Utilise les axes du plan monde
            x_axis_r = rg.Vector3d.XAxis
            y_axis_r = rg.Vector3d.YAxis
            z_axis_r = rg.Vector3d.ZAxis
        
        # --- Création de la Matrice de Rotation Locale ---
        # Rotations autour du centre d'insertion (Rz, Ry, Rx)
        
        # Rz (Rotation Z)
        xform_rz = rg.Transform.Rotation(rz, z_axis_r, rotation_center)
        # Ry (Rotation Y)
        xform_ry = rg.Transform.Rotation(ry, y_axis_r, rotation_center)
        # Rx (Rotation X)
        xform_rx = rg.Transform.Rotation(rx, x_axis_r, rotation_center)
        
        # Composition R = Rx * Ry * Rz (Ordre d'application Z-Y-X)
        xform_r = xform_rx * xform_ry * xform_rz
        
        # Transformation finale: Translation * Rotation
        # T_final = R * T_base. Si T_base est d'abord, on translate la rotation.
        # Pour une transformation cohérente, on applique R sur le bloc, puis la Translation T.
        final_xform = xform_t_base * xform_r
        
        # Application de la transformation
        if rs.TransformObject(block_id, final_xform, copy=False):
            count += 1
            
    rs.EnableRedraw(True) 
    
    # Afficher les résultats
    print("------------------------------------------------------------------")
    print("Transformation terminée. Repère de travail: %s" % coordinate_system)
    print(" Translation (T) : X=%.2f, Y=%.2f, Z=%.2f" % (tx, ty, tz))
    print(" Rotation (deg): Rz=%.2f, Ry=%.2f, Rx=%.2f" % (rz_deg, ry_deg, rx_deg))
    print("Transformation appliquée à %d bloc(s) sélectionné(s)." % count)
    
if __name__ == "__main__":
    transform_blocks_with_interactive_options()


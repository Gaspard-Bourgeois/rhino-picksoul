# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc

def create_pose_block():
    """Crée le bloc 'Pose' (trièdre RVB) s'il n'existe pas."""
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        items = []
        items.append(rs.AddLine([0,0,0], [1,0,0]))
        rs.ObjectColor(items[-1], [255,0,0])
        items.append(rs.AddLine([0,0,0], [0,1,0]))
        rs.ObjectColor(items[-1], [0,255,0])
        items.append(rs.AddLine([0,0,0], [0,0,1]))
        rs.ObjectColor(items[-1], [0,0,255])
        rs.AddBlock(items, [0,0,0], "Pose", True)
        rs.EnableRedraw(True)
    return "Pose"

def get_next_instance_index(block_name):
    """Trouve l'indice Y unique pour un block_name donné dans le document."""
    max_index = 0
    all_objs = rs.AllObjects()
    for obj in all_objs:
        keys = rs.GetUserText(obj)
        if keys:
            for key in keys:
                if key.startswith("BlockNameLevel_"):
                    value = rs.GetUserText(obj, key)
                    if value and "#" in value:
                        try:
                            name_part, index_part = value.split("#")
                            if name_part == block_name:
                                idx = int(index_part)
                                if idx > max_index: max_index = idx
                        except: continue
    return max_index + 1

def get_current_hierarchy_info(obj_id):
    """Récupère le niveau d'imbrication (X) et l'historique des UserTexts."""
    keys = rs.GetUserText(obj_id)
    max_level = -1
    existing_data = {}
    if keys:
        for key in keys:
            if key.startswith("BlockNameLevel_"):
                try:
                    lvl = int(key.split("_")[-1])
                    if lvl > max_level: max_level = lvl
                    existing_data[key] = rs.GetUserText(obj_id, key)
                except: continue
    return max_level + 1, existing_data

def decompose_reciproque():
    # --- 1. CONFIGURATION DE L'OUTIL DE SÉLECTION ---
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez les blocs à décomposer")
    go.EnablePreSelect(True, True)
    go.EnablePostSelect(True)
    
    # --- 2. GESTION DES RÉGLAGES PERSISTANTS ---
    # On récupère le dictionnaire de réglages propre à ce script
    settings = sc.ad_settings("DecomposeReciproque")
    
    # On récupère la dernière valeur choisie (par défaut : False si c'est la première fois)
    blocs_to_current_layer = settings.GetBool("BlocsToCurrentLayer", False)
    
    # Création du bouton booléen dans l'invite de commande
    opt_toggle = Rhino.Input.Custom.OptionToggle(blocs_to_current_layer, "Non", "Oui")
    go.AddOptionToggle("BlocsToCurrentLayer", opt_toggle)
    
    object_ids = []
    
    # --- 3. BOUCLE DE SÉLECTION ET GESTION DE L'OPTION ---
    while True:
        res = go.GetMultiple(1, 0)
        
        # Si l'utilisateur clique sur l'option BlocsToCurrentLayer
        if res == Rhino.Input.GetResult.Option:
            blocs_to_current_layer = opt_toggle.CurrentValue
            # Sauvegarde immédiate du nouveau choix pour les prochains lancements
            settings.SetBool("BlocsToCurrentLayer", blocs_to_current_layer)
            continue
            
        # Si l'utilisateur a fini de sélectionner des objets (ou avait pré-sélectionné)
        elif res == Rhino.Input.GetResult.Object:
            object_ids = [obj.ObjectId for obj in go.Objects()]
            break
            
        # Si annulation (Échap)
        else:
            return

    if not object_ids: return

    all_results = []
    create_pose_block()
    rs.EnableRedraw(False)
    
    # Récupération de l'ID du calque actif
    current_layer = rs.CurrentLayer()
    
    # --- 4. TRAITEMENT DES OBJETS ---
    for obj_id in object_ids:
        
        # --- CAS 1 : INSTANCE DE BLOC ---
        if rs.IsBlockInstance(obj_id):
            block_name = rs.BlockInstanceName(obj_id)
            
            # SECURITE : On ne décompose JAMAIS le bloc "Pose"
            if block_name == "Pose":
                all_results.append(obj_id)
                continue

            block_xform = rs.BlockInstanceXform(obj_id)
            
            # Récupération hiérarchie et calcul de l'indice unique
            next_level, hierarchy_history = get_current_hierarchy_info(obj_id)
            instance_index = get_next_instance_index(block_name)
            
            # Explosion
            exploded_items = rs.ExplodeBlockInstance(obj_id)
            if not exploded_items: exploded_items = []
            
            # Création et ajout du bloc Pose (lui reste intact)
            pose_id = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(pose_id, block_xform)
            
            # Liste complète des nouveaux objets à marquer
            targets = list(exploded_items) + [pose_id]
            
            for item in targets:
                # -> APPLICATION DE L'OPTION CALQUE
                if blocs_to_current_layer:
                    rs.ObjectLayer(item, current_layer)

                # 1. On recopie l'historique parent
                for key, val in hierarchy_history.items():
                    rs.SetUserText(item, key, val)
                
                # 2. On ajoute le niveau actuel
                new_key = "BlockNameLevel_{}".format(next_level)
                new_value = "{}#{}".format(block_name, instance_index)
                rs.SetUserText(item, new_key, new_value)
            
            all_results.extend(targets)

        # --- CAS 2 : GÉOMÉTRIE SIMPLE ---
        else:
            all_results.append(obj_id)

    rs.UnselectAllObjects()
    if all_results:
        rs.SelectObjects(all_results)
    
    rs.EnableRedraw(True)
    print("Décomposition terminée : {} objets créés ou conservés.".format(len(all_results)))

if __name__ == "__main__":
    decompose_reciproque()

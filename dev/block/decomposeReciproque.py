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

def get_base_name(block_name):
    """
    Extrait le nom racine d'un bloc.
    Si le bloc se nomme 'toto#3', retourne 'toto'.
    Si le bloc se nomme 'toto',   retourne 'toto'.
    """
    if "#" in block_name:
        return block_name.split("#")[0]
    return block_name

def get_next_instance_index(base_name):
    """
    Trouve l'indice unique suivant pour un base_name donné dans le document.
    Parcourt tous les UserTexts BlockNameLevel_X et cherche les valeurs
    dont la partie racine (avant #) correspond à base_name.
    """
    max_index = 0
    all_objs = rs.AllObjects()
    if not all_objs:
        return 1
    for obj in all_objs:
        keys = rs.GetUserText(obj)
        if keys:
            for key in keys:
                if key.startswith("BlockNameLevel_"):
                    value = rs.GetUserText(obj, key)
                    if value and "#" in value:
                        try:
                            name_part, index_part = value.split("#", 1)
                            if name_part == base_name:
                                idx = int(index_part)
                                if idx > max_index:
                                    max_index = idx
                        except ValueError:
                            continue
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
                    if lvl > max_level:
                        max_level = lvl
                    existing_data[key] = rs.GetUserText(obj_id, key)
                except ValueError:
                    continue
    return max_level + 1, existing_data

def decompose_reciproque():
    # --- 1. CONFIGURATION DE L'OUTIL DE SÉLECTION ---
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez les blocs à décomposer")
    go.EnablePreSelect(True, True)
    go.EnablePostSelect(True)

    # --- 2. GESTION DES RÉGLAGES PERSISTANTS ---
    rhino_settings = Rhino.PlugIns.PlugIn.GetPluginSettings(Rhino.RhinoApp.CurrentRhinoId, False)
    script_settings = rhino_settings.AddChild("DecomposeReciproqueSettings")
    blocs_to_current_layer = script_settings.GetBool("BlocsToCurrentLayer", False)

    opt_toggle = Rhino.Input.Custom.OptionToggle(blocs_to_current_layer, "Non", "Oui")
    go.AddOptionToggle("BlocsToCurrentLayer", opt_toggle)

    object_ids = []

    # --- 3. BOUCLE DE SÉLECTION ET GESTION DE L'OPTION ---
    while True:
        res = go.GetMultiple(1, 0)

        if res == Rhino.Input.GetResult.Option:
            blocs_to_current_layer = opt_toggle.CurrentValue
            script_settings.SetBool("BlocsToCurrentLayer", blocs_to_current_layer)
            Rhino.PlugIns.PlugIn.SavePluginSettings(Rhino.RhinoApp.CurrentRhinoId)
            continue

        elif res == Rhino.Input.GetResult.Object:
            object_ids = [obj.ObjectId for obj in go.Objects()]
            break

        else:
            return

    if not object_ids:
        return

    all_results = []
    create_pose_block()
    rs.EnableRedraw(False)

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

            # Récupération hiérarchie
            next_level, hierarchy_history = get_current_hierarchy_info(obj_id)

            # --- CORRECTION CLEF ---
            # Cas particulier : si le bloc contient déjà un '#', on garde sa valeur telle quelle
            if "#" in block_name:
                new_value = block_name
            else:
                # Sinon, c'est un nom racine, on cherche l'indice suivant
                instance_index = get_next_instance_index(block_name)
                new_value = "{}#{}".format(block_name, instance_index)

            # Explosion
            exploded_items = rs.ExplodeBlockInstance(obj_id)
            if not exploded_items:
                exploded_items = []

            # Création et transformation du bloc Pose
            pose_id = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(pose_id, block_xform)

            targets = list(exploded_items) + [pose_id]

            for item in targets:
                if blocs_to_current_layer:
                    rs.ObjectLayer(item, current_layer)

                # Recopie de l'historique parent
                for key, val in hierarchy_history.items():
                    rs.SetUserText(item, key, val)

                # Ajout du niveau actuel avec la valeur normalisée ou conservée
                new_key = "BlockNameLevel_{}".format(next_level)
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

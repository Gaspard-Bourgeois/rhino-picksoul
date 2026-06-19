# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def get_bbox_center(obj_id):
    """Calcule le centre d'une BoundingBox pour l'origine manuelle."""
    bbox = rs.BoundingBox(obj_id)
    if not bbox: return [0,0,0]
    pt_min = bbox[0]
    pt_max = bbox[6]
    return [(pt_min[i] + pt_max[i]) / 2.0 for i in range(3)]

def get_indexed_name(base_name):
    """Génère un nom du type Nom#1, Nom#2 basé sur la disponibilité."""
    i = 1
    while rs.IsBlock("{}#{}".format(base_name, i)):
        i += 1
    return "{}#{}".format(base_name, i)

def ensure_pose_block():
    """S'assure que la définition du bloc 'Pose' existe."""
    if not rs.IsBlock("Pose"):
        rs.EnableRedraw(False)
        p1 = [0,0,0]
        l1 = rs.AddLine(p1, [1,0,0]); rs.ObjectColor(l1, [255,0,0])
        l2 = rs.AddLine(p1, [0,1,0]); rs.ObjectColor(l2, [0,255,0])
        l3 = rs.AddLine(p1, [0,0,1]); rs.ObjectColor(l3, [0,0,255])
        rs.AddBlock([l1, l2, l3], p1, "Pose", True)
        rs.EnableRedraw(True)
    return "Pose"

def get_hierarchy_map(obj_ids, virtual_overrides=None):
    """
    Construit la cartographie signature -> {level, objects, pose}.

    virtual_overrides: dict optionnel {obj_id: (level, signature)} permettant
    de simuler l'appartenance d'un objet à un niveau/signature SANS lire ni
    écrire de UserText réelle sur l'objet. Utilisé pour les objets orphelins
    en attente de confirmation (afin de rester réversible avec Ctrl+Z, qui
    n'a aucune prise sur une donnée gardée en mémoire Python).
    """
    if virtual_overrides is None:
        virtual_overrides = {}

    mapping = {}
    for obj in obj_ids:
        if not rs.IsObject(obj): continue

        if obj in virtual_overrides:
            max_lvl, signature = virtual_overrides[obj]
        else:
            keys = rs.GetUserText(obj)
            max_lvl = -1
            signature = "Root"
            if keys:
                for k in keys:
                    if k.startswith("BlockNameLevel_"):
                        try:
                            lvl = int(k.split("_")[-1])
                            if lvl > max_lvl:
                                max_lvl = lvl
                                signature = rs.GetUserText(obj, k)
                        except: continue

        if signature not in mapping:
            mapping[signature] = {"level": max_lvl, "objects": [], "pose": None}
        if rs.IsBlockInstance(obj) and rs.BlockInstanceName(obj) == "Pose":
            mapping[signature]["pose"] = obj
        else:
            mapping[signature]["objects"].append(obj)
    return mapping

def clean_name(signature):
    name = signature.split("#")[0] if "#" in signature else signature
    if name.lower().endswith("_base"): name = name[:-5]
    if len(name) > 3 and name[-3] == "_" and name[-2:].isdigit(): name = name[:-3]
    return name


def get_existing_level_signature_pairs(obj_ids):
    """
    Parcourt les objets et collecte tous les couples (level, signature complète)
    rencontrés dans les clés BlockNameLevel_X, ainsi que le mapping
    nom_affiche -> signature complète pour pouvoir fusionner exactement.

    Retourne une liste de tuples (level, clean_display_name, full_signature)
    dédupliquée et triée par level croissant puis nom.
    """
    pairs = {}  # (level, full_signature) -> clean_display_name
    for obj in obj_ids:
        if not rs.IsObject(obj): continue
        keys = rs.GetUserText(obj)
        if not keys: continue
        for k in keys:
            if k.startswith("BlockNameLevel_"):
                try:
                    lvl = int(k.split("_")[-1])
                except:
                    continue
                sig = rs.GetUserText(obj, k)
                if not sig: continue
                pairs[(lvl, sig)] = clean_name(sig)

    result = [(lvl, disp, sig) for (lvl, sig), disp in pairs.items()]
    result.sort(key=lambda t: (t[0], t[1]))
    return result


def _pick_new_orphan_name(existing_triplets):
    """
    Demande un nouveau nom de bloc (niveau 0 par défaut, signature indexée
    pour éviter toute collision). Retourne (level, signature) ou (None, None)
    si annulé.
    """
    new_name = rs.StringBox("Nom du nouveau bloc :", "", "Nouveau bloc")
    if not new_name:
        return None, None
    level = 0
    i = 1
    existing_sigs = set(sig for (_, _, sig) in existing_triplets)
    while "{}#{}".format(new_name, i) in existing_sigs:
        i += 1
    signature = "{}#{}".format(new_name, i)
    return level, signature


def _pick_orphan_name_from_listbox(existing_triplets):
    """
    Ouvre une ListBox complète: <Nouveau nom...> + tous les couples
    level/nom existants. Retourne (level, signature) ou (None, None)
    si annulé.
    """
    NEW_NAME_LABEL = "<Nouveau nom...>"
    choices = [NEW_NAME_LABEL]
    choice_map = {}  # label -> (level, full_signature)

    for lvl, disp, sig in existing_triplets:
        label = "{}  (Level {})".format(disp, lvl)
        choices.append(label)
        choice_map[label] = (lvl, sig)

    picked = rs.ListBox(choices, "Choisissez un nom de bloc à attribuer", "Attribution de bloc manquante")
    if not picked:
        return None, None

    if picked == NEW_NAME_LABEL:
        return _pick_new_orphan_name(existing_triplets)
    else:
        level, signature = choice_map[picked]
        return level, signature


def assign_orphan_blockname(orphan_objs, existing_triplets):
    """
    Demande à l'utilisateur d'attribuer un (level, signature) aux objets
    orphelins (sans aucune clé BlockNameLevel_X).

    - Affiche/sélectionne les objets concernés pour que l'utilisateur voie
      de quoi il s'agit.
    - Propose un GetString avec en raccourci (mot-clé court, sans espace)
      le premier nom trouvé dans la sélection, plus un mot-clé "Liste" qui
      ouvre la ListBox complète (tous les couples existants + "Nouveau nom").
    - Choix d'un nom existant -> fusion directe avec la signature exacte
      (même level, même signature complète, ex. "Bloc01#1").
    - Choix "Nouveau nom" -> demande le nom, niveau 0 par défaut, nouvelle
      signature indexée "<nom>#1".

    Retourne (level, signature) ou (None, None) si annulé.

    IMPORTANT: cette fonction ne modifie AUCUNE UserText sur les objets.
    Elle se contente de retourner le couple choisi; c'est à l'appelant de
    décider comment l'appliquer (en mémoire ou via SetUserText).
    """
    rs.UnselectAllObjects()
    rs.SelectObjects(orphan_objs)
    rs.EnableRedraw(True)

    LIST_KEYWORD = "Liste"

    if existing_triplets:
        first_lvl, first_disp, first_sig = existing_triplets[0]
        # Mot-clé court, sans espace, sans parenthèses, pour rester
        # cliquable/tapable dans le mode liste de GetString.
        default_keyword = first_disp.replace(" ", "_")

        print("Objet(s) sans attribution de bloc: {} -> proposition '{}' (Level {})".format(
            len(orphan_objs), first_disp, first_lvl))
        for lvl, disp, sig in existing_triplets:
            print("  - disponible: {} (Level {})".format(disp, lvl))

        choices = [default_keyword, LIST_KEYWORD]
        msg = "Nom à attribuer aux {} objet(s) orphelin(s)".format(len(orphan_objs))
        picked = rs.GetString(msg, default_keyword, choices)

        if picked is None:
            return None, None
        elif picked == default_keyword:
            return first_lvl, first_sig
        elif picked == LIST_KEYWORD:
            return _pick_orphan_name_from_listbox(existing_triplets)
        else:
            # L'utilisateur a tapé autre chose que les choix proposés
            # -> traité comme un nouveau nom direct, niveau 0.
            i = 1
            existing_sigs = set(sig for (_, _, sig) in existing_triplets)
            while "{}#{}".format(picked, i) in existing_sigs:
                i += 1
            return 0, "{}#{}".format(picked, i)
    else:
        # Aucun couple existant dans la sélection: pas de raccourci possible,
        # on demande directement le nouveau nom (niveau 0).
        msg = "{} objet(s) sans attribution de bloc. Aucun nom existant détecté.".format(len(orphan_objs))
        print(msg)
        return _pick_new_orphan_name(existing_triplets)


def handle_orphan_objects(current_selection):
    """
    Détecte les objets "Root" (sans aucune clé BlockNameLevel_X) dans la
    sélection courante. Si trouvés, demande à l'utilisateur de leur
    attribuer un (level, signature).

    IMPORTANT: aucune UserText n'est écrite ici. L'attribution reste
    purement en mémoire (dict virtual_overrides) tant que la reconstruction
    n'a pas réellement besoin de matérialiser un bloc, afin que l'opération
    reste annulable avec Ctrl+Z comme n'importe quelle autre action native.
    La matérialisation réelle (SetUserText) n'intervient que plus tard,
    au moment de la création du Pose temporaire pour l'origine -- exactement
    comme pour n'importe quel autre groupe découvert dans le flux normal.

    Retourne un dict {obj_id: (level, signature)} si succès (vide si rien à
    faire), ou None si l'utilisateur annule.
    """
    h_map = get_hierarchy_map(current_selection)
    if "Root" not in h_map or not h_map["Root"]["objects"]:
        return {}

    orphan_objs = h_map["Root"]["objects"]
    existing_triplets = get_existing_level_signature_pairs(current_selection)

    level, signature = assign_orphan_blockname(orphan_objs, existing_triplets)
    if level is None:
        print("Opération annulée.")
        return None

    return {obj: (level, signature) for obj in orphan_objs}



def _get_pose_origin(prompt):
    """
    Demande à l'utilisateur de choisir un objet comme origine.
    - Clic sur un objet  → retourne (xform, True)
    - Touche Entrée      → retourne (XformIdentity, True)  [origine Monde]
    - Touche Échap       → retourne (None, False)           [annulation]

    Inspiré de _get_origin_with_option() dans defineBlock.py.
    """
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(prompt)
    go.AcceptNothing(True)   # Entrée autorisée
    go.DisablePreSelect()

    while True:
        get_rc = go.Get()

        # L'utilisateur a cliqué sur un objet
        if get_rc == Rhino.Input.GetResult.Object:
            obj_ref = go.Object(0)
            origin_id = obj_ref.ObjectId
            go.Dispose()
            if rs.IsBlockInstance(origin_id):
                xf = rs.BlockInstanceXform(origin_id)
            else:
                xf = rs.XformTranslation(get_bbox_center(origin_id))
            return xf if xf is not None else rs.XformIdentity(), True

        # Entrée sans sélection → Origine Mondiale
        elif get_rc == Rhino.Input.GetResult.Nothing:
            go.Dispose()
            return rs.XformIdentity(), True

        # Échap ou toute autre annulation
        else:
            go.Dispose()
            return None, False


def reconstructBlock():
    initial_objs = rs.GetObjects("Sélectionnez les objets à reconstruire", preselect=True)
    if not initial_objs: return

    rs.EnableRedraw(False)
    ensure_pose_block()
    current_selection = list(initial_objs)

    # --- ATTRIBUTION DES OBJETS ORPHELINS (sans BlockNameLevel_X) ---
    # Reste purement en mémoire (aucune UserText écrite) pour que
    # l'opération soit annulable avec Ctrl+Z comme tout le reste.
    rs.EnableRedraw(True)
    virtual_overrides = handle_orphan_objects(current_selection)
    if virtual_overrides is None:
        return
    rs.EnableRedraw(False)

    # --- VÉRIFICATION ORIGINES ---
    h_map = get_hierarchy_map(current_selection, virtual_overrides)
    missing = [sig for sig, d in h_map.items() if sig != "Root" and d["pose"] is None]

    # Matérialisation tardive des orphelins qui ont fusionné avec un groupe
    # déjà pourvu d'une origine (donc absent de `missing`, jamais traité
    # par la boucle ci-dessous). On l'écrit maintenant, juste avant toute
    # opération de reconstruction qui en dépend.
    if virtual_overrides:
        for sig, data in h_map.items():
            if sig == "Root": continue
            if data["pose"] is None: continue  # sera traité dans la boucle missing
            group_objs = data["objects"]
            if any(o in virtual_overrides for o in group_objs):
                key = "BlockNameLevel_{}".format(data["level"])
                for obj in group_objs:
                    if obj in virtual_overrides:
                        rs.SetUserText(obj, key, sig)
    
    if missing:
        levels = [h_map[sig]["level"] for sig in missing]
        low_lvl = max(levels)
        objs_to_fix = [o for sig in missing if h_map[sig]["level"] == low_lvl for o in h_map[sig]["objects"]]
        if set(current_selection) != set(objs_to_fix):
            rs.UnselectAllObjects()
            rs.SelectObjects(objs_to_fix)
            rs.EnableRedraw(True)
            print("Origine manquante au niveau {}.".format(low_lvl))
            return
        
        rs.EnableRedraw(True)
        for sig in missing:
            xform, success = _get_pose_origin(
                "Origine pour '{}' (clic sur un objet/bloc, ou Entrée = Monde)".format(sig)
            )

            # Échap → annulation totale
            if not success:
                print("Opération annulée.")
                return

            # Matérialisation tardive: si ce groupe provient d'objets
            # orphelins virtuels, on écrit maintenant la vraie UserText
            # (action normale, donc annulable par Ctrl+Z), juste avant de
            # créer le Pose qui en dépend pour la suite du pipeline.
            group_objs = h_map[sig]["objects"]
            key = "BlockNameLevel_{}".format(h_map[sig]["level"])
            ref_obj = group_objs[0]
            if ref_obj in virtual_overrides:
                for obj in group_objs:
                    rs.SetUserText(obj, key, sig)

            temp_pose = rs.InsertBlock("Pose", [0,0,0])
            rs.TransformObject(temp_pose, xform)

            # Propagation des UserText de hiérarchie
            for k in rs.GetUserText(ref_obj):
                if k.startswith("BlockNameLevel_"):
                    rs.SetUserText(temp_pose, k, rs.GetUserText(ref_obj, k))

            current_selection.append(temp_pose)

        rs.EnableRedraw(False)

    # --- RECONSTRUCTION ---
    h_map = get_hierarchy_map(current_selection)
    
    unique_levels = sorted(
        [d["level"] for sig, d in h_map.items() if sig != "Root"],
        reverse=True
    )
    
    for current_lvl in unique_levels:
        current_map = get_hierarchy_map(current_selection)
        
        for sig, data in current_map.items():
            if data["level"] != current_lvl or sig == "Root": continue
            
            pose_obj, geometries = data["pose"], data["objects"]
            if not pose_obj or not geometries: continue

            original_name = clean_name(sig)
            target_name = original_name
            xform = rs.BlockInstanceXform(pose_obj)
            
            skip_reconstruction = False
            overwrite_block = False
            user_action = "Ecraser"

            # --- BOUCLE DE VALIDATION DU NOM ---
            while rs.IsBlock(target_name):
                rs.UnselectAllObjects()
                rs.SelectObjects(geometries)
                rs.SelectObject(pose_obj)
                
                temp_compare = rs.InsertBlock(target_name, [0,0,0])
                rs.TransformObject(temp_compare, xform)
                rs.ObjectColor(temp_compare, [150, 150, 150])
                
                rs.EnableRedraw(True)
                msg = "Le bloc '{}' existe déjà. Souhaitez-vous l'écraser ?".format(target_name)
                user_action = rs.GetString(msg, "Ecraser", ["Ecraser", "Renommer", "Conserver", "Annuler"])
                rs.EnableRedraw(False)
                rs.DeleteObject(temp_compare)
                
                if user_action == "Ecraser":
                    overwrite_block = True
                    break 
                elif user_action == "Renommer":
                    suggested_name = get_indexed_name(target_name)
                    new_name = rs.StringBox("Nouveau nom :", suggested_name, "Renommer le bloc")
                    if not new_name:
                        user_action = "Annuler"
                        break
                    target_name = new_name
                elif user_action == "Conserver":
                    skip_reconstruction = True
                    break
                else:
                    user_action = "Annuler"
                    break
            
            if user_action == "Annuler": continue

            # --- MISE À JOUR DES SIGNATURES ---
            if target_name != original_name:
                old_prefix = original_name + "#"
                new_prefix = target_name + "#"
                for obj in current_selection:
                    keys = rs.GetUserText(obj)
                    if keys:
                        for k in keys:
                            if k.startswith("BlockNameLevel_"):
                                val = rs.GetUserText(obj, k)
                                if val and val.startswith(old_prefix):
                                    rs.SetUserText(obj, k, val.replace(old_prefix, new_prefix))

            # --- RECONSTRUCTION GÉOMÉTRIQUE ---
            if not skip_reconstruction:
                inv_xform = rs.XformInverse(xform)
                copied_geos = []
                for g in geometries:
                    cp = rs.CopyObject(g)
                    rs.TransformObject(cp, inv_xform)
                    keys = rs.GetUserText(cp)
                    if keys:
                        for k in keys:
                            if k.startswith("BlockNameLevel_"): rs.SetUserText(cp, k, "")
                    copied_geos.append(cp)
                
                if overwrite_block and rs.IsBlock(target_name):
                    idef = sc.doc.InstanceDefinitions.Find(target_name)
                    if idef:
                        geo_list = []
                        attr_list = []
                        for guid in copied_geos:
                            rh_obj = sc.doc.Objects.Find(guid)
                            if rh_obj:
                                geo_list.append(rh_obj.Geometry)
                                attr_list.append(rh_obj.Attributes)
                        sc.doc.InstanceDefinitions.ModifyGeometry(idef.Index, geo_list, attr_list)
                    rs.DeleteObjects(copied_geos)
                else:
                    rs.AddBlock(copied_geos, [0,0,0], target_name, delete_input=False)
                    rs.DeleteObjects(copied_geos)

            # Insertion instance
            new_inst = rs.InsertBlock(target_name, [0,0,0])
            rs.TransformObject(new_inst, xform)
            
            # Transmission UserText
            sample_obj = geometries[0]
            all_keys = rs.GetUserText(sample_obj)
            if all_keys:
                for k in all_keys:
                    if k.startswith("BlockNameLevel_"):
                        lvl_idx = int(k.split("_")[-1])
                        if lvl_idx < current_lvl:
                            rs.SetUserText(new_inst, k, rs.GetUserText(sample_obj, k))

            # Nettoyage
            rs.DeleteObjects(geometries)
            rs.DeleteObject(pose_obj)
            
            current_selection = [obj for obj in current_selection if obj not in geometries and obj != pose_obj]
            current_selection.append(new_inst)
    
    count = 0
    for item in h_map:
        if item == 'Root':
            if 'objects' in h_map['Root']:
                print("{} objets ignorés car sans structure. (Copier les propriétés d'un autre objet)".format(len(h_map['Root']['objects'])))
                current_selection = [obj for obj in current_selection if obj not in h_map['Root']['objects']]
        count += 1
    print("{} blocs reconstruits au sein de {} instance(s)".format(count, len(current_selection)))

    rs.EnableRedraw(True)
    if current_selection: rs.SelectObjects(current_selection)
    print("Terminé.")

if __name__ == "__main__":
    reconstructBlock()

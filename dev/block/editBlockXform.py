"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import rhinoscript.utility as rhutil
import uuid 


# ----------------------------------------------------------------------
# Fonctions Utilitaires RhinoCommon/rhinoscriptsyntax
# ----------------------------------------------------------------------


def _format_xform(x):
    """Retourne une représentation 4x4 d'une transformation."""
    if x is None:
        return "<None>"
    out_lines = []
    for i in range(4):
        row = []
        for j in range(4):
            v = x[i, j]
            row.append("%+0.6f" % (v,))
        out_lines.append(" ".join(row))
    return "\n".join(out_lines)


def update_block_def(sti, xform):
    """
    Applique 'xform' (X_def) à TOUTE la géométrie interne de la définition
    via RhinoCommon ModifyGeometry.
    """
    objref = rs.coercerhinoobject(sti)
    if objref is None: return False
    
    idef = objref.InstanceDefinition
    idefIndex = idef.Index


    idef_obj = sc.doc.InstanceDefinitions[idefIndex]
    if idef_obj is None: return False
    
    block_objects = idef_obj.GetObjects()


    newGeometry = []
    newAttributes = []


    for rhino_obj in block_objects:
        # Dupliquer et transformer la géométrie de l'objet dans la définition
        geometry = rhino_obj.Geometry.DuplicateShallow() 
        geometry.Transform(xform)
        attributes = rhino_obj.Attributes.Duplicate()
        newGeometry.append(geometry)
        newAttributes.append(attributes)


    InstanceDefinitionTable = sc.doc.InstanceDefinitions
    success = InstanceDefinitionTable.ModifyGeometry(idefIndex, newGeometry, newAttributes)
    return success




def selective_update_block_def(definition_name, target_object_id, xform):
    """
    Applique 'xform' (X_comp) UNIQUEMENT à un objet spécifique (l'instance enfant) 
    à l'intérieur de la définition parente via ModifyGeometry.
    'target_object_id' doit être l'ID de l'objet tel qu'il est stocké DANS la définition.
    """
    
    # Recherche de la définition parente directement par son nom (string)
    parent_def = sc.doc.InstanceDefinitions.Find(definition_name, False) 
    
    if parent_def is None: 
        print("ATTENTION: Définition parente '%s' introuvable." % definition_name)
        return False
    
    idefIndex = parent_def.Index
    block_objects = parent_def.GetObjects()


    newGeometry = []
    newAttributes = []
    modified = False


    for rhino_obj in block_objects:
        geometry = rhino_obj.Geometry.DuplicateShallow() 
        attributes = rhino_obj.Attributes.Duplicate()


        # Cible l'objet (l'instance de bloc enfant) par son ID interne à la définition
        if rhino_obj.Id.Equals(target_object_id):
            # Applique X_comp pour compenser l'effet X_def
            geometry.Transform(xform) 
            modified = True


        newGeometry.append(geometry)
        newAttributes.append(attributes)


    if modified:
        InstanceDefinitionTable = sc.doc.InstanceDefinitions
        success = InstanceDefinitionTable.ModifyGeometry(idefIndex, newGeometry, newAttributes)
        # print("DEBUG_UPWARD_MOD: Compensated nested instance %s in def %s. Success: %s" % (target_object_id, definition_name, success))
        return success
    
    return False


def PropagateUpwardCompensation(child_block_name, xform_compensation, visited_defs=None):
    """
    RÉCURSIF : applique la compensation (X_comp) à l'instance de bloc enfant
    à l'intérieur de toutes ses définitions parentes.
    """
    if visited_defs is None:
        visited_defs = set()


    parent_block_names = rs.BlockContainers(child_block_name)
    if not parent_block_names:
        return


    for parent_name in parent_block_names:
        if parent_name in visited_defs:
            continue  # éviter double propagation


        visited_defs.add(parent_name)


        # 1. Objets dans la définition parente (GUIDs d'objets internes à la définition)
        definition_objects = rs.BlockObjects(parent_name) 


        # 2. Sauvegarder les positions initiales des objets non-blocs (pour debug)
        pre_positions = {}
        for obj_id in definition_objects:
            if not rs.IsBlockInstance(obj_id):
                bbox = rs.BoundingBox(obj_id)
                if bbox:
                    pt = rs.PointCoordinates(bbox[0])
                    pre_positions[obj_id] = pt


        # 3. Identifier uniquement les instances directes de l'enfant dans la définition parente
        child_instances_in_def = [
            obj_id for obj_id in definition_objects
            if rs.IsBlockInstance(obj_id) and rs.BlockInstanceName(obj_id) == child_block_name
        ]


        # 4. Appliquer la compensation (X_comp) à chaque instance enfant interne
        for inst_id_in_def in child_instances_in_def:
            selective_update_block_def(parent_name, inst_id_in_def, xform_compensation)


        # 5. Vérification debug : s'assurer que les objets non-blocs n'ont pas bougé
        for obj_id, old_pt in pre_positions.items():
            bbox = rs.BoundingBox(obj_id)
            if bbox:
                new_pt = rs.PointCoordinates(bbox[0])
                dx, dy, dz = new_pt[0]-old_pt[0], new_pt[1]-old_pt[1], new_pt[2]-old_pt[2]
                dist = (dx**2 + dy**2 + dz**2)**0.5
                if dist > 1e-9:  # tolérance minimale
                    print("WARNING: Objet imbriqué %s a bougé de %.9f unités !" % (obj_id, dist))


        # 6. Récursion vers le parent
        PropagateUpwardCompensation(parent_name, xform_compensation, visited_defs)


# ----------------------------------------------------------------------


## ⚙️ Fonction Principale d'Exécution (`editBlockXform`)


def editBlockXform():
    # 1. Sélection de la Cible
    sel_tar_insts = rs.GetObjects("Choisir les instances de bloc cible", rs.filter.instance, preselect=True)
    if not sel_tar_insts: return 0


    # 2. Sélection de la Source (logique simplifiée)
    sel_ori_insts = rs.GetObjects("Choisir un Bloc Source (ou appuyer sur Entrée pour utiliser l'Origine Mondiale)", rs.filter.instance, maximum_count=1)


    if sel_ori_insts is None or sel_ori_insts is True:
        soiXform = rs.XformIdentity() # T_source
    elif isinstance(sel_ori_insts, list) and len(sel_ori_insts) > 0 and rs.IsBlockInstance(sel_ori_insts[0]):
        soiXform = rs.BlockInstanceXform(sel_ori_insts[0]) # T_source
    else:
        return 0


    rs.EnableRedraw(False)
    
    # 3. Traitement par Définition
    sel_per_def = {}
    for sti in sel_tar_insts:
        objref = rs.coercerhinoobject(sti)
        idef = objref.InstanceDefinition
        sel_per_def.setdefault(idef.Index, []).append(sti)


    target_defs_to_process = {
        idef_index: instances[-1]
        for idef_index, instances in sel_per_def.items()
    }


    for idef_index, sti_for_calc in target_defs_to_process.items():
        # print(('DEBUG: processing definition index', idef_index, 'using instance', sti_for_calc))
        
        stiXform = rs.BlockInstanceXform(sti_for_calc) # T_cible_original
        if stiXform is None: continue
        
        # --- CALCUL DES TRANSFORMATIONS ---
        
        # X_def = T_source^-1 * T_cible_original
        inv_soiXform = rs.XformInverse(soiXform)
        if inv_soiXform is None: continue
        def_update = rs.XformMultiply(inv_soiXform, stiXform) # X_def


        # X_comp = X_def^-1
        inv_def = rs.XformInverse(def_update) # X_comp
        if inv_def is None: continue
        
        # 4. Modification de la Définition de la Cible (Def A)
        ok = update_block_def(sti_for_calc, def_update)
        if not ok: continue
        
        # 5. Compensation Ascendante des Blocs Imbriqués
        initial_block_name = rs.BlockInstanceName(sti_for_calc)
        # print("DEBUG: Starting UPWARD propagation/compensation (SAFE METHOD) for nested blocks.")
        PropagateUpwardCompensation(initial_block_name, inv_def) # inv_def est X_comp
        # print("DEBUG: Upward propagation/compensation complete.")




        # 6. Compensation des Instances Sœurs (et Cible)
        blockName = rs.BlockInstanceName(sti_for_calc)
        bro_tar_insts = rs.BlockInstances(blockName) or []
        
        pre_xforms = {}
        # Récupérer T_old pour toutes les instances (T_old n'est pas affecté par ModifyGeometry)
        for bti in bro_tar_insts:
            pre_xforms[bti] = rs.BlockInstanceXform(bti) 
        
        for bti in bro_tar_insts:
            T_old = pre_xforms.get(bti)
            if T_old is None: continue


            if bti.Equals(sti_for_calc):
                # CIBLE : La transformation finale désirée est T_source
                desired_T = soiXform 
            else:
                # SŒUR : La transformation finale désirée est T_new = X_comp * T_old
                desired_T = rs.XformMultiply(T_old, inv_def) 
            
            # Calcul X_apply : X_apply = desired_T * T_old^-1
            inv_T_old = rs.XformInverse(T_old)
            if inv_T_old is None: continue


            X_apply = rs.XformMultiply(desired_T, inv_T_old)


            if not X_apply.IsIdentity:
                # Appliquer X_apply à l'instance (False = transformation de l'objet)
                rs.TransformObject(bti, X_apply, False)




    rs.EnableRedraw(True)
    return 1


if __name__ == '__main__':
    editBlockXform()

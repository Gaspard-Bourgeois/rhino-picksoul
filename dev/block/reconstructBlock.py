import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import rhinoscript.utility as rhutil

# --- FONCTIONS UTILITAIRES (Identiques à editblockxform) ---

def update_block_def(instance_id, xform):
    """Applique xform à la géométrie interne de la définition."""
    objref = rs.coercerhinoobject(instance_id)
    if not objref: return False
    idef = objref.InstanceDefinition
    idef_index = idef.Index
    
    block_objects = idef.GetObjects()
    new_geometry = []
    new_attributes = []

    for rhino_obj in block_objects:
        geometry = rhino_obj.Geometry.DuplicateShallow() 
        geometry.Transform(xform)
        attributes = rhino_obj.Attributes.Duplicate()
        new_geometry.append(geometry)
        new_attributes.append(attributes)

    return sc.doc.InstanceDefinitions.ModifyGeometry(idef_index, new_geometry, new_attributes)

def selective_update_block_def(definition_name, target_object_id, xform):
    """Compense une instance spécifique à l'intérieur d'une autre définition."""
    parent_def = sc.doc.InstanceDefinitions.Find(definition_name, False)
    if not parent_def: return False
    
    idef_index = parent_def.Index
    block_objects = parent_def.GetObjects()
    new_geometry = []
    new_attributes = []
    modified = False

    for rhino_obj in block_objects:
        geometry = rhino_obj.Geometry.DuplicateShallow() 
        attributes = rhino_obj.Attributes.Duplicate()
        if rhino_obj.Id.Equals(target_object_id):
            geometry.Transform(xform)
            modified = True
        new_geometry.append(geometry)
        new_attributes.append(attributes)

    if modified:
        return sc.doc.InstanceDefinitions.ModifyGeometry(idef_index, new_geometry, new_attributes)
    return False

def PropagateUpwardCompensation(child_block_name, xform_compensation, visited_defs=None):
    """Récursivité pour stabiliser les blocs parents."""
    if visited_defs is None: visited_defs = set()
    parent_block_names = rs.BlockContainers(child_block_name)
    if not parent_block_names: return

    for parent_name in parent_block_names:
        if parent_name in visited_defs: continue
        visited_defs.add(parent_name)

        definition_objects = rs.BlockObjects(parent_name)
        child_instances_in_def = [
            obj_id for obj_id in definition_objects
            if rs.IsBlockInstance(obj_id) and rs.BlockInstanceName(obj_id) == child_block_name
        ]

        for inst_id_in_def in child_instances_in_def:
            selective_update_block_def(parent_name, inst_id_in_def, xform_compensation)

        PropagateUpwardCompensation(parent_name, xform_compensation, visited_defs)

# --- FONCTION PRINCIPALE : REBUILD RECIPROQUE ---

def rebuild_reciproque():
    # 1. Sélection de l'instance de référence
    target_inst = rs.GetObject("Sélectionner l'instance de bloc pour réinitialiser la définition", rs.filter.instance)
    if not target_inst: return

    block_name = rs.BlockInstanceName(target_inst)
    
    # 2. Calcul des matrices
    # T_current : La transformation actuelle de l'instance choisie
    t_current = rs.BlockInstanceXform(target_inst)
    
    # X_def : Ce qu'on applique à la géométrie interne pour la ramener à l'origine
    # C'est l'inverse de la position actuelle
    x_def = rs.XformInverse(t_current)
    if not x_def: return

    # X_comp : Ce qu'on applique aux instances pour compenser le changement de définition
    # C'est l'inverse de X_def, donc t_current lui-même.
    x_comp = t_current

    rs.EnableRedraw(False)

    # 3. Mise à jour de la définition (La géométrie interne bouge vers l'origine)
    if not update_block_def(target_inst, x_def):
        rs.EnableRedraw(True)
        print("Erreur lors de la modification de la définition.")
        return

    # 4. Compensation des instances imbriquées (Propagation ascendante)
    # On utilise x_comp pour que les blocs parents ne voient pas de changement visuel
    PropagateUpwardCompensation(block_name, x_comp)

    # 5. Compensation des instances "sœurs" dans le document
    all_instances = rs.BlockInstances(block_name)
    
    for inst in all_instances:
        # On récupère l'ancienne matrice (Rhino ne l'a pas encore mise à jour visuellement)
        t_old = rs.BlockInstanceXform(inst)
        
        if inst == target_inst:
            # L'instance de référence doit maintenant être à l'Identité (0,0,0 sans rotation)
            new_xform = rs.XformIdentity()
        else:
            # Les autres instances reçoivent : T_new = T_old * X_comp
            new_xform = rs.XformMultiply(t_old, x_comp)
        
        # Calcul du delta à appliquer à l'objet instance lui-même
        # X_apply = T_new * T_old^-1
        inv_t_old = rs.XformInverse(t_old)
        x_apply = rs.XformMultiply(new_xform, inv_t_old)
        
        if not x_apply.IsIdentity:
            rs.TransformObject(inst, x_apply)

    rs.EnableRedraw(True)
    print("Définition de bloc '{}' reconstruite et instances stabilisées.".format(block_name))

if __name__ == "__main__":
    rebuild_reciproque()

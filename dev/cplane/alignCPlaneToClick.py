import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Sélection ultra-précise
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Polysurface ou Extrusion)")
    # On accepte Surface (face de Brep) et Polysrf (Brep entier avec sélection de face activée)
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
    go.SubObjectSelect = True 
    go.GroupSelect = False
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. EXTRACTION ROBUSTE DE LA GÉOMÉTRIE
    # On récupère l'index du sous-objet (la face) cliquée
    comp_index = objref.GeometryComponentIndex
    # On récupère la géométrie de base (dans le cas d'un bloc, c'est la géométrie LOCALE du bloc)
    base_geom = objref.Geometry()
    
    face = None
    
    # Cas A : C'est un Brep (ou une face de Brep)
    if isinstance(base_geom, Rhino.Geometry.Brep):
        if comp_index.Index >= 0:
            face = base_geom.Faces[comp_index.Index]
        else:
            face = base_geom.Faces[0] # Fallback
            
    # Cas B : C'est une Extrusion (ex: commande Boîte ou Extrusion simple)
    elif isinstance(base_geom, Rhino.Geometry.Extrusion):
        brep = base_geom.ToBrep()
        if comp_index.Index >= 0:
            face = brep.Faces[comp_index.Index]
        else:
            face = brep.Faces[0]

    if face is None:
        print("Erreur : Impossible d'accéder à la face de la définition.")
        return

    # 3. TRANSFORMATION (LE POINT CRITIQUE)
    # objref.InstanceXform renvoie la matrice totale du bloc vers le monde.
    # Pour un objet normal (hors bloc), cette matrice est 'Identity' (neutre). 
    # C'est ce qui rend ce script universel.
    xform = objref.InstanceXform

    # 4. CALCUL DU PLAN
    pick_pt_world = objref.SelectionPoint()
    
    # Ramener le point de clic dans le référentiel local de la définition
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    rc_inv, inv_xform = xform.TryGetInverse()
    if rc_inv:
        local_pt.Transform(inv_xform)

    # Calculer le plan (Frame) sur la face locale
    success_uv, u, v = face.ClosestPoint(local_pt)
    success_frame, local_plane = face.FrameAt(u, v)

    if not success_frame:
        print("Erreur : Calcul du plan local impossible.")
        return

    # Transformer le plan LOCAL vers le MONDE
    world_plane = local_plane.Duplicate()
    world_plane.Transform(xform)
    
    # On force l'origine exacte au point de clic
    world_plane.Origin = pick_pt_world

    # 5. ORIENTATION ET VUE
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    
    # Si la normale s'éloigne de la caméra, on la retourne
    if (world_plane.Normal * viewport.CameraDirection) > 0:
        world_plane.Flip()

    # Application
    viewport.SetConstructionPlane(world_plane)
    
    # Synchronisation de la vue (Top relative au CPlane)
    rs.Command("_Plan", False)
    
    sc.doc.Views.Redraw()
    print("Succès : CPlane aligné sur la face (Compatible Instances de Bloc).")

if __name__ == "__main__":
    ForceSmartCPlane()

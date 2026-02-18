import Rhino
import scriptcontext as sc

def SmartCPlaneFinal():
    # 1. Configuration de la sélection pour accepter les sous-faces
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Extrusion ou Polysurface)")
    # Le filtre Surface permet de sélectionner des faces de Brep ou d'Extrusion
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True 
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. Récupération de la face (Gestion robuste pour Blocs et Extrusions)
    face = objref.Face()
    if face is None:
        # Cas spécifique : si objref.Face() échoue, on force la conversion en Brep
        geom = objref.Geometry()
        if hasattr(geom, "ToBrep"):
            brep = geom.ToBrep()
            face = brep.Faces[objref.GeometryComponentIndex.Index]

    if face is None:
        print("Erreur : Impossible d'accéder à la géométrie de la face.")
        return

    # 3. Récupération des données spatiales
    pick_pt_world = objref.SelectionPoint()
    parent_obj = objref.Object()
    
    # Matrice de transformation (Identité par défaut si ce n'est pas un bloc)
    xform = Rhino.Geometry.Transform.Identity
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform

    # 4. Calcul du plan (Espace Local -> Espace Monde)
    # On transforme le point de clic "monde" en point "local" au bloc
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    success_inv, inv_xform = xform.TryGetInverse()
    if success_inv:
        local_pt.Transform(inv_xform)

    # Calcul de la normale sur la face dans la définition du bloc
    rc, u, v = face.ClosestPoint(local_pt)
    success_frame, plane = face.FrameAt(u, v)

    if not success_frame:
        print("Erreur : Impossible de calculer le plan de la face.")
        return

    # On transforme le plan local pour qu'il corresponde à l'instance du bloc dans le monde
    plane.Transform(xform)
    
    # On replace l'origine exactement sur le point cliqué
    plane.Origin = pick_pt_world

    # 5. Inversion intelligente (Orientation vers la caméra)
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    # CameraDirection est le vecteur qui va de la caméra vers l'objet
    cam_dir = viewport.CameraDirection
    
    # Si le produit scalaire > 0, la normale et la caméra pointent dans le même sens
    # (donc la normale entre dans l'objet), on doit inverser.
    if (plane.Normal * cam_dir) > 0:
        plane.Flip()

    # 6. Mise à jour du CPlane
    viewport.SetConstructionPlane(plane)
    view.Redraw()
    print("CPlane aligné sur la face (Support Bloc/Extrusion OK).")

if __name__ == "__main__":
    SmartCPlaneFinal()

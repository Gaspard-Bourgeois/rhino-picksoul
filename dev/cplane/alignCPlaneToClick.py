import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def SmartCPlaneAndPlan():
    # 1. Sélection de la face (Fonctionne sur Brep, Extrusion, Bloc)
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc ou Objet standard)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True 
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. Récupération de la face géométrique
    # On passe par la géométrie directe pour éviter les erreurs de type Brep/Extrusion
    face = objref.Geometry()
    if not isinstance(face, Rhino.Geometry.BrepFace):
        # Si c'est une extrusion, on la convertit à la volée
        if hasattr(face, "ToBrep"):
            brep = face.ToBrep()
            face = brep.Faces[0]
    
    if not face:
        print("Erreur : Impossible d'extraire la face.")
        return

    # 3. Gestion de la transformation (La partie critique pour les blocs)
    pick_pt_world = objref.SelectionPoint()
    parent_obj = objref.Object()
    
    # Matrice d'identité par défaut
    xform = Rhino.Geometry.Transform.Identity
    
    # Si c'est une instance de bloc, on récupère sa matrice de transformation
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform

    # 4. Calcul du plan (Mapping Monde -> Local -> Monde)
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    success_inv, inv_xform = xform.TryGetInverse()
    if success_inv:
        local_pt.Transform(inv_xform)

    # Trouver la normale locale sur la définition du bloc
    rc, u, v = face.ClosestPoint(local_pt)
    success_frame, plane = face.FrameAt(u, v)

    if not success_frame:
        return

    # Appliquer la transformation du bloc au plan local pour le remettre dans le monde
    plane.Transform(xform)
    # Caler l'origine sur le clic
    plane.Origin = pick_pt_world

    # 5. Inversion intelligente (Z vers l'utilisateur)
    viewport = sc.doc.Views.ActiveView.ActiveViewport
    if (plane.Normal * viewport.CameraDirection) > 0:
        plane.Flip()

    # 6. Mise à jour du CPlane
    viewport.SetConstructionPlane(plane)
    
    # 7. Mise à jour de la vue (Commandes demandées)
    # On utilise rs.Command pour forcer la mise à jour de la vue proprement
    rs.Command("_SetView _CPlane _Top", False)
    rs.Command("_Plan", False)
    
    sc.doc.Views.ActiveView.Redraw()
    print("CPlane et Vue mis à jour.")

if __name__ == "__main__":
    SmartCPlaneAndPlan()

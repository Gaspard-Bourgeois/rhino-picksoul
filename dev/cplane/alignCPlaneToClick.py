import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def SmartCPlaneV3():
    # 1. Configuration de la sélection
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Surface, Polysurface, Extrusion ou Bloc)")
    
    # On accepte les surfaces, les polysurfaces et les extrusions
    go.GeometryFilter = (Rhino.DocObjects.ObjectType.Surface | 
                         Rhino.DocObjects.ObjectType.Brep | 
                         Rhino.DocObjects.ObjectType.Extrusion)
    go.SubObjectSelect = True
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. Récupération de la face
    # .Face() fonctionne pour les Breps et les Extrusions dans Rhino 7
    face = objref.Face()
    if not face:
        print("Erreur : Impossible d'extraire la géométrie de la face.")
        return

    # 3. Récupération du point de clic et gestion de la transformation
    pick_pt_world = objref.SelectionPoint()
    parent_obj = objref.Object()
    
    # Initialisation de la matrice de transformation (Identité par défaut)
    xform = Rhino.Geometry.Transform.Identity
    
    # Si l'objet parent est une instance de bloc, on récupère sa transformation
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform
    
    # 4. Calcul du plan en coordonnées LOCALES
    # Pour trouver les paramètres U,V, on doit ramener le point de clic dans l'espace local du bloc
    local_pick_pt = Rhino.Geometry.Point3d(pick_pt_world)
    if xform != Rhino.Geometry.Transform.Identity:
        # On calcule l'inverse de la transformation du bloc
        success, inv_xform = xform.TryGetInverse()
        if success:
            local_pick_pt.Transform(inv_xform)

    # Trouver les paramètres U,V sur la face locale
    rc, u, v = face.ClosestPoint(local_pick_pt)
    rc, plane = face.FrameAt(u, v)

    # 5. Transformer le plan LOCAL vers le monde REEL (World)
    # On applique la rotation/position du bloc au plan calculé
    plane.Transform(xform)
    
    # On force l'origine au point de clic précis
    plane.Origin = pick_pt_world

    # 6. Correction de l'orientation (Z-Face vers Caméra)
    viewport = sc.doc.Views.ActiveView.ActiveViewport
    cam_dir = viewport.CameraDirection # Vecteur de la caméra

    # Si le produit scalaire est positif, la normale et la caméra vont dans le même sens
    # La face nous tourne le dos, donc on l'inverse.
    if (plane.Normal * cam_dir) > 0:
        plane.Flip()

    # 7. Application du CPlane
    viewport.SetConstructionPlane(plane)
    sc.doc.Views.ActiveView.Redraw()
    print("CPlane mis à jour (Orientation corrigée).")

if __name__ == "__main__":
    SmartCPlaneV3()

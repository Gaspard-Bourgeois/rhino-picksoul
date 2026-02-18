import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def SmartCPlaneUniversal():
    # 1. Sélection de la face (accepte sous-objets de blocs et polysurfaces)
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Surface, Polysurface ou Bloc)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    face = objref.Face()
    pick_pt = objref.SelectionPoint()
    
    if not face:
        print("Erreur : Impossible de récupérer la face.")
        return

    # 2. Calcul du plan local sur la face
    rc, u, v = face.ClosestPoint(pick_pt)
    rc, plane = face.FrameAt(u, v)

    # 3. Gestion de la transformation (La clé pour les BLOCS)
    # On récupère l'objet parent pour voir s'il a une transformation
    parent_obj = objref.Object()
    if parent_obj and isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        # Si c'est un bloc, on applique sa matrice de transformation au plan
        xform = parent_obj.InstanceXform
        plane.Transform(xform)
    elif objref.Geometry().HasBrepForm:
        # Pour une polysurface standard, on s'assure que le point est en World Coordinates
        # (Généralement déjà le cas avec SelectionPoint)
        pass

    # 4. Inversion intelligente (Orientation vers la caméra)
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    cam_dir = viewport.CameraDirection 

    # Si la normale pointe dans la même direction que la caméra (dot > 0), on inverse
    if (plane.Normal * cam_dir) > 0:
        plane.Flip()

    # 5. Mise à jour du CPlane
    # On force l'origine au point cliqué pour la précision
    plane.Origin = pick_pt
    viewport.SetConstructionPlane(plane)
    
    sc.doc.Views.Redraw()
    print("CPlane aligné sur la face (Normalisé vers la caméra).")

if __name__ == "__main__":
    SmartCPlaneUniversal()

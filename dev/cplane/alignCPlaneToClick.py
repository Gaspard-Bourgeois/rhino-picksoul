import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Configuration de la sélection pour accepter les sous-objets (faces)
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc ou Brep)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True
    go.GroupSelect = False 
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    face = objref.Face()
    
    if face is None:
        print("Erreur : Impossible de récupérer la face.")
        return

    # 2. Gestion de la transformation (Cas spécifique des Blocs)
    # On récupère la matrice de transformation de l'instance
    xform = Rhino.Geometry.Transform.Identity
    parent_obj = objref.Object()
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform

    # 3. Calcul des paramètres sur la face locale
    pick_pt_world = objref.SelectionPoint()
    
    # On projette le point de clic sur la face (en tenant compte de la transformation)
    local_pick_pt = Rhino.Geometry.Point3d(pick_pt_world)
    rc, inv_xform = xform.TryGetInverse()
    if rc: local_pick_pt.Transform(inv_xform)

    success, u, v = face.ClosestPoint(local_pick_pt)
    if not success: return

    # Création du plan basé sur la normale de la face
    origin = face.PointAt(u, v)
    normal = face.NormalAt(u, v)
    
    # On construit un plan local à la définition du bloc
    plane = Rhino.Geometry.Plane(origin, normal)

    # 4. Transformation du plan LOCAL vers le monde REEL
    plane.Transform(xform)
    
    # On force l'origine exacte là où l'utilisateur a cliqué
    plane.Origin = pick_pt_world

    # 5. Orientation par rapport à la vue (Face à la caméra)
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    
    # Si le Z du CPlane pointe à l'opposé de la caméra, on l'inverse
    cam_dir = viewport.CameraDirection
    if (plane.Normal * cam_dir) > 0:
        plane.Flip()

    # 6. Mise à jour du CPlane et alignement de la vue
    viewport.SetConstructionPlane(plane)
    
    # On aligne la vue pour regarder le plan de face (équivalent de _Plan)
    viewport.SetProjection(Rhino.Display.DefinedViewportProjection.Top, None, False)
    # On force la caméra à s'aligner sur le nouveau plan
    viewport.PushViewProjection()
    
    # Utilisation d'une commande simple pour finaliser l'alignement visuel
    rs.Command("_Plan", False)
    
    sc.doc.Views.Redraw()
    print("CPlane aligné sur la face sélectionnée.")

if __name__ == "__main__":
    ForceSmartCPlane()

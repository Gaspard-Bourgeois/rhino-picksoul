import Rhino
import scriptcontext as sc

def SmartCPlaneAlign():
    # 1. Configurer la sélection pour accepter les sous-faces (Polysurfaces et Blocs)
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Polysurface ou Bloc)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True # Permet de cliquer sur une face individuelle
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    # 2. Récupérer les données du clic
    objref = go.Object(0)
    face = objref.Face() # La géométrie de la face
    pick_pt = objref.SelectionPoint() # Le point précis du clic

    if not face:
        print("Erreur: Impossible de récupérer la face.")
        return

    # 3. Calculer le plan au point de contact
    # On trouve les paramètres U,V de la face au point cliqué
    rc, u, v = face.ClosestPoint(pick_pt)
    rc, plane = face.FrameAt(u, v)

    # 4. Appliquer la transformation si c'est un BLOC
    # Si la face appartient à un bloc, le plan est actuellement en coordonnées locales.
    # On le transforme en coordonnées "Monde" (World).
    xform = objref.Object().InstanceIncrementalTransform
    if not xform.IsIdentity:
        plane.Transform(xform)

    # 5. Inversion intelligente (Check Caméra)
    # On récupère le vecteur de direction de la caméra actuelle
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    # CameraDirection est le vecteur allant de la caméra vers la cible
    cam_dir = viewport.CameraDirection 

    # Produit scalaire : si > 0, la normale et la caméra pointent dans le même sens
    # Donc la face nous tourne le dos (elle regarde vers l'intérieur de l'objet)
    dot_product = plane.Normal * cam_dir
    
    if dot_product > 0:
        # On inverse l'axe Z pour que le CPlane regarde l'utilisateur
        plane.Flip()

    # 6. Mise à jour du CPlane (sans changer la vue)
    plane.Origin = pick_pt # On centre le plan sur le clic
    viewport.SetConstructionPlane(plane)
    view.Redraw()
    print("CPlane mis à jour avec succès.")

if __name__ == "__main__":
    SmartCPlaneAlign()

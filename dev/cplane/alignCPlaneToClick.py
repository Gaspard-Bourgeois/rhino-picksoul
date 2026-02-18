import Rhino
import scriptcontext as sc

def UltimateCPlane():
    # 1. Sélection ciblée sur les faces
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Extrusion ou Polysurface)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True 
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. Extraction robuste de la face
    # On récupère la géométrie de la face, peu importe si c'est une extrusion ou un brep
    face = objref.Face()
    if not face:
        # Tentative de secours : conversion de l'objet entier en Brep pour extraire la face
        geom = objref.Geometry()
        if hasattr(geom, "ToBrep"):
            brep = geom.ToBrep()
            if brep:
                face = brep.Faces[objref.GeometryComponentIndex.Index]

    if not face:
        print("Erreur : Géométrie de face illisible.")
        return

    # 3. Gestion du point de clic et des transformations
    pick_pt_world = objref.SelectionPoint()
    parent_obj = objref.Object()
    
    # Récupérer la matrice de transformation (monde réel)
    xform = Rhino.Geometry.Transform.Identity
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform

    # 4. Calcul du plan local -> Conversion vers le monde
    # On projette le point de clic dans l'espace local pour obtenir UV
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    success_inv, inv_xform = xform.TryGetInverse()
    if success_inv:
        local_pt.Transform(inv_xform)

    # Calcul de la normale locale
    rc, u, v = face.ClosestPoint(local_pt)
    success_frame, plane = face.FrameAt(u, v)

    # Transformer le plan local pour qu'il suive la position/rotation de l'objet
    plane.Transform(xform)
    # L'origine est placée exactement sur le clic
    plane.Origin = pick_pt_world

    # 5. Correction automatique de l'inversion (Z vers utilisateur)
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    # Vecteur de vue : de la caméra vers la cible
    look_dir = viewport.CameraDirection
    
    # Si le Z du plan "regarde" dans la même direction que la caméra, il pointe vers l'intérieur
    if (plane.Normal * look_dir) > 0:
        plane.Flip()

    # 6. Application
    viewport.SetConstructionPlane(plane)
    view.Redraw()
    print("CPlane aligné avec succès.")

if __name__ == "__main__":
    UltimateCPlane()

import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Sélection
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Brep ou Extrusion)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
    go.SubObjectSelect = True
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. RÉCUPÉRATION DE LA TRANSFORMATION
    # On récupère l'objet "parent". Si c'est un bloc, c'est un InstanceObject.
    parent_obj = objref.Object()
    xform = Rhino.Geometry.Transform.Identity
    
    # Vérification robuste de la présence d'une transformation de bloc
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform

    # 3. RÉCUPÉRATION DE LA FACE (Géométrie locale)
    # objref.Face() renvoie la face telle qu'elle existe dans la définition (coordonnées locales)
    face = objref.Face()
    
    # Gestion des Extrusions (les boîtes créées avec 'Box' par exemple)
    if face is None:
        geom = objref.Geometry()
        if isinstance(geom, Rhino.Geometry.Extrusion):
            face = geom.ToBrep().Faces[0]
        elif isinstance(geom, Rhino.Geometry.Brep):
            idx = objref.GeometryComponentIndex.Index
            if idx >= 0: face = geom.Faces[idx]

    if face is None:
        print("Erreur : Impossible d'extraire la géométrie de la face.")
        return

    # 4. CALCUL DU PLAN
    pick_pt_world = objref.SelectionPoint()
    
    # On convertit le point cliqué en coordonnées LOCALES (référentiel du bloc)
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    success_inv, inv_xform = xform.TryGetInverse()
    if success_inv:
        local_pt.Transform(inv_xform)

    # On trouve le plan local sur la face à ces coordonnées
    success_uv, u, v = face.ClosestPoint(local_pt)
    success_frame, plane = face.FrameAt(u, v)

    if not success_frame:
        return

    # 5. RETOUR AU MONDE RÉEL
    # On applique la transformation du bloc au plan pour l'orienter correctement dans l'espace
    plane.Transform(xform)
    
    # On force l'origine du CPlane au point exact du clic
    plane.Origin = pick_pt_world

    # 6. ALIGNEMENT DE LA VUE
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    
    # Inversion si la normale pointe à l'opposé de la caméra
    if (plane.Normal * viewport.CameraDirection) > 0:
        plane.Flip()

    # Application du CPlane
    viewport.SetConstructionPlane(plane)
    
    # Alignement de la caméra (Vue de dessus du nouveau CPlane)
    rs.Command("_Plan", False)
    
    sc.doc.Views.Redraw()
    print("CPlane aligné.")

if __name__ == "__main__":
    ForceSmartCPlane()

import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Sélection de la face (Gestion précise des sous-objets)
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Polysurface ou Extrusion)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = True
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. Extraction de la géométrie de la FACE (pas de l'objet entier)
    # objref.Face() est plus sûr ici si on veut la normale locale
    face = objref.Face()
    if face is None:
        # Debug : si Face() échoue, on convertit la géométrie en Brep manuellement
        brep = objref.Geometry().ToBrep()
        if brep:
            face = brep.Faces[objref.GeometryComponentIndex.Index]

    if face is None:
        print("Erreur critique : Impossible d'extraire la face.")
        return

    # 3. Récupération des données spatiales
    pick_pt_world = objref.SelectionPoint()
    parent_obj = objref.Object()
    
    # Récupération de la transformation (Crucial pour les blocs orientés)
    xform = Rhino.Geometry.Transform.Identity
    if isinstance(parent_obj, Rhino.DocObjects.InstanceObject):
        xform = parent_obj.InstanceXform

    # 4. Calcul du plan LOCAL sur la définition du bloc
    # On ramène le point cliqué dans l'univers 0,0,0 du bloc pour trouver les UV
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    success_inv, inv_xform = xform.TryGetInverse()
    if success_inv:
        local_pt.Transform(inv_xform)

    # Calcul de la structure (Frame) au point UV
    rc, u, v = face.ClosestPoint(local_pt)
    success_frame, plane = face.FrameAt(u, v)

    if not success_frame:
        print("Erreur : Impossible de calculer le plan local.")
        return

    # 5. Transformation du plan LOCAL vers le monde REEL
    # On applique la matrice du bloc pour que le plan suive l'orientation de l'instance
    plane.Transform(xform)
    
    # On force l'origine du CPlane au point de clic précis
    plane.Origin = pick_pt_world

    # 6. Correction d'inversion par rapport à la vue
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    # Si la normale du plan "fuit" la caméra, on la retourne vers nous
    if (plane.Normal * viewport.CameraDirection) > 0:
        plane.Flip()

    # 7. Application et mise à jour de la vue
    viewport.SetConstructionPlane(plane)
    
    # Synchronisation forcée de la vue
    rs.Command("_SetView _World _Top", False) # Reset temporaire
    rs.Command("_SetView _CPlane _Top", False) # Aligne la caméra sur le nouveau Z
    rs.Command("_Plan", False) # Vue de dessus 2D
    
    sc.doc.Views.Redraw()
    print("CPlane et Vue synchronisés avec succès.")

if __name__ == "__main__":
    ForceSmartCPlane()

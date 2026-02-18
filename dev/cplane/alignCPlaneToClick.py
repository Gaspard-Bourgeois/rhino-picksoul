import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Sélection de la face (Brep, Extrusion ou Instance de bloc)
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Brep ou Extrusion)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
    go.SubObjectSelect = True
    go.GroupSelect = False
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. GESTION DE LA TRANSFORMATION (La correction clé)
    # InstanceTransforms() renvoie la pile de transformations (utile pour blocs imbriqués)
    xforms = objref.InstanceTransforms()
    final_xform = Rhino.Geometry.Transform.Identity
    if xforms:
        for x in xforms:
            final_xform = final_xform * x

    # 3. RÉCUPÉRATION DE LA GÉOMÉTRIE (Face)
    # objref.Face() est la méthode la plus directe pour obtenir la face sélectionnée
    face = objref.Face()
    
    # Cas particulier : Extrusions (elles ne sont pas toujours lues comme BrepFace)
    if face is None:
        geom = objref.Geometry()
        if isinstance(geom, Rhino.Geometry.Extrusion):
            face = geom.ToBrep().Faces[0]
        elif isinstance(geom, Rhino.Geometry.Brep):
            # Si Face() a échoué mais que c'est un Brep, on utilise l'index
            idx = objref.GeometryComponentIndex.Index
            if idx >= 0: face = geom.Faces[idx]

    if face is None:
        print("Erreur : Impossible d'extraire la face de l'objet.")
        return

    # 4. CALCUL DU PLAN
    pick_pt_world = objref.SelectionPoint()
    
    # On ramène le point cliqué dans l'espace local pour trouver les UV corrects
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    rc_inv, inv_xform = final_xform.TryGetInverse()
    if rc_inv:
        local_pt.Transform(inv_xform)

    # Trouver les paramètres UV sur la face locale
    success_uv, u, v = face.ClosestPoint(local_pt)
    # FrameAt donne le plan complet (Origine + Normale + Orientation X/Y)
    success_frame, local_plane = face.FrameAt(u, v)

    if not success_frame:
        return

    # 5. TRANSFORMATION DU PLAN VERS LE MONDE RÉEL
    world_plane = local_plane
    world_plane.Transform(final_xform)
    
    # On force l'origine au point de clic exact pour le confort
    world_plane.Origin = pick_pt_world

    # 6. ALIGNEMENT AVEC LA VUE
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    
    # Si la normale s'éloigne de la caméra, on la retourne vers l'utilisateur
    if (world_plane.Normal * viewport.CameraDirection) > 0:
        world_plane.Flip()

    # 7. APPLICATION
    viewport.SetConstructionPlane(world_plane)
    
    # Synchronisation visuelle (vue de dessus par rapport au nouveau CPlane)
    rs.Command("_Plan", False)
    
    sc.doc.Views.Redraw()
    print("CPlane et Vue synchronisés avec succès.")

if __name__ == "__main__":
    ForceSmartCPlane()

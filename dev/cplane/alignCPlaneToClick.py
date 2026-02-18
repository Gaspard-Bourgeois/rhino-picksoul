import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Sélection
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Bloc, Brep ou Extrusion)")
    # On autorise la sélection de surfaces et de polysurfaces
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
    go.SubObjectSelect = True
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)

    # 2. GESTION DE LA TRANSFORMATION (La version correcte de l'API)
    # InstanceIncrementalTransforms() renvoie un tableau de matrices pour les blocs (même imbriqués)
    # Si ce n'est pas un bloc, le tableau est vide.
    xforms = objref.InstanceIncrementalTransforms()
    full_xform = Rhino.Geometry.Transform.Identity
    for x in xforms:
        full_xform = x * full_xform

    # 3. RÉCUPÉRATION DE LA GÉOMÉTRIE DE LA FACE
    # On récupère d'abord la géométrie sélectionnée (dans l'espace local du bloc)
    geom = objref.Geometry()
    face = None

    if isinstance(geom, Rhino.Geometry.BrepFace):
        face = geom
    elif isinstance(geom, Rhino.Geometry.Brep):
        # Si c'est un Brep complet, on cherche l'index de la face cliquée
        idx = objref.GeometryComponentIndex.Index
        if idx >= 0: face = geom.Faces[idx]
    elif isinstance(geom, Rhino.Geometry.Extrusion):
        # Pour les extrusions, on convertit en Brep pour avoir des faces
        face = geom.ToBrep().Faces[0]

    if face is None:
        print("Erreur : Impossible d'extraire la géométrie de la face.")
        return

    # 4. CALCUL DU PLAN DANS L'ESPACE LOCAL
    pick_pt_world = objref.SelectionPoint()
    
    # Conversion du point cliqué (Monde) vers l'espace Local (Bloc)
    local_pt = Rhino.Geometry.Point3d(pick_pt_world)
    rc, inv_xform = full_xform.TryGetInverse()
    if rc:
        local_pt.Transform(inv_xform)

    # Trouver les paramètres UV sur la face locale pour obtenir la normale exacte
    success, u, v = face.ClosestPoint(local_pt)
    if not success: return
    
    # FrameAt donne un plan complet (Z = Normale, X/Y alignés sur la face)
    rc_frame, local_plane = face.FrameAt(u, v)
    if not rc_frame: return

    # 5. TRANSFORMATION DU PLAN VERS LE MONDE
    # On applique la matrice cumulée du bloc au plan local
    world_plane = local_plane
    world_plane.Transform(full_xform)
    
    # On replace l'origine au point de clic précis
    world_plane.Origin = pick_pt_world

    # 6. ORIENTATION PAR RAPPORT À LA CAMÉRA
    viewport = sc.doc.Views.ActiveView.ActiveViewport
    # Si la normale du plan "regarde" à l'opposé de la caméra, on l'inverse
    if (world_plane.Normal * viewport.CameraDirection) > 0:
        world_plane.Flip()

    # 7. MISE À JOUR DU CPLANE ET DE LA VUE
    viewport.SetConstructionPlane(world_plane)
    
    # On force l'alignement de la vue (équivalent de la commande _Plan)
    rs.Command("_Plan", False)
    
    sc.doc.Views.Redraw()
    print("CPlane aligné avec succès (Blocs et Breps gérés).")

if __name__ == "__main__":
    ForceSmartCPlane()

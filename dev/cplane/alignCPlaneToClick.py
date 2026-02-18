import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

def ForceSmartCPlane():
    # 1. Configuration de la sélection
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Sélectionnez une face (Brep, Extrusion ou Bloc)")
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
    go.SubObjectSelect = True # Permet de sélectionner une face dans un bloc ou un brep
    go.GroupSelect = False
    go.Get()

    if go.CommandResult() != Rhino.Commands.Result.Success:
        return

    objref = go.Object(0)
    
    # 2. Récupération de la géométrie de la face
    # objref.Face() fonctionne pour les Breps et les Blocs
    face = objref.Face()
    
    # Cas particulier : Les Extrusions ne sont pas toujours lues comme des faces
    if face is None:
        geom = objref.Geometry()
        if isinstance(geom, Rhino.Geometry.Extrusion):
            face = geom.ToBrep().Faces[0]
            
    if face is None:
        print("Erreur : Impossible d'extraire la géométrie de la face.")
        return

    # 3. GESTION ROBUSTE DE LA TRANSFORMATION
    # objref.InstanceXform récupère la matrice cumulative (même si bloc dans un bloc)
    # Pour un objet normal (Brep hors bloc), cette matrice est 'Identity' (neutre)
    xform = objref.InstanceXform
    
    # 4. CALCUL DU PLAN (Transition Local -> Monde)
    # A. On récupère le point de clic en coordonnées MONDE
    pick_pt_world = objref.SelectionPoint()
    
    # B. On convertit ce point en coordonnées LOCALES (pour trouver les UV sur la face)
    rc, inv_xform = xform.TryGetInverse()
    pick_pt_local = Rhino.Geometry.Point3d(pick_pt_world)
    if rc: # Si on est dans un bloc, on transforme le point
        pick_pt_local.Transform(inv_xform)

    # C. Calcul des UV et de la normale sur la face LOCALE
    success, u, v = face.ClosestPoint(pick_pt_local)
    if not success:
        return
    
    # On extrait le plan local à cet endroit
    # FrameAt donne l'origine, le X, le Y et le Z (normale) de la face
    res, local_plane = face.FrameAt(u, v)
    
    # D. TRANSFORMATION DU PLAN VERS LE MONDE
    # On applique la matrice de transformation de l'instance au plan entier
    world_plane = local_plane.Duplicate()
    world_plane.Transform(xform)
    
    # On force l'origine sur le point de clic précis (en monde)
    world_plane.Origin = pick_pt_world

    # 5. ALIGNEMENT AVEC LA VUE
    view = sc.doc.Views.ActiveView
    viewport = view.ActiveViewport
    
    # Retourner la face si elle pointe à l'opposé de la caméra
    if (world_plane.Normal * viewport.CameraDirection) > 0:
        world_plane.Flip()

    # 6. APPLICATION
    sc.doc.Views.ActiveView.ActiveViewport.SetConstructionPlane(world_plane)
    
    # Pour que la vue s'aligne (équivalent de la commande _Plan)
    # On utilise rs.Command pour garantir que l'affichage suit la logique de Rhino
    rs.Command("_Plan", False)
    
    sc.doc.Views.Redraw()
    print("CPlane synchronisé (Compatible Blocs & Breps).")

if __name__ == "__main__":
    ForceSmartCPlane()

import rhinoscriptsyntax as rs
import Rhino

def SmartCPlane():
    # 1. Sélection de la face ou de l'objet
    # On autorise la sélection de sous-objets (faces de polysurfaces/blocs)
    res = rs.GetSurfaceObject("Sélectionnez la face pour le CPlane", select=False)
    
    if not res:
        return

    obj_id, surface_id, pick_point = res[0], res[1], res[3]

    # 2. Récupérer la normale de la surface au point cliqué
    # On convertit en géométrie RhinoCommon pour plus de précision
    brep = rs.coercebrep(obj_id)
    if not brep: return
    
    face = brep.Faces[surface_id]
    
    # Trouver les paramètres U,V les plus proches du clic
    success, u, v = face.ClosestPoint(pick_point)
    if not success: return
    
    # Calculer la normale et le plan de la face à cet endroit
    # On utilise FrameAt pour récupérer aussi l'orientation X et Y d'origine
    success, plane = face.FrameAt(u, v)
    if not success: return

    # 3. Ajuster l'orientation par rapport à la caméra
    view = rs.CurrentView()
    cam_dir = rs.ViewCameraDirection(view) # Vecteur de ce que l'on voit

    # Produit scalaire : si > 0, la normale et la caméra pointent dans le même sens
    # (donc la normale "s'éloigne" de nous et entre dans l'objet)
    dot_product = plane.Normal * cam_dir
    
    if dot_product > 0:
        # On inverse l'axe Z (et on ajuste l'axe Y pour garder un repère direct)
        plane.Flip()

    # 4. Mettre à jour le CPlane (sans changer la vue)
    # On déplace l'origine du plan au point exact du clic
    plane.Origin = pick_point
    rs.ViewCPlane(view, plane)

if __name__ == "__main__":
    SmartCPlane()

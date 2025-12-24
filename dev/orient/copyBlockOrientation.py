import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def CopyBlockOrientation():
    source_id = rs.GetObject("Sélectionnez le bloc source (orientation de référence)", rs.filter.instance)
    if not source_id: return
    
    targets = rs.GetObjects("Sélectionnez les blocs à réorienter", rs.filter.instance)
    if not targets: return

    # Obtenir la matrice de la source
    source_xform = rs.BlockInstanceXform(source_id)
    
    rs.EnableRedraw(False)
    for target in targets:
        # Position actuelle de la cible
        target_pos = rs.BlockInstanceInsertPoint(target)
        
        # Créer une nouvelle matrice basée sur la source
        # On repart d'une matrice propre et on applique la translation vers la cible
        new_xform = rg.Transform(source_xform)
        
        # On extrait le point de la source pour calculer le vecteur de déplacement
        source_pos = rs.BlockInstanceInsertPoint(source_id)
        translation = rg.Transform.Translation(target_pos - source_pos)
        
        final_xform = translation * new_xform
        rs.TransformObject(target, final_xform, False)
    rs.EnableRedraw(True)

CopyBlockOrientation()

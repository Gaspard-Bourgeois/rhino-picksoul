import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def AlignCPlaneToBlock():
    # 1. Sélectionner l'instance de bloc
    block_id = rs.GetObject("Sélectionnez une instance de bloc", rs.filter.instance)
    
    if not block_id:
        print("Aucun bloc sélectionné.")
        return

    # 2. Obtenir la matrice de transformation du bloc
    # Cette matrice contient la position, la rotation et l'échelle
    matrix = rs.BlockInstanceXform(block_id)
    
    if matrix:
        # 3. Créer un plan de base (World XY)
        # On applique ensuite la transformation du bloc à ce plan
        new_plane = rg.Plane.WorldXY
        new_plane.Transform(matrix)
        
        # 4. Mettre à jour le CPlane de la vue active
        rs.ViewCPlane(None, new_plane)
        
        print("CPlane aligné sur l'origine du bloc.")

if __name__ == "__main__":
    AlignCPlaneToBlock()

import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def AlignGumballToSpecificBlock():
    # 1. Récupérer les objets déjà sélectionnés
    targets = rs.SelectedObjects()
    if not targets:
        print("Veuillez sélectionner des objets avant de lancer le script.")
        return

    # 2. Demander le bloc de référence (l'orientation à copier)
    # On désactive la présélection pour choisir le bloc
    rs.UnselectAllObjects()
    ref_block = rs.GetObject("Sélectionnez le bloc dont vous voulez copier l'orientation", rs.filter.instance)
    
    if not ref_block:
        rs.SelectObjects(targets) # Restaurer la sélection si annulé
        return

    # 3. Calculer le plan du bloc
    matrix = rs.BlockInstanceXform(ref_block)
    new_plane = rg.Plane.WorldXY
    new_plane.Transform(matrix)

    # 4. Appliquer les changements
    rs.EnableRedraw(False)
    
    # Aligner le CPlane sur le bloc
    rs.ViewCPlane(None, new_plane)
    
    # Aligner le Gumball sur le CPlane
    rs.Command("_GumballAlignment _CPlane", False)
    
    # Resélectionner les objets initiaux pour mettre à jour le Gumball
    rs.SelectObjects(targets)
    
    rs.EnableRedraw(True)
    print("Gumball aligné sur l'orientation du bloc.")

if __name__ == "__main__":
    AlignGumballToSpecificBlock()

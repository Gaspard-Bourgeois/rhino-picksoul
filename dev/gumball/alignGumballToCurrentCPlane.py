import rhinoscriptsyntax as rs

def AlignGumballToCurrentCPlane():
    # Récupérer la sélection actuelle
    targets = rs.SelectedObjects()
    if not targets:
        print("Aucun objet sélectionné.")
        return

    # Commande Rhino pour changer l'alignement du Gumball
    rs.Command("_GumballAlignment _CPlane", False)
    
    # Petite astuce : on désélectionne et resélectionne pour 
    # forcer Rhino à redessiner le Gumball immédiatement.
    rs.EnableRedraw(False)
    rs.UnselectAllObjects()
    rs.SelectObjects(targets)
    rs.EnableRedraw(True)
    
    print("Gumball aligné sur le CPlane actuel.")

if __name__ == "__main__":
    AlignGumballToCurrentCPlane()

import rhinoscriptsyntax as rs

def AlignCPlaneAndPlanView():
    # 1. Sélection de l'objet ou de la face
    # On utilise la commande native car elle gère intelligemment 
    # le clic sur les sous-faces et l'orientation des blocs.
    rc = rs.Command("_CPlane _Object")
    
    if rc:
        # 2. Une fois le CPlane mis à jour, on lance la commande Plan
        # Le suffixe _Plan met la vue actuelle perpendiculaire au CPlane.
        rs.Command("_Plan")
        
        # Optionnel : Zoom sur l'objet pour mieux voir
        # rs.Command("_Zoom _Selected")
    else:
        print("Opération annulée ou aucun objet sélectionné.")

if __name__ == "__main__":
    AlignCPlaneAndPlanView()

"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 21/01/26
"""
import rhinoscriptsyntax as rs
import fnmatch

__commandname__ = "showLayer"

def RunCommand(is_interactive):
    # 1. Récupérer tous les noms de calques du document
    all_layers = rs.LayerNames()
    if not all_layers:
        return 0

    # 2. Demander la saisie à l'utilisateur
    # Exemple : "p1::l1, p1::l2, p2::*"
    prompt = "Calques à afficher (séparés par une virgule). Ex: p1::*, p2*, Layer01"
    user_input = rs.GetString(prompt)
    
    if not user_input:
        return 0

    # 3. Nettoyer la saisie : on sépare par les virgules et on enlève les espaces
    patterns = [p.strip() for p in user_input.split(",")]

    matched_layers = []

    # 4. Logique de recherche (Pattern Matching)
    for layer in all_layers:
        for pattern in patterns:
            # fnmatch gère nativement le caractère '*'
            if fnmatch.fnmatch(layer.lower(), pattern.lower()):
                matched_layers.append(layer)
                break # On passe au calque suivant dès qu'une correspondance est trouvée

    # 5. Application des modifications
    if matched_layers:
        rs.EnableRedraw(False) # Optimisation de l'affichage
        for layer in matched_layers:
            # Rendre le calque visible
            rs.LayerVisible(layer, True)
            
            # LOGIQUE ÉTENDUE : S'assurer que les parents sont aussi visibles
            parent = rs.ParentLayer(layer)
            while parent:
                rs.LayerVisible(parent, True)
                parent = rs.ParentLayer(parent)
        
        rs.EnableRedraw(True)
        print("Affichage de {} calque(s).".format(len(matched_layers)))
    else:
        print("Aucun calque ne correspond à votre recherche.")
        return 1

    return 0

if __name__ == "__main__":
    RunCommand(True)

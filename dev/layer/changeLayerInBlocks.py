"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 20/05/2026
"""
import rhinoscriptsyntax as rs
import fnmatch

def changeLayerInBlocks():
    
    all_layers = rs.LayerNames()
    if not all_layers:
        return 0
    
    objs = rs.GetObjects("Select block instances", 4096, preselect=True)
    if not objs:return 0
    
    layer = "Blocs"
    prompt = "Calque de destination"
    afficherListe = 'ListeDesCalques'
    user_input = rs.GetString(prompt, layer, [afficherListe])
    
    if not user_input:return 0
        
    if user_input == afficherListe:
        user_input = rs.GetLayer()

    if not user_input:return
    
    # 3. Nettoyer la saisie : on sépare par les virgules et on enlève les espaces
    patterns = [p.strip() for p in user_input.split(",")]

    matched_layer = None

    # 4. Logique de recherche (Pattern Matching)
    for layer in all_layers:
        for pattern in patterns:
            # fnmatch gère nativement le caractère '*'
            if fnmatch.fnmatch(layer.lower(), pattern.lower()):
                matched_layer = layer
                break
    
    if not matched_layer:
        user_input2 = rs.GetString('Calque introuvable, voulez vous créer "' + user_input + '"', "oui", ["oui", "non"])
        if user_input2 == "oui":
            rs.AddLayer(user_input)
            matched_layer = user_input
    
    if not matched_layer:return
    
    b_b_names = list(set([rs.BlockInstanceName(id) for id in objs]))
    done = []
    
    def BlockDrill(b_b_names):
        while True:
            if len (b_b_names) > 0 :
                b_name = b_b_names.pop()
            else: break
            
            done.append(b_name)
            temp = rs.BlockObjects(b_name)
            rs.ObjectLayer(temp, matched_layer)
            
            for tempId in temp:
                if rs.IsBlockInstance(tempId):
                    tempName = rs.BlockInstanceName(tempId)
                    if tempName not in b_b_names and tempName not in done:
                        b_b_names.append(tempName)
                        BlockDrill(b_b_names)
            
    BlockDrill(b_b_names)
    
    print('Objets déplacé sur ' + matched_layer)
    
if __name__ == "__main__": 
    changeLayerInBlocks()

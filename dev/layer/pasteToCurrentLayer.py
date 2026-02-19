import rhinoscriptsyntax as rs

def paste_to_current_layer():
    # Désactiver le rafraîchissement de l'écran pour éviter les scintillements
    rs.EnableRedraw(False)
    
    try:
        # Récupérer le calque actuel
        current_layer = rs.CurrentLayer()
        
        # Sauvegarder les calques existants et leur visibilité avant le collage
        layers_before = rs.LayerNames()
        layer_visibility = {layer: rs.LayerVisible(layer) for layer in layers_before}
        
        # Exécuter la commande Coller silencieusement
        rs.Command("_-Paste", echo=False)
        
        # Récupérer les objets qui viennent d'être créés (collés)
        pasted_objs = rs.LastCreatedObjects(select=True)
        
        if pasted_objs:
            # 1. Assigner tous les objets collés au calque actuel
            rs.ObjectLayer(pasted_objs, current_layer)
            
            # 2. Gérer l'affichage et le nettoyage des calques
            layers_after = rs.LayerNames()
            for layer in layers_after:
                if layer in layer_visibility:
                    # Restaurer la visibilité initiale si le collage l'a modifiée
                    if rs.LayerVisible(layer) != layer_visibility[layer]:
                        rs.LayerVisible(layer, layer_visibility[layer])
                else:
                    # Supprimer les calques importés par le collage qui sont maintenant vides
                    if layer != current_layer and rs.IsLayerEmpty(layer):
                        rs.DeleteLayer(layer)
            
            # 3. Sélectionner uniquement les objets fraîchement collés
            rs.UnselectAllObjects()
            rs.SelectObjects(pasted_objs)
            print("{} objet(s) collé(s) avec succès sur le calque actuel.".format(len(pasted_objs)))
        else:
            print("Le presse-papier est vide ou ne contient pas d'objets Rhino.")
            
    except Exception as e:
        print("Une erreur s'est produite lors du collage : {}".format(e))
        
    finally:
        # Toujours réactiver le rafraîchissement de l'écran à la fin
        rs.EnableRedraw(True)

if __name__ == "__main__":
    paste_to_current_layer()

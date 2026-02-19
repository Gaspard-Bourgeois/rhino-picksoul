import rhinoscriptsyntax as rs

def copy_or_paste_to_current_layer():
    # Récupérer le calque actuel
    current_layer = rs.CurrentLayer()
    
    # Récupérer les objets actuellement sélectionnés
    selected_objs = rs.SelectedObjects()
    
    # Désactiver le rafraîchissement de l'écran pour éviter les scintillements
    rs.EnableRedraw(False)
    
    try:
        if selected_objs:
            # CAS 1 : Objets sélectionnés (Copier sur le calque actuel)
            copied_objs = rs.CopyObjects(selected_objs)
            if copied_objs:
                rs.ObjectLayer(copied_objs, current_layer)
                rs.UnselectAllObjects()
                rs.SelectObjects(copied_objs)
                print("{} objet(s) copié(s) sur le calque actuel.".format(len(copied_objs)))
        else:
            # CAS 2 : Aucun objet sélectionné (Coller sur le calque actuel)
            
            # Sauvegarder les calques existants et leur visibilité
            layers_before = rs.LayerNames()
            layer_visibility = {layer: rs.LayerVisible(layer) for layer in layers_before}
            
            # Exécuter la commande Coller silencieusement
            rs.Command("_-Paste", echo=False)
            pasted_objs = rs.LastCreatedObjects(select=True)
            
            if pasted_objs:
                # Assigner les objets collés au calque actuel
                rs.ObjectLayer(pasted_objs, current_layer)
                
                # Gérer l'affichage et le nettoyage des calques
                layers_after = rs.LayerNames()
                for layer in layers_after:
                    if layer in layer_visibility:
                        # Restaurer la visibilité initiale si elle a été modifiée par le collage
                        if rs.LayerVisible(layer) != layer_visibility[layer]:
                            rs.LayerVisible(layer, layer_visibility[layer])
                    else:
                        # Supprimer les nouveaux calques importés par le collage (s'ils sont vides)
                        if layer != current_layer and rs.IsLayerEmpty(layer):
                            rs.DeleteLayer(layer)
                
                # Sélectionner les objets collés
                rs.UnselectAllObjects()
                rs.SelectObjects(pasted_objs)
                print("{} objet(s) collé(s) sur le calque actuel.".format(len(pasted_objs)))
            else:
                print("Le presse-papier est vide ou ne contient pas d'objets Rhino.")
                
    except Exception as e:
        print("Une erreur s'est produite : {}".format(e))
        
    finally:
        # Toujours réactiver le rafraîchissement de l'écran à la fin
        rs.EnableRedraw(True)

if __name__ == "__main__":
    copy_or_paste_to_current_layer()

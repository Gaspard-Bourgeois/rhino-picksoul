"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 05/01/26
"""
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def CopyBlockOrientation():
    # 1. Sélection des blocs à modifier (Cibles) avec gestion de la présélection
    targets = rs.GetObjects("Sélectionnez les blocs à réorienter", rs.filter.instance, preselect=True)
    if not targets: return
    
    # On vide la sélection pour choisir les sources proprement
    rs.UnselectAllObjects()
    
    # 2. Sélection du ou des blocs sources
    sources = rs.GetObjects("Sélectionnez le ou les blocs sources", rs.filter.instance, preselect=False)
    if not sources: return

    rs.EnableRedraw(False)
    
    num_sources = len(sources)
    
    for i, target_id in enumerate(targets):
        # Choix de la source selon l'ordre (boucle modulo)
        source_id = sources[i % num_sources]
        
        # Récupérer la matrice (Transform) de la source et de la cible
        # rs.BlockInstanceXform renvoie un objet Rhino.Geometry.Transform
        source_xform = rs.BlockInstanceXform(source_id)
        target_xform = rs.BlockInstanceXform(target_id)
        
        # Récupérer les points d'insertion
        source_pos = rs.BlockInstanceInsertPoint(source_id)
        target_pos = rs.BlockInstanceInsertPoint(target_id)
        
        # ÉTAPE A : Aligner l'orientation de la source sur la position de la cible
        # On déplace la matrice source vers la position cible
        translation_vec = target_pos - source_pos
        translation_xform = rg.Transform.Translation(translation_vec)
        final_target_xform = translation_xform * source_xform
        
        # ÉTAPE B : Calculer la transformation RELATIVE
        # Pour ne pas "ajouter" un déplacement, on calcule ce qu'il manque 
        # entre l'état actuel de la cible et l'état final désiré
        # Formule : Relative = Finale * Inverse(Actuelle)
        
        success, inverse_target_xform = target_xform.TryGetInverse()
        if success:
            relative_xform = final_target_xform * inverse_target_xform
            
            # Appliquer la transformation relative
            rs.TransformObject(target_id, relative_xform)
        
    rs.EnableRedraw(True)
    print("Succès : {} blocs réorientés sur place.".format(len(targets)))

if __name__ == "__main__":
    CopyBlockOrientation()

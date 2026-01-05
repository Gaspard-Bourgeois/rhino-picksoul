import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def CopyBlockOrientation():
    # 1. Sélection des blocs à modifier (Cibles)
    # preselect=True permet de récupérer les blocs déjà sélectionnés avant de lancer le script
    targets = rs.GetObjects("Sélectionnez les blocs à réorienter", rs.filter.instance, preselect=True)
    if not targets: return
    
    # 2. Sélection du ou des blocs sources
    # On désactive la présélection ici pour être sûr de choisir les sources après
    rs.UnselectAllObjects()
    sources = rs.GetObjects("Sélectionnez le ou les blocs sources", rs.filter.instance, preselect=False)
    if not sources: return

    rs.EnableRedraw(False)
    
    num_sources = len(sources)
    
    for i, target_id in enumerate(targets):
        # Choix de la source selon l'ordre (boucle modulo)
        source_id = sources[i % num_sources]
        
        # Récupérer la matrice de la source et son point d'insertion
        source_xform = rs.BlockInstanceXform(source_id)
        source_pos = rs.BlockInstanceInsertPoint(source_id)
        
        # Récupérer le point d'insertion de la cible
        target_pos = rs.BlockInstanceInsertPoint(target_id)
        
        # CALCUL DE LA MATRICE
        # On veut que la source soit déplacée de son point d'origine vers le point de la cible
        translation_vec = target_pos - source_pos
        translation_xform = rg.Transform.Translation(translation_vec)
        
        # La nouvelle matrice est la combinaison de l'orientation source + translation vers la cible
        final_xform = translation_xform * source_xform
        
        # APPLICATION DIRECTE
        # rs.BlockInstanceXform remplace l'ancienne matrice par la nouvelle
        # Cela évite de cumuler les déplacements
        rs.BlockInstanceXform(target_id, final_xform)
        
    rs.EnableRedraw(True)
    print("Succès : {} blocs réorientés.".format(len(targets)))

if __name__ == "__main__":
    CopyBlockOrientation()

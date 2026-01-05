import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def CopyBlockOrientation():
    # 1. Sélectionner d'abord les blocs à modifier (Cibles)
    targets = rs.GetObjects("Sélectionnez les blocs à réorienter", rs.filter.instance)
    if not targets: return
    
    # 2. Sélectionner ensuite le ou les blocs sources
    sources = rs.GetObjects("Sélectionnez le ou les blocs sources (orientations de référence)", rs.filter.instance)
    if not sources: return

    rs.EnableRedraw(False)
    
    num_sources = len(sources)
    
    for i, target_id in enumerate(targets):
        # 4. Parcours en boucle sur la liste des sources (modulo)
        source_id = sources[i % num_sources]
        
        # Obtenir les données de la source
        source_xform = rs.BlockInstanceXform(source_id)
        source_pos = rs.BlockInstanceInsertPoint(source_id)
        
        # Obtenir la position actuelle de la cible (pour la maintenir)
        target_pos = rs.BlockInstanceInsertPoint(target_id)
        
        # 3. Calcul de la nouvelle matrice :
        # On prend la matrice de la source (orientation + échelle)
        # On calcule le vecteur pour déplacer le point d'insertion de la source vers celui de la cible
        translation_vec = target_pos - source_pos
        translation_xform = rg.Transform.Translation(translation_vec)
        
        # Le produit des matrices applique l'orientation de la source au point de la cible
        final_xform = translation_xform * source_xform
        
        # Appliquer la transformation (remplace l'ancienne matrice)
        rs.TransformObject(target_id, final_xform, False)
        
    rs.EnableRedraw(True)
    print("Réorientation de {} blocs terminée.".format(len(targets)))

if __name__ == "__main__":
    CopyBlockOrientation()

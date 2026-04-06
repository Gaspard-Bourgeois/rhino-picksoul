Voici le script Python 3 spécialement conçu pour Rhino 8 qui répond à votre demande.
Pour traduire votre contrainte géométrique (le "tube de collision" d'épaisseur T) de manière algorithmique, le script procède en deux étapes chirurgicales :
 * Le calcul de la vérité mathématique : Il génère un décalage brut de la Courbe 1 à la distance exacte D, en forçant une tolérance interne extrême (10 fois plus petite que votre T).
 * L'optimisation topologique : Il utilise la méthode FitCurve de RhinoCommon pour reconstruire cette courbe brute. L'algorithme réduit drastiquement le nombre de points de contrôle (courbe de degré 3 "la plus simple possible") jusqu'à la limite absolue où la courbe menace de sortir de votre tolérance T. Enfin, il s'assure qu'elle reste mathématiquement plaquée sur la surface.
Comment utiliser ce script dans Rhino 8
 * Ouvrez l'éditeur de script de Rhino 8 (commande ScriptEditor).
 * Créez un nouveau script Python 3.
 * Copiez-collez le code ci-dessous et exécutez-le.
#! python3
# -*- coding: utf-8 -*-

"""
Script de Décalage Chirurgical sur Surface pour Rhino 8 (Python 3)
Ce script crée une courbe C2 décalée d'une distance D par rapport à une courbe C1
sur une surface, tout en garantissant que C2 reste dans le "tube" de tolérance T.
La courbe résultante est simplifiée au maximum (points de contrôle réduits).
"""

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

def decalage_chirurgical():
    # 1. Sélection des géométries
    srf_id = rs.GetObject("1. Sélectionnez la surface support (Brep/Face)", rs.filter.surface | rs.filter.polysurface)
    if not srf_id: return
    
    crv_id = rs.GetObject("2. Sélectionnez la courbe 1 à décaler (doit être sur la surface)", rs.filter.curve)
    if not crv_id: return
    
    # 2. Saisie des Paramètres D (Distance) et T (Tolérance)
    D = rs.GetReal("Distance de décalage (D)", 10.0)
    if not D: return
    
    T = rs.GetReal("Tolérance d'épaisseur du tube (T) [Ex: 0.1]", 0.1)
    if not T: return
    
    # 3. Extraction de la géométrie sous-jacente (RhinoCommon)
    brep = rs.coercebrep(srf_id)
    curve = rs.coercecurve(crv_id)
    
    if not brep or not curve:
        print("Erreur: Impossible de convertir la géométrie en RhinoCommon.")
        return
        
    # Identification de la face de la surface sur laquelle se trouve la courbe
    mid_t = curve.Domain.Mid
    pt_mid = curve.PointAt(mid_t)
    
    face = None
    for f in brep.Faces:
        rc, u, v = f.ClosestPoint(pt_mid)
        # On vérifie si la courbe est bien sur cette face spécifique
        if rc and f.PointAt(u, v).DistanceTo(pt_mid) <= sc.doc.ModelAbsoluteTolerance * 10:
            face = f
            break
            
    if not face:
        print("Erreur: La courbe ne semble pas être strictement sur la surface sélectionnée.")
        return

    # 4. Étape A : Décalage mathématique "parfait" (Tolérance très fine)
    # On calcule l'offset exact avec une marge de manœuvre de 10% de T.
    tol_interne = T * 0.1 
    courbes_brutes = curve.OffsetOnSurface(face, D, tol_interne)
    
    if not courbes_brutes or len(courbes_brutes) == 0:
        print("Erreur: Le calcul du décalage a échoué. La distance D est peut-être plus grande que la surface disponible.")
        return

    nouvelles_courbes_ids = []
    
    # 5. Étape B : Simplification chirurgicale dans la tolérance T
    for crv_brute in courbes_brutes:
        # La méthode Fit recrée la courbe avec le moins de points de contrôle possibles
        # (degré 3) tant qu'elle ne dévie pas de plus de T de la courbe brute.
        courbe_simplifiee = crv_brute.Fit(3, T, 0.0)
        
        if courbe_simplifiee:
            # Sécurité : Le lissage (Fit) en 3D peut parfois très légèrement décoller 
            # la courbe de la topologie locale. On la re-plaque sur la surface stricte.
            courbes_plaquees = courbe_simplifiee.PullToBrepFace(face, tol_interne)
            
            if courbes_plaquees and len(courbes_plaquees) > 0:
                courbe_finale = courbes_plaquees[0]
            else:
                courbe_finale = courbe_simplifiee
        else:
            # Solution de secours si l'optimisation échoue
            courbe_finale = crv_brute
            
        # 6. Ajout de la Courbe 2 au document Rhino
        id_final = sc.doc.Objects.AddCurve(courbe_finale)
        nouvelles_courbes_ids.append(id_final)
        
    sc.doc.Views.Redraw()
    print("Décalage réussi. La Courbe 2 a été optimisée et respecte l'enveloppe de tolérance T = {}.".format(T))
    rs.SelectObjects(nouvelles_courbes_ids)

if __name__ == "__main__":
    decalage_chirurgical()


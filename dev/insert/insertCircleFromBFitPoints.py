"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg


def best_fit_circle_custom():
    # 1. Sélection des points
    point_ids = rs.GetObjects("Sélectionnez les points pour le cercle moyen", 1, preselect=True)
    if not point_ids: return


    points = [rs.PointCoordinates(id) for id in point_ids]
    count = len(points)
    
    if count < 3:
        print("Erreur : Sélectionnez au moins 3 points.")
        return


    # 2. Calcul du cercle par Best Fit
    rc, circle = rg.Circle.TryFitCircleToPoints(points)


    if not rc:
        print("Erreur : Impossible de calculer un cercle.")
        return


    # 3. Création de l'objet dans Rhino
    circle_id = rs.AddCircle(circle.Plane, circle.Radius)


    # 4. Calcul de l'erreur moyenne de distance au cercle
    # On mesure la distance réelle entre le point et sa projection sur le cercle
    total_distance_error = 0
    for pt in points:
        # Trouver le paramètre du point le plus proche sur la courbe du cercle
        closest_pt = circle.ClosestPoint(pt)
        # closest_pt = circle.PointAt(t)
        
        # Distance 3D entre le point d'origine et la circonférence
        dist = pt.DistanceTo(closest_pt)
        total_distance_error += dist


    avg_dist_error = total_distance_error / count


    # 5. Affichage des résultats
    print("--- Rapport Best-Fit Circle ---")
    print("Points traités : {}".format(count))
    print("Diamètre : {:.4f} mm".format(circle.Radius * 2))
    print("Centre : {:.3f}, {:.3f}, {:.3f}".format(circle.Center.X, circle.Center.Y, circle.Center.Z))
    print("Erreur moyenne de distance au cercle : {:.4f} mm".format(avg_dist_error))


    if circle_id:
        rs.SelectObject(circle_id)


if __name__ == "__main__":
    best_fit_circle_custom()


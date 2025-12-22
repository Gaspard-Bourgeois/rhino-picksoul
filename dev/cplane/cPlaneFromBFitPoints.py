"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import math


def update_best_fit_cplane():
    # 1. Sélection des points
    point_ids = rs.GetObjects("Sélectionnez les points", 1, preselect=True)
    if not point_ids: return


    points = [rs.PointCoordinates(id) for id in point_ids]
    count = len(points)
    
    if count < 3:
        print("Erreur : Sélectionnez au moins 3 points.")
        return


    # 2. Calcul du Centroïde (Moyenne des positions)
    sum_x = sum(p.X for p in points)
    sum_y = sum(p.Y for p in points)
    sum_z = sum(p.Z for p in points)
    centroid = rg.Point3d(sum_x/count, sum_y/count, sum_z/count)


    # 3. Calcul du plan moyen (Best Fit)
    # On calcule d'abord le plan, puis on force son origine au centroïde
    plane = rs.PlaneFitFromPoints(points)
    if not plane: 
        print("Erreur : Calcul du plan impossible.")
        return
    
    # On replace l'origine du plan précisément sur le centroïde calculé
    plane.Origin = centroid


    # 4. Calcul des statistiques
    total_dist_to_plane = 0
    total_dist_to_origin = 0


    for pt in points:
        # Distance perpendiculaire au plan
        total_dist_to_plane += abs(rs.DistanceToPlane(plane, pt))
        # Distance directe (Euclidienne) à l'origine (centroïde)
        total_dist_to_origin += rs.Distance(pt, centroid)


    avg_error_plane = total_dist_to_plane / count
    avg_dist_to_origin = total_dist_to_origin / count


    # 5. Mise à jour de l'interface
    view = rs.CurrentView()
    rs.ViewCPlane(view, plane)


    # 6. Affichage des résultats
    print("--- Rapport Best-Fit CPlane ---")
    print("Points traités : {}".format(count))
    print("Origine du CPlane : {:.3f}, {:.3f}, {:.3f}".format(centroid.X, centroid.Y, centroid.Z))
    print("Erreur moyenne de projection : {:.4f} mm".format(avg_error_plane))
    print("Distance moyenne des points à l'origine : {:.4f} mm".format(avg_dist_to_origin))


if __name__ == "__main__":
    update_best_fit_cplane()


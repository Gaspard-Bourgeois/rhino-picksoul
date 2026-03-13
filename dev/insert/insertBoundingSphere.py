import rhinoscriptsyntax as rs
import random
import math
import sys

# Augmentation de la limite de récursivité pour l'algorithme de Welzl sur de gros nuages de points
sys.setrecursionlimit(5000)

# ==========================================
# FONCTIONS MATHÉMATIQUES ET WELZL (EXACT)
# ==========================================

def distance(p1, p2):
    return math.sqrt((p1.X-p2.X)**2 + (p1.Y-p2.Y)**2 + (p1.Z-p2.Z)**2)

def get_circle_2pts(p1, p2):
    center = rs.PointDivide(rs.PointAdd(p1, p2), 2)
    return center, distance(p1, p2) / 2.0

def get_circle_3pts(p1, p2, p3):
    v1 = rs.PointSubtract(p2, p1)
    v2 = rs.PointSubtract(p3, p1)
    v1v1 = rs.VectorDotProduct(v1, v1)
    v2v2 = rs.VectorDotProduct(v2, v2)
    v1v2 = rs.VectorDotProduct(v1, v2)
    det = 2.0 * (v1v1 * v2v2 - v1v2 * v1v2)
    if abs(det) < 1e-9: return get_circle_2pts(p1, p2)
    s1 = (v2v2 * v1v1 - v1v2 * v2v2) / det
    s2 = (v1v1 * v2v2 - v1v2 * v1v1) / det
    center = rs.PointAdd(p1, rs.PointAdd(rs.VectorScale(v1, s1), rs.VectorScale(v2, s2)))
    return center, distance(center, p1)

def get_sphere_4pts(p1, p2, p3, p4):
    try:
        matrix = [
            [p2.X-p1.X, p2.Y-p1.Y, p2.Z-p1.Z],
            [p3.X-p1.X, p3.Y-p1.Y, p3.Z-p1.Z],
            [p4.X-p1.X, p4.Y-p1.Y, p4.Z-p1.Z]
        ]
        b = [
            0.5 * (p2.X**2 + p2.Y**2 + p2.Z**2 - (p1.X**2 + p1.Y**2 + p1.Z**2)),
            0.5 * (p3.X**2 + p3.Y**2 + p3.Z**2 - (p1.X**2 + p1.Y**2 + p1.Z**2)),
            0.5 * (p4.X**2 + p4.Y**2 + p4.Z**2 - (p1.X**2 + p1.Y**2 + p1.Z**2))
        ]
        center = rs.SolveLinearSystem(matrix, b)
        if center:
            pt_center = rs.coerce3dpoint(center)
            return pt_center, distance(pt_center, p1)
    except:
        pass
    return get_circle_3pts(p1, p2, p3)

def welzl(points, boundary, n):
    if n == 0 or len(boundary) == 4:
        if not boundary: return rs.coerce3dpoint([0,0,0]), 0
        if len(boundary) == 1: return boundary[0], 0
        if len(boundary) == 2: return get_circle_2pts(boundary[0], boundary[1])
        if len(boundary) == 3: return get_circle_3pts(boundary[0], boundary[1], boundary[2])
        if len(boundary) == 4: return get_sphere_4pts(boundary[0], boundary[1], boundary[2], boundary[3])

    p = points[n-1]
    center, r = welzl(points, boundary, n-1)

    if distance(center, p) <= r + 1e-9:
        return center, r

    return welzl(points, boundary + [p], n-1)


# ==========================================
# FONCTIONS D'EXTRACTION ET DE TRAITEMENT
# ==========================================

def extraire_points(obj_ids):
    pts = []
    rs.EnableRedraw(False)
    for obj in obj_ids:
        if rs.IsPoint(obj): 
            pts.append(rs.PointCoordinates(obj))
        elif rs.IsPointCloud(obj): 
            pts.extend(rs.PointCloudPoints(obj))
        elif rs.IsMesh(obj): 
            pts.extend(rs.MeshVertices(obj))
        elif rs.IsCurve(obj): 
            pts.extend(rs.CurvePoints(obj) or [])
        elif rs.IsSurface(obj) or rs.IsPolysurface(obj):
            # Création d'un maillage de rendu temporaire pour extraire précisément l'enveloppe
            meshes = rs.ExtractObjectMesh(obj)
            if meshes:
                for m in meshes: pts.extend(rs.MeshVertices(m))
                rs.DeleteObjects(meshes) # Nettoyage
    rs.EnableRedraw(True)
    
    # Supprimer les doublons pour alléger le calcul
    return rs.CullDuplicatePoints(pts, 0.001) if pts else []

def main():
    obj_ids = rs.GetObjects("Sélectionnez les objets à englober", preselect=True)
    if not obj_ids: return

    # --- OPTIONS UTILISATEUR ---
    methode = rs.GetString("Choisissez la méthode de calcul", "Welzl", ["Welzl", "BoundingBox"])
    seuil_filtre = 0.7 
    if methode == "Welzl":
        seuil_filtre = rs.GetReal("Seuil du filtre BBox (0.0 = aucun filtre, 0.8 = ne garde que les points très extérieurs)", 0.7, 0.0, 0.99)

    rs.EnableRedraw(False)

    if methode == "BoundingBox":
        # Méthode Rapide Bounding Box
        bbox = rs.BoundingBox(obj_ids)
        c_x = (bbox[0].X + bbox[6].X) / 2.0
        c_y = (bbox[0].Y + bbox[6].Y) / 2.0
        c_z = (bbox[0].Z + bbox[6].Z) / 2.0
        center = rs.coerce3dpoint([c_x, c_y, c_z])
        radius = rs.Distance(center, bbox[0])
        
        sp_id = rs.AddSphere(center, radius)
        pt_id = rs.AddPoint(center)
        grp_sphere = rs.AddGroup("Sphere_BoundingBox")
        rs.AddObjectsToGroup([sp_id, pt_id], grp_sphere)
        
        print("--- Sphère via BoundingBox créée ---")
        
    elif methode == "Welzl":
        # 1. Extraction des points
        tous_les_points = extraire_points(obj_ids)
        if not tous_les_points:
            print("Erreur : Aucun point n'a pu être extrait de la sélection.")
            return

        # 2. Filtrage via Bounding Box globale des points
        bbox = rs.BoundingBox(tous_les_points)
        c_x = (bbox[0].X + bbox[6].X) / 2.0
        c_y = (bbox[0].Y + bbox[6].Y) / 2.0
        c_z = (bbox[0].Z + bbox[6].Z) / 2.0
        center_bbox = rs.coerce3dpoint([c_x, c_y, c_z])

        max_dist = max([distance(p, center_bbox) for p in tous_les_points])
        limite_distance = max_dist * seuil_filtre

        pts_ext = []
        pts_int = []

        # Tri des points extérieurs/intérieurs
        for p in tous_les_points:
            if distance(p, center_bbox) >= limite_distance:
                pts_ext.append(p)
            else:
                pts_int.append(p)
                
        # Sécurité : s'il n'y a pas assez de points extérieurs (seuil trop haut)
        if len(pts_ext) < 4:
            pts_ext = tous_les_points
            pts_int = []

        # 3. Création des Groupes de points
        grp_int_name = rs.AddGroup("Welzl_Points_Interieurs")
        if pts_int:
            int_ids = rs.AddPoints(pts_int)
            rs.ObjectColor(int_ids, [150, 150, 150]) # Gris
            rs.AddObjectsToGroup(int_ids, grp_int_name)

        grp_ext_name = rs.AddGroup("Welzl_Points_Exterieurs")
        if pts_ext:
            ext_ids = rs.AddPoints(pts_ext)
            rs.ObjectColor(ext_ids, [255, 0, 0]) # Rouge
            rs.AddObjectsToGroup(ext_ids, grp_ext_name)

        # 4. Exécution de Welzl sur les points extérieurs uniquement
        # Le mélange (shuffle) est indispensable pour éviter d'exploser la limite de récursivité
        random.shuffle(pts_ext)
        center, radius = welzl(pts_ext, [], len(pts_ext))

        # 5. Création de la Sphère et de son centre
        sp_id = rs.AddSphere(center, radius)
        pt_id = rs.AddPoint(center)
        grp_sphere_name = rs.AddGroup("Welzl_Sphere_Resultat")
        rs.AddObjectsToGroup([sp_id, pt_id], grp_sphere_name)
        
        rs.SelectObjects([sp_id, pt_id])
        
        print("--- Résultat Welzl ---")
        print("Points filtrés : {} extérieurs / {} intérieurs".format(len(pts_ext), len(pts_int)))

    rs.EnableRedraw(True)
    if center and radius:
        print("Centre : X={:.3f}, Y={:.3f}, Z={:.3f}".format(center.X, center.Y, center.Z))
        print("Diamètre : {:.3f}".format(radius * 2.0))


if __name__ == "__main__":
    main()

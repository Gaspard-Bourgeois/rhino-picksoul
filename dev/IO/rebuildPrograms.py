import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import re

def get_transform_between_curves(crv_orig, crv_copy):
    """Calcule la transformation (translation + rotation) entre deux courbes."""
    pts_orig = rs.PolylineVertices(crv_orig)
    pts_copy = rs.PolylineVertices(crv_copy)
    if not pts_orig or not pts_copy or len(pts_orig) != len(pts_copy):
        return None
    # Calcul basé sur le premier segment pour la transformation rigide
    return rg.Transform.PlaneToPlane(rg.Plane(pts_orig[0], rg.Vector3d.ZAxis), 
                                     rg.Plane(pts_copy[0], rg.Vector3d.ZAxis))

def analyze_and_rebuild_from_text():
    # 1. Sélection des objets programmes (Textes avec type=program)
    all_texts = rs.ObjectsByType(rs.filter.instance)
    prog_texts = [t for t in all_texts if rs.GetUserText(t, "type") == "program"]
    
    if not prog_texts:
        rs.MessageBox("Aucun texte de type 'program' trouvé.")
        return

    selected_progs = rs.MultiListBox([rs.ObjectName(t) or str(t) for t in prog_texts], "Sélectionner les programmes à traiter")
    if not selected_progs: return

    copy_order = rs.GetString("Ordre des copies", "last", ["first", "last"])
    if not copy_order: return

    # 2. Dictionnaire global des objets présents dans le document pour recherche rapide
    all_objs = rs.AllObjects()
    obj_map = {} # { uuid_origin : [list of current rhino uuids] }
    for o in all_objs:
        u_orig = rs.GetUserText(o, "uuid_origin")
        if u_orig:
            if u_orig not in obj_map: obj_map[u_orig] = []
            obj_map[u_orig].append(o)

    # 3. Traitement de chaque programme sélectionné
    for prog_name in selected_progs:
        prog_obj = [t for t in prog_texts if (rs.ObjectName(t) or str(t)) == prog_name][0]
        
        # Récupération de l'ordre des courbes depuis le texte
        # On suppose des clés type Crv_0, Crv_1...
        keys = sorted([k for k in rs.GetUserText(prog_obj) if k.startswith("Crv_")], 
                      key=lambda x: int(x.split("_")[1]))
        
        ordered_curve_origins = [rs.GetUserText(prog_obj, k) for k in keys]
        
        new_sequence_data = [] # Liste de {'pos': Point, 'arcon': bool, 'type': move}
        
        for u_crv_orig in ordered_curve_origins:
            if u_crv_orig not in obj_map: continue # Courbe supprimée
            
            # Récupérer l'original et ses copies
            current_curves = obj_map[u_crv_orig]
            # Trier : Original en premier si 'last', copies en premier si 'first'
            current_curves.sort(key=lambda x: str(x) != u_crv_orig, reverse=(copy_order == "first"))

            for crv in current_curves:
                # Vérifier si c'est une copie déplacée (ou l'original)
                # (Ici on traite toutes les occurrences trouvées dans Rhino)
                
                is_arcon = "ARCON" in (rs.ObjectName(crv) or "")
                
                # Récupérer les points/instances depuis les UserStrings de l'ORIGINAL 
                # car la copie peut ne pas avoir conservé les clés Pt_0, etc.
                crv_metadata_source = rs.coerceguid(u_crv_orig)
                pt_keys = sorted([k for k in rs.GetUserText(crv_metadata_source) if k.startswith("Pt_")],
                                 key=lambda x: int(x.split("_")[1]))
                
                actual_vertices = rs.PolylineVertices(crv)
                if not actual_vertices: continue

                for i, k_pt in enumerate(pt_keys):
                    if i >= len(actual_vertices): break
                    
                    inst_idx_name = rs.GetUserText(crv_metadata_source, k_pt)
                    # Chercher l'instance correspondante dans le document
                    # Logique : On cherche parmi les instances ayant cet index
                    found_pt = actual_vertices[i]
                    
                    new_sequence_data.append({
                        'pos': found_pt,
                        'arcon': is_arcon,
                        'name_orig': inst_idx_name
                    })

        # 4. Reconstruction physique
        if not new_sequence_data: continue

        # Nettoyage des anciennes instances pour ce programme spécifique
        # (Optionnel : vous pouvez choisir de créer un nouveau calque)
        new_lyr = rs.AddLayer("REBUILT_" + prog_name)
        traj_lyr = rs.AddLayer("trajs_arcon_arcof", parent=new_lyr)
        
        # Recréation des blocs Pose aux nouvelles positions
        final_instances = []
        for i, data in enumerate(new_sequence_data):
            # Insertion d'un nouveau bloc à la position analysée
            new_inst = rs.InsertBlock("Pose", data['pos'])
            rs.ObjectName(new_inst, str(i))
            rs.ObjectLayer(new_inst, new_lyr)
            rs.SetUserText(new_inst, "uuid_origin", str(new_inst))
            final_instances.append(new_inst)

        # Recréation des courbes ARCON / ARCOF
        rs.CurrentLayer(traj_lyr)
        if len(new_sequence_data) > 1:
            temp_pts = [new_sequence_data[0]['pos']]
            last_state = new_sequence_data[0]['arcon']
            start_idx = 0

            def build_pl(pts, state, s_idx, e_idx):
                if len(pts) < 2: return
                pid = rs.AddPolyline(pts)
                pref = "ARCON" if state else "ARCOF"
                rs.ObjectName(pid, "{} {}-{}".format(pref, s_idx, e_idx))
                rs.ObjectColor(pid, (255,0,0) if state else (150,150,150))
                rs.SetUserText(pid, "uuid_origin", str(pid))

            for i in range(1, len(new_sequence_data)):
                if new_sequence_data[i]['arcon'] != last_state:
                    build_pl(temp_pts, last_state, start_idx, i-1)
                    temp_pts = [new_sequence_data[i-1]['pos'], new_sequence_data[i]['pos']]
                    start_idx = i - 1
                    last_state = new_sequence_data[i]['arcon']
                else:
                    temp_pts.append(new_sequence_data[i]['pos'])
            build_pl(temp_pts, last_state, start_idx, len(new_sequence_data)-1)

    rs.EnableRedraw(True)
    rs.MessageBox("Reconstruction terminée avec succès.")

if __name__ == "__main__":
    analyze_and_rebuild_from_text()

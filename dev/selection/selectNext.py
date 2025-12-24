import rhinoscriptsyntax as rs
import re

def select_next_element():
    # Récupérer les objets actuellement sélectionnés
    selected_objects = rs.GetObjects("Sélectionnez les éléments actuels", preselect=True)
    
    if not selected_objects:
        print("Aucune sélection active.")
        return

    next_objects_to_select = []
    
    # On désélectionne tout pour ne garder que les "suivants" à la fin
    rs.UnselectAllObjects()

    for obj_id in selected_objects:
        obj_name = rs.ObjectName(obj_id)
        obj_layer = rs.ObjectLayer(obj_id)
        
        if not obj_name:
            continue

        # --- CAS 1 : C'est une POSE (Instance de bloc nommée par un chiffre "0", "1", "8"...) ---
        # On cherche un nombre entier simple
        if obj_name.isdigit():
            current_idx = int(obj_name)
            next_idx = current_idx + 1
            next_name = str(next_idx)
            
            # Chercher l'objet sur le même calque qui a ce nom
            # On récupère tous les objets du calque pour filtrer (plus rapide que AllObjects)
            layer_objs = rs.ObjectsByLayer(obj_layer)
            found = False
            if layer_objs:
                for cand_id in layer_objs:
                    if rs.ObjectName(cand_id) == next_name:
                        next_objects_to_select.append(cand_id)
                        found = True
                        break # On a trouvé le suivant, on passe à l'objet sélectionné suivant
            
            if not found:
                print("Pose suivante '{}' introuvable sur le calque '{}'.".format(next_name, obj_layer))

        # --- CAS 2 : C'est une COURBE (Nommée "ARCON X-Y" ou "ARCOF X-Y") ---
        # On cherche le pattern "TEXTE DEBUT-FIN" (ex: ARCON 2-3)
        else:
            # Regex pour capturer le dernier chiffre (l'index de fin)
            # Accepte "ARCON 2-3", "ARCOF 8-9", "NomComplexe 10-11"
            match = re.search(r"(\d+)-(\d+)$", obj_name)
            
            if match:
                start_idx = int(match.group(1))
                end_idx = int(match.group(2))
                
                # La logique : la courbe actuelle finit à 'end_idx'.
                # La courbe SUIVANTE doit commencer par 'end_idx'.
                # Son nom devrait finir par "end_idx-NOUVEAU_FIN"
                # Pattern recherché : "quelquechose end_idx-..."
                
                target_start_str = "{}-".format(end_idx)
                
                layer_objs = rs.ObjectsByLayer(obj_layer)
                found = False
                
                if layer_objs:
                    for cand_id in layer_objs:
                        cand_name = rs.ObjectName(cand_id)
                        if cand_name and cand_name != obj_name: # Ne pas se re-sélectionner soi-même
                            # Vérifie si le nom contient " 3-" (ex: "ARCOF 3-4")
                            # On utilise un regex ou un check string simple
                            # Pour être robuste, on re-parse le nom du candidat
                            cand_match = re.search(r"(\d+)-(\d+)$", cand_name)
                            if cand_match:
                                cand_start = int(cand_match.group(1))
                                if cand_start == end_idx:
                                    next_objects_to_select.append(cand_id)
                                    found = True
                                    # Note: On ne 'break' pas ici car il pourrait théoriquement y avoir 
                                    # une bifurcation (rare dans un JBI linéaire mais possible), 
                                    # mais pour un script simple, on peut breaker si on veut juste le premier trouvé.
                                    break 
                
                if not found:
                    print("Courbe suivante commençant par l'index {} introuvable.".format(end_idx))
            else:
                print("L'objet '{}' ne respecte pas le format attendu (Index ou X-Y).".format(obj_name))

    # Sélection finale
    if next_objects_to_select:
        rs.SelectObjects(next_objects_to_select)
        print("{} éléments suivants sélectionnés.".format(len(next_objects_to_select)))
    else:
        print("Aucun élément suivant trouvé.")

if __name__ == "__main__":
    select_next_element()
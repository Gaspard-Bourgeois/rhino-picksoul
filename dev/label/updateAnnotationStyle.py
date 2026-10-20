"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.1
Date: 20/10/2026
"""
# -*- coding: utf-8 -*-
import re
import Rhino
import rhinoscriptsyntax as rs

# Constante : hauteur de texte des styles créés automatiquement (mm)
HAUTEUR_TEXTE_MM = 2.5

def parse_style_mm(name):
    """Retourne l'échelle (float) si le nom est du type mm10, mm5, mm2.5... sinon None."""
    m = re.match(r"^mm(\d+(?:[.,]\d+)?)$", name.strip(), re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "."))
    return None

def creer_style_mm(name, echelle):
    """Crée le style 'name' avec hauteur de texte constante et échelle de texte donnée."""
    rs.AddDimStyle(name)

    doc = Rhino.RhinoDoc.ActiveDoc
    existant = doc.DimStyles.FindName(name)
    if existant is None:
        print("Impossible de créer le style '{}'.".format(name))
        return

    # On modifie une copie du style puis on la réinjecte dans le document
    ds = Rhino.DocObjects.DimensionStyle()
    ds.TextHeight = HAUTEUR_TEXTE_MM
    ds.DimensionScale = echelle
    ok = doc.DimStyles.Modify(ds, existant.Id, False)

    print("Style '{}' créé (hauteur {} mm, échelle {}) : {}".format(
        name, HAUTEUR_TEXTE_MM, echelle, "OK" if ok else "échec de la modification"))

def update_annotations_with_options():
    # 1. Récupérer les styles et le style actuel
    styles = rs.DimStyleNames()
    if not styles:
        print("Aucun style d'annotation trouvé.")
        return

    current_default = rs.CurrentDimStyle()
    options = [s.replace(" ", "_") for s in styles if s != None]

    # 2. Demander le style via la barre de commande
    msg = "Style actuel : {}. Choisir le nouveau style (ou saisir mmXX)".format(current_default)
    res = rs.GetString(msg, current_default, options)

    if res is None: return # Annulation

    # Retrouver le nom original du style
    chosen_style = None
    if res in styles:
        chosen_style = res

    # 2b. Style inexistant : création automatique si le nom est du type mmXX
    if not chosen_style:
        echelle = parse_style_mm(res)
        if echelle is None:
            print("Style invalide.")
            return
        chosen_style = res.strip()
        creer_style_mm(chosen_style, echelle)

    # 3. Traiter la sélection
    selected_objs = rs.SelectedObjects()

    if selected_objs:
        rs.EnableRedraw(False)
        anno_count = 0
        for obj_id in selected_objs:
            # 512 = Code pour tous les objets d'annotation (Cotes, Textes, Leaders)
            if rs.ObjectType(obj_id) == 512:
                rs.DimensionStyle(obj_id, chosen_style)
                anno_count += 1
        rs.EnableRedraw(True)

        if anno_count > 0:
            print("Succès : {} annotation(s) mise(s) à jour sur '{}'.".format(anno_count, chosen_style))
        else:
            print("Aucune annotation trouvée dans la sélection.")
    else:
        print("Aucune sélection. Modification du style par défaut uniquement.")

    # 4. Définir comme style par défaut
    rs.CurrentDimStyle(chosen_style)
    print("Style par défaut défini sur : {}".format(chosen_style))

if __name__ == "__main__":
    update_annotations_with_options()

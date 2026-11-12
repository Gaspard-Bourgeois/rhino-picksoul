# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import os
import re
import unicodedata

def slugify(value):
    """Nettoie le nom de fichier pour éviter les erreurs système."""
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

class DisplayModeContext(object):
    """Passe temporairement toutes les vues en filaire, puis restaure leur mode d'affichage."""
    def __init__(self, english_name="Wireframe"):
        self.english_name = english_name
        self.saved = []  # liste de (vue, mode d'origine)

    def _find_mode(self):
        # Recherche par nom anglais : fonctionne quelle que soit la langue de Rhino
        for m in Rhino.Display.DisplayModeDescription.GetDisplayModes():
            if m.EnglishName == self.english_name:
                return m
        return None

    def __enter__(self):
        mode = self._find_mode()
        if mode is None:
            print("Mode d'affichage '{}' introuvable, affichage inchangé.".format(self.english_name))
            return self
        for view in sc.doc.Views:
            vp = view.ActiveViewport
            self.saved.append((view, vp.DisplayMode))
            vp.DisplayMode = mode
            view.Redraw()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for view, original in self.saved:
            try:
                view.ActiveViewport.DisplayMode = original
                view.Redraw()
            except Exception:
                pass  # vue fermée entre-temps
        return False

class LayerStateContext(object):
    """Gestionnaire de contexte pour sauvegarder/restaurer l'état des calques."""
    def __init__(self):
        self.layers = rs.LayerNames()
        self.states = {}

    def __enter__(self):
        if self.layers:
            for layer in self.layers:
                self.states[layer] = {
                    "visible": rs.LayerVisible(layer),
                    "locked": rs.LayerLocked(layer)
                }
                # Déverrouiller et rendre visible pour permettre l'export
                rs.LayerLocked(layer, False)
                rs.LayerVisible(layer, True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for layer, state in self.states.items():
            if rs.IsLayer(layer):
                rs.LayerVisible(layer, state["visible"])
                rs.LayerLocked(layer, state["locked"])
        return False

class RhinoExportManager:
    def __init__(self, export_path):
        self.export_path = export_path
        self.block_layer_map = self._map_blocks_to_layers()

    def _map_blocks_to_layers(self):
        """Crée un dictionnaire associant chaque définition de bloc aux calques qu'elle contient."""
        mapping = {}
        block_names = rs.BlockNames()

        if block_names:
            for block_name in block_names:
                objs = rs.BlockObjects(block_name)
                if objs:
                    layers = {rs.ObjectLayer(o) for o in objs if o}
                    mapping[block_name] = layers
        return mapping

    def get_blocks_using_layer(self, layer_name):
        """Trouve les noms de blocs qui contiennent des objets sur ce calque."""
        return [bn for bn, layers in self.block_layer_map.items() if layer_name in layers]

    def export_layer(self, layer_name, include_children=True, include_blocks=True):
        rs.UnselectAllObjects()

        # 1. Sélection des objets directs
        layers_to_process = [layer_name]
        if include_children:
            children = rs.LayerChildren(layer_name)
            if children: layers_to_process.extend(children)

        for l in layers_to_process:
            if rs.IsLayer(l):
                rs.ObjectsByLayer(l, True)

        # 2. Sélection des instances de blocs liées
        if include_blocks:
            for l in layers_to_process:
                related_blocks = self.get_blocks_using_layer(l)
                for bn in related_blocks:
                    instances = rs.BlockInstances(bn)
                    if instances: rs.SelectObjects(instances)

        if rs.SelectedObjects():
            # Nettoyage du nom : remplace '::' par '_' pour la hiérarchie
            clean_name = layer_name.replace("::", "_")
            file_name = "{}.3dm".format(slugify(clean_name))
            full_path = os.path.join(self.export_path, file_name)

            # Export
            rs.Command('-_Export "{}" _Enter'.format(full_path), echo=False)
            print("Exporté : {}".format(file_name))
        else:
            print("Calque vide, ignoré : {}".format(layer_name))

def main():
    # 1. Récupération du chemin
    doc_path = rs.DocumentPath()

    folder = rs.BrowseForFolder(doc_path, "Dossier d'export")
    if not folder: return

    # 2. Choix des calques
    layers_to_export = rs.GetLayers("Sélectionner les calques à exporter")
    if not layers_to_export: return

    # 3. Options
    items = [("Enfants", "Non", "Oui"), ("Blocs", "Non", "Oui")]
    options = rs.GetBoolean("Options d'export", items, [True, True])
    if not options: return

    # 4. Processus d'export
    manager = RhinoExportManager(folder)

    # Ordre : filaire d'abord, puis calques visibles.
    # À la sortie (même en cas d'erreur) : calques restaurés, puis mode d'affichage restauré.
    with DisplayModeContext("Wireframe"), LayerStateContext():
        for layer in layers_to_export:
            manager.export_layer(layer, options[0], options[1])

if __name__ == "__main__":
    main()

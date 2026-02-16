import rhinoscriptsyntax as rs
import os
import unicodedata
import re

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def export_by_layer():
    path = rs.DocumentPath()
    if not path:
        title = "Select a folder for export"
        path = rs.BrowseForFolder(title)
        if not path:
            print("Not a valid path")
            exit()
    layers = rs.GetLayers("Select Layers to export")
    if layers:

        rhino_layers = RhinoLayers()
        rhino_blocks = RhinoBlocks()
        
        export_blockinstance_def = True
        include_sub_layer = True
        if rhino_blocks.get_blocknames_from_layers(layers):
            result = rs.GetBoolean("Export block instance defined with this layer", [("SearchAllInBlockDef", "False", "True"), ("IncludeSubLayers", "False", "True")], (export_blockinstance_def, include_sub_layer))
            if result:
                export_blockinstance_def = result[0]
                include_sub_layer = result[1]

        rhino_layers.force_visibility(True)
        rhino_layers.force_locks(False)
        for layer in layers:

            rs.UnselectAllObjects()

            look_at_layers = [layer]
            if include_sub_layer:
                look_at_layers.extend(rs.LayerChildren(layer))

            for sub_layers in look_at_layers:
                select_layer_objects(sub_layers, recursive=True)
            
                if export_blockinstance_def:
                    bns = rhino_blocks.get_blocknames_from_layer(sub_layers)
                    # print(bns)
                    for bn in bns:
                        select_instance_objects(bn)
            
            if rs.SelectedObjects():
                types = [rs.ObjectType(obj) for obj in rs.SelectedObjects()]
                cnt_instance = [_type == rs.filter.instance for _type in types].count(True)
                print("{} instances from layer {}".format(cnt_instance, layer))
                cnt_obj = len(types) - cnt_instance
                print("{} objects from layer {}".format(cnt_obj, layer))
                name = rs.LayerName(layer, fullpath=True)
                try:
                    name = name.replace("::", ";;")
                    file_name = name
                    # print(file_name)
                    # file_name = slugify(name, allow_unicode=True)
                    extension = ".3dm"
                    file_path = os.path.join(path, file_name + extension)
                    with open(file_path, "w") as f:
                        f.close()
                except:
                    name = name.replace("::", "-")
                    file_name = name
                    file_name = slugify(name, allow_unicode=True)
                    extension = ".3dm"
                    file_path = os.path.join(path, file_name + extension)

                # print(file_path)
                rs.Command('-_Export "{}"'.format(file_path), echo=False)
                # print("File exported at {}".format(file_path)) already written
            else:
                print("no object for layer {}".format(layer))

        rs.UnselectAllObjects()
        rhino_layers.previous_visibility()
        rhino_layers.previous_locks()


def select_layer_objects(layer, recursive=False):
    if recursive:
            children = rs.LayerChildren(layer)
            for child in children:
                select_layer_objects(child, recursive=True)
    
    rs.ObjectsByLayer(layer, True)


def select_instance_objects(blockname):
    objs = rs.BlockInstances(blockname, 0)
    rs.SelectObjects(objs)

class Block:
    def __init__(self, name):
        self.name = name
        self.layers = {}  

    def get_layers(self):
        return self.layers

    def set_layers(self, layers):
        self.layers = set(layers)

    def is_in_layer(self, layer):
        return layer in self.layers

class RhinoBlocks:
    def __init__(self):
        self.names = rs.BlockNames()
        self.blocks = [Block(name) for name in self.names]
        print(self.names)
        self.blocks_layers = []
        self.layers = {}

    def get_block_by_name(self, name):
        return self.blocks[self.names.index(name)]

    def get_blocknames_from_layers(self, layers):
            return [self.get_blocknames_from_layer(l) for l in layers]

    def get_blocknames_from_layer(self, layer):
        blocknames = []
        for i, layers in enumerate(self.get_blocks_layers()):
            if layer in layers:
                blockname = self.blocks[i].name
                blocknames.append(blockname)
        return blocknames
    
    def get_all_block_layers(self):
        if not self.layers:
            self.layers = set.union(*self.get_blocks_layers())
        return self.layers

    def get_blocks_layers(self):
        if not self.blocks_layers:
            for block in self.blocks:
                layers = self.get_block_layer(block)
                self.blocks_layers.append(layers)
        return self.blocks_layers

    def get_block_layer(self, block):
            if not block.get_layers():
                layers = []
                for obj in rs.BlockObjects(block.name):
                    if rs.IsBlockInstance(obj):
                        child_name = rs.BlockInstanceName(obj)
                        child_block = self.get_block_by_name(child_name)
                        layers.extend(self.get_block_layer(child_block))
                    layer = rs.ObjectLayer(obj)
                    layers.append(layer)
                block.set_layers(layers)

            return block.get_layers()
                


class RhinoLayers:
    def __init__(self):
        self.names = rs.LayerNames()

    def get_visibility(self):
        return self.visibles

    def force_visibility(self, visible):
        self.visibles = []
        for name in self.names:
            prev = rs.LayerVisible(name, visible)
            self.visibles.append(prev)
    
    def previous_visibility(self):
        visibles = self.get_visibility()
        for name, visible in zip(self.names, visibles):
            rs.LayerVisible(name, visible)

    def get_locks(self):
        return self.locks

    def force_locks(self, lock):
        self.locks = []
        for name in self.names:
            prev = rs.LayerLocked(name, lock)
            self.locks.append(prev)
    
    def previous_locks(self):
        locks = self.get_locks()
        for name, lock in zip(self.names, locks):
            rs.LayerLocked(name, lock)
   


export_by_layer()

"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs

__commandname__ = "hideLayer"

# RunCommand is the called when the user enters the command name in Rhino.
# The command name is defined by the filname minus "_cmd.py"
def RunCommand( is_interactive ):
    layers = rs.LayerNames()
    if layers:
        layer = rs.CurrentLayer()
        layer = rs.GetString("Layer to hide", layer, layers)
        if layer and rs.IsLayer(layer):
            rs.LayerVisible(layer, False)
        else:
            print("This is not a layer")
            return 1
    return 0

RunCommand(True)

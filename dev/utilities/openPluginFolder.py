"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import os
import rhinoscriptsyntax as rs
path = "%AppData%/McNeel/Rhinoceros/7.0/Plug-ins/PythonPlugins/"
expandpath = os.path.expandvars(path)
rs.Command("_NoEcho -_OpenURL {}".format(expandpath))

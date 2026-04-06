"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 06/04/2026
"""
import os
import rhinoscriptsyntax as rs
path = "%AppData%/McNeel/Rhinoceros/8.0/Plug-ins/"
expandpath = os.path.expandvars(path)
rs.Command("_NoEcho -_OpenURL {}".format(expandpath))

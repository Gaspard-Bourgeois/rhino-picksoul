"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 12/05/2026
"""
import os
import rhinoscriptsyntax as rs
path = "%AppData%/McNeel/Rhinoceros/7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/"
expandpath = os.path.expandvars(path)
rs.Command('_NoEcho -_OpenURL "{}"'.format(expandpath))

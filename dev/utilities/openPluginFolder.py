import os
import rhinoscriptsyntax as rs
path = "%AppData%/McNeel/Rhinoceros/7.0/Plug-ins/PythonPlugins/"
expandpath = os.path.expandvars(path)
rs.Command("_NoEcho -_OpenURL {}".format(expandpath))

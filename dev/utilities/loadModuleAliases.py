"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 08/01/26
"""
import rhinoscriptsyntax as rs


def loadModuleAliases():
    oldAliases = ["zsdu", "swpe", "sdmsd", "sdmgd", "sdmwe", "svtp", "svft", "svbk", "svrt", "svlt", "me", "re", "ihe", "sh", "jn", "ese"]
    rhino_aliases = {
            "zoomSelected" : "_NoEcho '_Zoom _Selected",
            "perspectiveView" : "_NoEcho '_SetView _World _Perspective",
            "topView" : "_NoEcho '_SetView _World _Top",
            "frontView" : "_NoEcho '_SetView _World _Front",
            "backView" : "_NoEcho '_SetView _World _Back",
            "rightView" : "_NoEcho '_SetView _World _Right",
            "leftView" : "_NoEcho '_SetView _World _Left",
            "shadedMode" : "_NoEcho '_SetDisplayMode _Viewport=_Active _Mode=_Shaded",
            "ghostedMode" : "_NoEcho '_SetDisplayMode _Viewport=_Active _Mode=_Ghosted",
            "wireframeMode" : "_NoEcho '_SetDisplayMode _Viewport=_Active _Mode=_Wireframe",
            "mirror" : "_NoEcho ! _Mirror",
            "changeLayer" : "! changeLayerInBlocks",
            "scale1D" : "_NoEcho ! _Scale1D",
            "move" : "_NoEcho ! _Move",
            "rotate" : "_NoEcho ! _Rotate",
            "invertHide" : "_NoEcho ! _Invert _Hide",
            "show" : "_NoEcho ! _Show",
            "join" : "_NoEcho ! _Join",
            "dupEdge" : "_NoEcho ! _DupEdge",
            "surfaceExtract" : "_NoEcho ! _ExtractSrf",
            "curveExtrude" : "! _ExtrudeCrv _Pause _Solid=_Yes",
            "surfaceExtrude" : "! _ExtrudeSrf _Pause _Solid=_Yes",
            "booleanUnion" : "_NoEcho ! _BooleanUnion _MergeAllFaces",
            "booleanDifference" : "_NoEcho ! _BooleanDifference",
            "curveBoolean" : "_NoEcho ! _CurveBoolean e t",
            "planarSrf" : "_NoEcho ! _PlanarSrf",
            "loft" : "_NoEcho ! _Loft",
            "sweep1" : "_NoEcho ! _Sweep1",
            "sweep2" : "_NoEcho ! _Sweep2",
            #"projectXY" : "_NoEcho ! _Project _ip _c",
            "projectXY" : "_NoEcho ! pTCPe",
            "projectToCPlane" : "_NoEcho ! _ProjectToCPlane _Pause _y",
            "cap" : "_NoEcho ! _Cap",
            "split" : "_NoEcho ! _Split",
            "worldCPlane" : "_NoEcho '_CPlane _World _Top",
            "objectCPlane" : "_CPlane _Object _Pause '_Plan",
            "showEdges" : "_NoEcho ! _ShowEdges",
            "showKeyValue" : '_NoEcho !_PropertiesPage _Pause T'
    }
    module_aliases_dev = {
            #cplane
            "editBlockXform" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/editBlockXform.py"',
            "copyBlockColor" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/copyBlockColor.py"',
            #cplane
            "alignCPlaneToBFitPoints" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/cplane/alignCPlaneToBFitPoints.py"',
            "alignCPlaneToBlock" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/cplane/alignCPlaneToBlock.py"',
            #insert
            "insertCircleFromBFitPoints" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertCircleFromBFitPoints.py"',
            #IO
            "importYaskawaJBI" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/importYaskawaJBI.py"',
            "rebuildPrograms" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/rebuildPrograms.py"',
            #layer
            "changeLayerInBlocks" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/changeLayerInBlocks.py"',
            "showLayer" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/showLayer.py"',
            "hideLayer" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/hideLayer.py"',
            #material
            "setMaterialData" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/material/setMaterialData.py"',
            "getMass" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/material/getMass.py"',
            "getGravityCenter" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/material/getGravityCenter.py"',
            #label#
            "blockNameLabel" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/label/blockNameLabel.py"',
            "blockCountLabel" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/label/blockCountLabel.py"',
            #selection#
            "selectNext" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectNext.py"',
            "selectNextOrigin" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectNextOrigin.py"',
            "selectPrev" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectPrev.py"',
            "selectPrevOrigin" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectPrevOrigin.py"',
            "selectDuplicateNames" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectDuplicateNames.py"',
            #orient#
            "copyBlockOrientation" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/orient/copyBlockOrientation.py"',
            "orientBlock" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/orient/orientBlock.py"',
            #utilities#
            "openPluginFolder" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/utilities/openPluginFolder.py"',
            "openRemotePanel" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/utilities/openRemotePanel.py"'
    }
    
    module_aliases_stable = {
    }

    def initials(string):
        return string[0] + "".join([char for char in string[1:-1] if (char.isupper() or char.isdigit())]) + string[-1]

    import rhinoscriptsyntax as rs

    items = ("Plugin_aliases", "Remove", "Install"), ("Rhino_aliases", "Remove", "Install"), ("Mode", "Safe", "ForceReinstal"), ("Plugin_version", "Stable", "Dev")
    results = rs.GetBoolean("Load Picksoul Module", items, (True, True, True, True))
    # print(results)
    if results:
        plugin_install = results[0]
        rhino_install = results[1]
        mode_force = results[2]
        plugin_version = results[3]
        all_aliases  = rs.AliasNames()
        count = 0
        if mode_force:
            for key in module_aliases_dev:
                count += rs.DeleteAlias(key)
                count += rs.DeleteAlias(initials(key))
            
            for key in module_aliases_stable:
                count += rs.DeleteAlias(key)
                count += rs.DeleteAlias(initials(key))
            
            for key in rhino_aliases:
                count += rs.DeleteAlias(key)
                count += rs.DeleteAlias(initials(key))

            for key in oldAliases:
                count += rs.DeleteAlias(key)
        else:
            if not plugin_install:
                for key in module_aliases_dev:
                    count += rs.DeleteAlias(key)
                    count += rs.DeleteAlias(initials(key))
                for key in module_aliases_stable:
                    count += rs.DeleteAlias(key)
                    count += rs.DeleteAlias(initials(key))
            if not rhino_install:
                for key in rhino_aliases:
                    count += rs.DeleteAlias(key)
                    count += rs.DeleteAlias(initials(key))
        if count:
            print("{} aliases deleted".format(count))
            
        count = 0
        if plugin_install:
            for key, value in module_aliases_dev.items():
                # print(key, value)
                if not mode_force and key in all_aliases:
                    pass
                count += rs.AddAlias(key, value)
                count += rs.AddAlias(initials(key), key)
            if plugin_version:
                for key, value in module_aliases_stable.items():
                    count += rs.AddAlias(key, value)
                    count += rs.AddAlias(initials(key), key)
        if rhino_install:
            for key, value in rhino_aliases.items():
                # print(key, value)
                if not mode_force and key in all_aliases:
                    pass
                count += rs.AddAlias(key, value)
                count += rs.AddAlias(initials(key), value)
        if count:
            print("{} aliases installed".format(count))

loadModuleAliases()

"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 18/02/26
"""
import rhinoscriptsyntax as rs


def loadModuleAliases():
    oldAliases = ["zsdu", "swpe", "sdmsd", "sdmgd", "sdmwe", "svtp", "svft", "svbk", "svrt", "svlt", "me", "re", "ihe", "sh", "jn", "ese"]

    roccat_aliases = {
    'A1' : 'Click',
    'A2' : 'Menu',
    'A3' : 'Universal scrolling',
    'A9' : 'rightView',
    'A10' : 'topView',
    'A11' : 'frontView',
    'A12' : 'perspectiveView',
    'A13' : 'rotate',
    'A14' : 'move',
    'A15' : 'Scroll Up',
    'A16' : 'Scroll Down',
    'A4' : '0',
    'A5' : 'Profile Up',
    'A6' : 'Easy shift',
    'A7' : 'Ctrl + Z',
    'A8' : 'Ctrl + Y',
    'A17' : 'invertHide',
    'A18' : 'show',
    'A19' : 'zoomSelected',
    'A25' : 'ghostMode',
    'A26' : 'shadedMode',
    'A27' : 'wireframeMode',
    'A28' : 'worldCPlane',
    'A29' : 'mirror',
    'A30' : 'scale1D',
    'A31' : 'Page_up',
    'A32' : 'Page_down',
    'A20' : 'Disabled',
    'A21' : 'Profile Up',
    'A22' : 'Disabled',
    'A23' : 'Disabled',
    'A24' : 'Disabled',
    'B1' : 'Click',
    'B2' : 'Menu',
    'B3' : 'objectToCPlane',
    'B9' : 'join',
    'B10' : 'projectToCPlane',
    'B11' : 'curveExtrude',
    'B12' : 'dupEdge',
    'B13' : 'curveBoolean',
    'B14' : 'booleanUnion',
    'B15' : 'Scroll Up',
    'B16' : 'Scroll Down',
    'B4' : 'booleanDifference',
    'B5' : 'Easy shift',
    'B6' : 'Profile Down',
    'B7' : 'sweep1',
    'B8' : 'sweep2',
    'B17' : 'planarSrf',
    'B18' : 'loft',
    'B19' : 'changeLayer',
    'B25' : 'cap',
    'B26' : 'projectXY',
    'B27' : 'surfaceExtrude',
    'B28' : 'surfaceExtract',
    'B29' : 'rotateWorld',
    'B30' : 'orientObject',
    'B31' : 'Volume up',
    'B32' : 'Volume down',
    'B20' : 'showEdges',
    'B21' : 'Disabled',
    'B22' : 'Profile Down',
    'B23' : 'Disabled',
    'B24' : 'Disabled'
    }

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
            # "changeLayer" : "! changeLayerInBlocks",
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
            "showKeyValue" : '_NoEcho !_PropertiesPage _Pause T',
            ## Layer
            'previousLayer' : '_NoEcho ! _-Layerbook _Previous _Enter -_showLayer "_pose_def, Blocs, Cellule"',
            'egalLayer' : '_NoEcho ! _-Layerbook _Enter -_showLayer "_pose_def, Blocs, Cellule"',
            'nextLayer' : '_NoEcho ! _-Layerbook _Next _Enter -_showLayer "_pose_def, Blocs, Cellule, anotation*" _Enter',
            'showLayerAtelier' : '_NoEcho ! -_showLayer Atelier*'
    }
    module_aliases_dev = {
            #block
            "editBlockXform" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/editBlockXform.py"',
            "copyBlockColor" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/copyBlockColor.py"',
            "definePose" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/definePose.py"',
            "decomposeReciproque" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/decomposeReciproque.py"',
            "reconstructBlock" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/reconstructBlock.py"',
            "extractFromBlock" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/extractFromBlock.py"',
            #cplane
            "alignCPlaneToBFitPoints" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/cplane/alignCPlaneToBFitPoints.py"',
            "alignCPlaneToBlock" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/cplane/alignCPlaneToBlock.py"',
            #insert
            "insertPose" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertPose.py"',
            "insertCircleFromBFitPoints" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertCircleFromBFitPoints.py"',
            #IO
            "importYaskawaJBI" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/importYaskawaJBI.py"',
            "rebuildPrograms" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/rebuildPrograms.py"',
            "exportByLayer" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/exportByLayer.py"',
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
            "updateAnnotationStyle" : '_NoEcho !-_RunPythonScript "../Plug-ins/PythonPlugins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/label/updateAnnotationStyle.py"',
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
    

    def initials(string):
        return string[0] + "".join([char for char in string[1:-1] if (char.isupper() or char.isdigit())]) + string[-1]

    import rhinoscriptsyntax as rs

    items = ("Module_aliases", "Remove", "Install"), ("Souris_roccat_aliases", "Remove", "Install"), ("Mode", "Safe", "ForceReinstal"), ("Plugin_version", "Stable", "Dev")
    results = rs.GetBoolean("Load Picksoul Module", items, (True, True, True, True))
    # print(results)
    if results:
        plugin_install = results[0]
        roccat_install = results[1]
        mode_force = results[2]
        version_dev = results[3]
        all_aliases  = rs.AliasNames()
        count = 0
        
        
        
        delete_aliases = {}
        
        if mode_force:
            delete_aliases.update(module_aliases_dev)
            delete_aliases.update(rhino_aliases)
            
            for key in oldAliases:
                count += rs.DeleteAlias(key)
        else:
            if not plugin_install:
                delete_aliases.update(module_aliases_dev)
                delete_aliases.update(rhino_aliases)
                
        for key in delete_aliases:
            count += rs.DeleteAlias(key)
            count += rs.DeleteAlias(initials(key))

        if count:
            print("{} aliases deleted".format(count))
            
        count = 0
        if plugin_install:
            
            install_aliases = {}
            if version_dev:
                install_aliases.update(module_aliases_dev)
                install_aliases.update(rhino_aliases)
            else:
                install_aliases.update(rhino_aliases)
            
            for key, value in install_aliases.items():
                # print(key, value)
                if not mode_force and key in all_aliases:
                    pass
                count += rs.AddAlias(key, value)
                count += rs.AddAlias(initials(key), key)
                

        if count:
            print("{} aliases installed".format(count))

loadModuleAliases()

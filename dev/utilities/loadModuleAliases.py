"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 18/02/26
"""
import rhinoscriptsyntax as rs


def loadModuleAliases():
    oldAliases = ["zsdu", "swpe", "sdmsd", "sdmgd", "sdmwe", "svtp", "svft", "svbk", "svrt", "svlt", "me", "re", "ihe", "sh", "jn", "ese"]

    roccat_aliases = {
    'a1' : 'Click',
    'a2' : 'Menu',
    'a3' : 'Universal scrolling',
    'a9' : 'rightView',
    'a10' : 'topView',
    'a11' : 'frontView',
    'a12' : 'perspectiveView',
    'a13' : 'rotate',
    'a14' : 'move',
    'a15' : 'Scroll Up',
    'a16' : 'Scroll Down',
    'a4' : '0',
    'a5' : 'Profile Up',
    'a6' : 'Easy shift',
    'a7' : 'Ctrl + Z',
    'a8' : 'Ctrl + Y',
    'a17' : 'invertHide',
    'a18' : 'show',
    'a19' : 'zoomSelected',
    'a25' : 'ghostMode',
    'a26' : 'shadedMode',
    'a27' : 'wireframeMode',
    'a28' : 'worldCPlane',
    'a29' : 'mirror',
    'a30' : 'scale1D',
    'a31' : 'Page_up',
    'a32' : 'Page_down',
    'a20' : 'Disabled',
    'a21' : 'Profile Up',
    'a22' : 'Disabled',
    'a23' : 'Disabled',
    'a24' : 'Disabled',
    'b1' : 'Click',
    'b2' : 'Menu',
    'b3' : 'objectToCPlane',
    'b9' : 'join',
    'b10' : 'projectToCPlane',
    'b11' : 'curveExtrude',
    'b12' : 'dupEdge',
    'b13' : 'curveBoolean',
    'b14' : 'booleanUnion',
    'b15' : 'Scroll Up',
    'b16' : 'Scroll Down',
    'b4' : 'booleanDifference',
    'b5' : 'Easy shift',
    'b6' : 'Profile Down',
    'b7' : 'sweep1',
    'b8' : 'sweep2',
    'b17' : 'planarSrf',
    'b18' : 'loft',
    'b19' : 'changeLayer',
    'b25' : 'cap',
    'b26' : 'projectXY',
    'b27' : 'surfaceExtrude',
    'b28' : 'surfaceExtract',
    'b29' : 'rotateWorld',
    'b30' : 'orientObject',
    'b31' : 'Volume up',
    'b32' : 'Volume down',
    'b20' : 'showEdges',
    'b21' : 'Disabled',
    'b22' : 'Profile Down',
    'b23' : 'Disabled',
    'b24' : 'Disabled'
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
            delete_aliases.update(roccat_aliases)

            for key in oldAliases:
                count += rs.DeleteAlias(key)
        else:
            if not plugin_install:
                delete_aliases.update(module_aliases_dev)
                delete_aliases.update(rhino_aliases)
                delete_aliases.update(roccat_aliases)
                
        for key in delete_aliases:
            count += rs.DeleteAlias(key)
            count += rs.DeleteAlias(initials(key))

        if count:
            print("{} aliases deleted".format(count))
            
        count = 0
        if plugin_install:
            
            install_aliases = {}
            if roccat_install:
                install_aliases.update(roccat_aliases)
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
                if key != initials(key):
                    count += rs.AddAlias(initials(key), key)
                

        if count:
            print("{} aliases installed".format(count))

loadModuleAliases()

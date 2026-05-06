"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 2.0
Date: 06/05/26
"""
import rhinoscriptsyntax as rs


def loadModuleAliases():
    
    module_aliases_dev = {
            #block
            "copyBlockColor" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/copyBlockColor.py"',
            "decomposeReciproque" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/decomposeReciproque.py"',
            "definePose" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/definePose.py"',
            "editBlockXform" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/editBlockXform.py"',
            "extractFromBlock" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/extractFromBlock.py"',
            "reconstructBlock" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/block/reconstructBlock.py"',
            #cplane
            "alignCPlaneToBFitPoints" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/cplane/alignCPlaneToBFitPoints.py"',
            "alignCPlaneToBlock" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/cplane/alignCPlaneToBlock.py"',
            #gumball
            "orientGumballWithCurrentCPlane" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/gumball/orientGumballWithCurrentCPlane.py"',
            "moveGumballToSpecificBlock" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/gumball/moveGumballToSpecificBlock.py"',
            #insert
            "insertBoundingSphere" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertBoundingSphere.py"',
            "insertCircleFromBFitPoints" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertCircleFromBFitPoints.py"',
            "insertPose" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertPose.py"',
            "insertShiftedCurvesOnSurface" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/insert/insertShiftedCurvesOnSurface.py"',
            #IO
            "exportByLayer" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/exportByLayer.py"',
            "importYaskawaJBI" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/importYaskawaJBI.py"',
            "rebuildPrograms" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/IO/rebuildPrograms.py"',
            #label#
            "blockCountLabel" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/label/blockCountLabel.py"',
            "blockNameLabel" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/label/blockNameLabel.py"',
            "updateAnnotationStyle" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/label/updateAnnotationStyle.py"',
            #layer
            "changeLayerInBlocks" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/changeLayerInBlocks.py"',
            "hideLayer" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/hideLayer.py"',
            "pasteToCurrentLayer" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/pasteToCurrentLayer.py"',
            "showLayer" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/layer/showLayer.py"',
            #material
            "getGravityCenter" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/material/getGravityCenter.py"',
            "getMass" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/material/getMass.py"',
            "setMaterialData" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/material/setMaterialData.py"',
            #move#
            "copyBlockOrientation" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/move/copyBlockOrientation.py"',
            "orientBlock" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/move/orientBlock.py"',
            "smartAlign" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/move/smartAlign.py"',
            "smartMove" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/move/smartMove.py"',
            #selection#
            "selectDuplicateNames" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectDuplicateNames.py"',
            "selectFromDecompose" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectFromDecompose.py"',
            "selectNext" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectNext.py"',
            "selectNextOrigin" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectNextOrigin.py"',
            "selectPose" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectPose.py"',
            "selectPrev" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectPrev.py"',
            "selectPrevOrigin" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/selection/selectPrevOrigin.py"',
            #utilities#
            "openPluginFolder" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/utilities/openPluginFolder.py"',
            "openRemotePanel" : '_NoEcho !-_RunPythonScript "../../7.0/Plug-ins/Rhino Picksoul (4a97e0e1-48sz-s842-5s58-d4fs5sd541fs)/dev/utilities/openRemotePanel.py"'
    }
    
    oldAliases = ["zsdu", "swpe", "sdmsd", "sdmgd", "sdmwe", "svtp", "svft", "svbk", "svrt", "svlt", "me", "re", "ihe", "sh", "jn", "ese"]

    roccat_aliases = {
'a1' : 'Click',
'a2' : 'Menu',
'a3' : 'Universal scrolling',
'a9' : '_rightView',
'a10' : '_topView',
'a11' : '_frontView',
'a12' : '_perspectiveView',
'a13' : '_rotate',
'a14' : '_move',
'a15' : 'Scroll Up',
'a16' : 'Scroll Down',
'a4' : '0',
'a5' : 'Profile Up',
'a6' : 'Easy shift',
'a7' : '_selectFromDecompose',
'a8' : '_decomposeReciproque',
'a17' : '_invertHide',
'a18' : '_show',
'a19' : '_zoomSelected',
'a25' : '_ghostedMode',
'a26' : '_shadedMode',
'a27' : '_wireframeMode',
'a28' : '_worldCPlane',
'a29' : '_mirror',
'a30' : '_scale1D',
'a31' : 'Page_up',
'a32' : 'Page_down',
'a20' : 'Disabled',
'a21' : 'Profile Up',
'a22' : 'Disabled',
'a23' : 'Disabled',
'a24' : '_selectPose',
'b1' : 'Click',
'b2' : 'Menu',
'b3' : '_ungroup',
'b9' : '_join',
'b10' : '_projectToCPlane',
'b11' : '_curveExtrude',
'b12' : '_dupEdge',
'b13' : '_curveBoolean',
'b14' : '_booleanUnion',
'b15' : 'Scroll Up',
'b16' : 'Scroll Down',
'b4' : '_booleanDifference',
'b5' : 'Easy shift',
'b6' : 'Profile Down',
'b7' : '_reconstructBlock',
'b8' : '_pasteToCurrentLayer',
'b17' : '_planarSrf',
'b18' : '_loft',
'b19' : '_group',
'b25' : '_cap',
'b26' : '_projectXY',
'b27' : '_surfaceExtrude',
'b28' : '_surfaceExtract',
'b29' : 'rotateWorld',
'b30' : '_smartMove',
'b31' : 'Volume up',
'b32' : 'Volume down',
'b20' : '_showEdges',
'b21' : 'Disabled',
'b22' : 'Profile Down',
'b23' : '_reconstructBlock',
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
            "group" : "_NoEcho ! _Group",
            "ungroup" : "_NoEcho ! _UnGroup",
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

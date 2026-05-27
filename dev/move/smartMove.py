import Rhino
import rhinoscriptsyntax as rs

__commandname__ = "orientObject"

def getWithOption(_message):
    _i = 0
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(_message)
    go.SubObjectSelect = False
    go.GroupSelect = True
    go.AcceptNothing(True)
    
    boolOption = Rhino.Input.Custom.OptionToggle(False, "False", "True")
    go.AddOptionToggle("Relative", boolOption)

    while True:
        get_rc = go.GetMultiple(1,0)
        if get_rc==Rhino.Input.GetResult.Object:
            break
        if (go.CommandResult() != Rhino.Commands.Result.Success):
            break
        if get_rc == Rhino.Input.GetResult.Option:
            continue
    rc = []
    count = go.ObjectCount
    for i in range(count):
        objref = go.Object(i)
        rc.append(objref.ObjectId)
    _i = boolOption.CurrentValue
    go.Dispose()
    
    return rc, _i

def getOriginDestWithOption(_message):
    rs.UnselectAllObjects()
    
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(_message)
    go.SubObjectSelect = False
    go.GroupSelect = False
    go.AcceptNothing(True)
    go.DisablePreSelect()
    
    go.GeometryFilter = (Rhino.DocObjects.ObjectType.InstanceReference | 
                         Rhino.DocObjects.ObjectType.Surface | 
                         Rhino.DocObjects.ObjectType.Brep | 
                         Rhino.DocObjects.ObjectType.Extrusion | 
                         Rhino.DocObjects.ObjectType.Curve)
    
    go.AddOption("UseCPlane")
    
    get_rc = go.Get()
    
    if get_rc == Rhino.Input.GetResult.Object:
        obj_ref = go.Object(0)
        obj_id = obj_ref.ObjectId
        pt = obj_ref.SelectionPoint()
        res = "object", (obj_id, False, 0, pt, rs.CurrentView())
        go.Dispose()
        return res
            
    elif get_rc == Rhino.Input.GetResult.Option:
        go.Dispose()
        return "cplane", None
            
    elif get_rc == Rhino.Input.GetResult.Nothing:
        go.Dispose()
        return "world", None
        
    go.Dispose()
    return None, None

def getClickedPlaneFromObjectEx(obj):
    objId = obj[0]
    objType = rs.ObjectType(objId)
    if rs.IsBlockInstance(objId):
        blockTransform = rs.BlockInstanceXform(objId)
        plane = rs.PlaneTransform(rs.WorldXYPlane(), blockTransform)
    elif objType == rs.filter.curve:
        moussePoint = obj[3]
        param = rs.CurveClosestPoint(objId, moussePoint)
        plane = rs.CurveFrame(objId, param)
    else:
        moussePoint = obj[3]
        bcp = rs.BrepClosestPoint(objId, moussePoint)
        pt = bcp[0]
        normal = -bcp[3]
        type = bcp[2][0]
        if type == 3:
            faceIdx = bcp[2][1]
            rs.EnableRedraw(False)
            faces = rs.ExplodePolysurfaces(objId)
            face = faces[faceIdx] if faces else objId
            u, v = rs.SurfaceClosestPoint(face, pt)
            plane = rs.SurfaceFrame(face, [u, v])
            rs.DeleteObjects(faces)
            rs.EnableRedraw(True)
        else:
            plane = rs.PlaneFromNormal(pt, normal)
    return plane

def pointBarycenter(points):
    x = y = z = 0
    for pt in points:
        x += pt[0]; y += pt[1]; z += pt[2]
    return [x/len(points), y/len(points), z/len(points)]

def getPlaneFromObject(objId):
    objType = rs.ObjectType(objId)
    if rs.IsBlockInstance(objId):
        blockTransform = rs.BlockInstanceXform(objId)
        return rs.PlaneTransform(rs.WorldXYPlane(), blockTransform)
    elif objType == rs.filter.curve:
        return rs.CurveFrame(objId, 0)
    elif objType == rs.filter.surface:
        return rs.SurfaceFrame(objId, [0, 0])
    else:
        corners = rs.BoundingBox(objId)
        pt = pointBarycenter(corners)
        return rs.MovePlane(rs.WorldXYPlane(), pt)

def RunCommand(is_interactive):
    objs = rs.SelectedObjects()
    is_relative = False
    
    if not objs:
        objs, is_relative = getWithOption("Select objects to translate")
        
    if objs:
        # ÉTAPE 1 : ORIGINE
        resTypeFrom, objFrom = getOriginDestWithOption("Select origin (Enter for WorldXY)")
        if resTypeFrom == "object":
            planeFrom = getClickedPlaneFromObjectEx(objFrom)
        elif resTypeFrom == "cplane":
            planeFrom = rs.ViewCPlane()
        elif resTypeFrom == "world":
            planeFrom = rs.WorldXYPlane()
        else:
            return

        # ÉTAPE 2 : DESTINATION
        resTypeDest, objDest = getOriginDestWithOption("Select destination (Enter for WorldXY)")
        if resTypeDest == "object":
            planeDest = getClickedPlaneFromObjectEx(objDest)
            if not rs.IsBlockInstance(objDest[0]):
                planeDest = rs.RotatePlane(planeDest, 180, planeDest.XAxis)
        elif resTypeDest == "cplane":
            planeDest = rs.ViewCPlane()
        elif resTypeDest == "world":
            planeDest = rs.WorldXYPlane()
        else:
            return

        # TRANSFORMATION
        if planeFrom and planeDest:
            if is_relative:
                # Transformation relative : on calcule le delta entre planeFrom et planeDest,
                # puis on l'applique depuis le repère local de chaque objet
                xform_delta = rs.XformChangeBasis(planeFrom, planeDest)
                for obj in objs:
                    planeObj = getPlaneFromObject(obj)
                    # On exprime le delta dans le repère local de l'objet
                    xform_to_local = rs.XformChangeBasis(rs.WorldXYPlane(), planeObj)
                    xform_to_world = rs.XformChangeBasis(planeObj, rs.WorldXYPlane())
                    xform = rs.XformMultiply(xform_to_world, rs.XformMultiply(xform_delta, xform_to_local))
                    rs.TransformObject(obj, xform)
            else:
                # Transformation absolue : changement de repère complet de planeFrom vers planeDest
                xform = rs.XformChangeBasis(planeFrom, planeDest)
                rs.TransformObjects(objs, xform)

            rs.SelectObjects(objs)
            print("{} objets orientés".format(len(objs)))

    return 0

if __name__ == "__main__":
    RunCommand(True)
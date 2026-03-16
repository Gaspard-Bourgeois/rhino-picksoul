import Rhino
import rhinoscriptsyntax as rs

__commandname__ = "smartAlign"

def getWithOption(_message):
    _i = 0
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(_message)
    go.SubObjectSelect = False
    go.GroupSelect = True
    go.AcceptNothing(True)
    
    boolOption = Rhino.Input.Custom.OptionToggle(False, "Mono", "Multi")
    go.AddOptionToggle("Destination", boolOption)

    while True:
        get_rc = go.GetMultiple(1,0)
        if get_rc==Rhino.Input.GetResult.Object:
            break
        if (go.CommandResult() != Rhino.Commands.Result.Success):
            return None, None
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

def getClickedPlaneFromObjectEx(obj):
    objId = obj[0]
    objType = rs.ObjectType(objId)
    # print(objType)
    if rs.IsBlockInstance(objId):
        blockTransform = rs.BlockInstanceXform(objId)
        print("Is a Block")
        plane = rs.PlaneTransform(rs.WorldXYPlane(), blockTransform)
    elif objType == rs.filter.curve:
        print("Is a Curve")
        moussePoint = obj[3]
        param = rs.CurveClosestPoint(objId, moussePoint)
        plane = rs.CurveFrame(objId, param)
    else:
        moussePoint = obj[3]
        bcp = rs.BrepClosestPoint(objId, moussePoint)
        pt = bcp[0]
        normal = - bcp[3]
        type = bcp[2][0]
        # print(bcp)
        if type == 3:
            print("Is a brep face")
            faceIdx = bcp[2][1]
            rs.EnableRedraw(False)
            faces = rs.ExplodePolysurfaces(objId)
            # print(faces)
            face = faces[faceIdx] if faces else objId
            u, v = rs.SurfaceClosestPoint(face, pt)
            plane = rs.SurfaceFrame(face, [u, v])
            rs.DeleteObjects(faces)
            rs.EnableRedraw(True)
        else:
            print("Is a brep element")
            plane = rs.PlaneFromNormal(pt, normal)
                    
    return plane

def pointBarycenter(points):
    x = 0
    y = 0
    z = 0
    for point in points:
        x += point[0]
        y += point[1]
        z += point[2]
    return [x/len(points), y/len(points), z/len(points)]

def getPlaneFromObject(objId):
    objType = rs.ObjectType(objId)
    # print(objType)
    if rs.IsBlockInstance(objId):
        blockTransform = rs.BlockInstanceXform(objId)
        print("Is a Block")
        plane = rs.PlaneTransform(rs.WorldXYPlane(), blockTransform)
    elif objType == rs.filter.curve:
        print("Is a Curve")
        param = 0
        plane = rs.CurveFrame(objId, param)
    elif objType == rs.filter.surface:
        print("Is a Surface")
        param = [0, 0]
        plane = rs.SurfaceFrame(objId, param)
    else:
        print("Is an element")
        corners = rs.BoundingBox(objId)
        pt = pointBarycenter(corners)
        plane = rs.MovePlane(rs.WorldXYPlane(), pt)
    return plane

    
# RunCommand is the called when the user enters the command name in Rhino.
# The command name is defined by the filname minus "_cmd.py"
def RunCommand( is_interactive ):
    objs = rs.SelectedObjects()
    objFilter = rs.filter.instance + rs.filter.surface + rs.filter.polysurface + rs.filter.extrusion + rs.filter.curve
    is_multi = False
    if not objs:
        # objs = rs.GetObjects("Select objects to translate")
        objs, is_multi = getWithOption("Select objects to group")
    if objs:
        planesDest = []
        if is_multi:
            objsDest = rs.GetObjectsEx("Select destinations", objFilter, False)
        else:
            objDest = rs.GetObjectEx("Select destination", objFilter, False)
            objsDest = [objDest] if objDest else []
        if len(objsDest):
            for objDest in objsDest:
                planeDest = getClickedPlaneFromObjectEx(objDest)
                planeDest = planeDest if rs.IsBlockInstance(objDest[0]) else rs.RotatePlane(planeDest, 180, planeDest.XAxis)
                planesDest.append(planeDest)
        else:
            print("Is the WorldXYPlane")
            planeDest = rs.WorldXYPlane()
            planesDest.append(planeDest)
        
        if planesDest:
            planesCount = len(planesDest)
            for i, obj in enumerate(objs):
                planeObj = getPlaneFromObject(obj)
                planeXY = rs.WorldXYPlane()
                planeDest = planesDest[i%planesCount]
                xform = rs.XformRotation1(planeObj, planeDest)
                rs.TransformObject(obj, xform)
            rs.SelectObjects(objs)
            print("{} objets oriented".format(len(objs)))
            return 0
  # you can optionally return a value from this function
  # to signify command result. Return values that make
  # sense are
  #   0 == success
  #   1 == cancel
  # If this function does not return a value, success is assumed
    return 0
    
RunCommand(True)

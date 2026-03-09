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
    """
    Demande à l'utilisateur de sélectionner un objet ou de cliquer sur l'option 'UseCPlane'.
    Renvoie le type de sélection ("object", "cplane" ou None) et les données associées.
    """
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(_message)
    go.SubObjectSelect = False
    go.GroupSelect = True
    go.AcceptNothing(True)
    
    # Filtre géométrique équivalent à : rs.filter.instance + rs.filter.surface + rs.filter.polysurface + rs.filter.extrusion + rs.filter.curve
    go.GeometryFilter = (Rhino.DocObjects.ObjectType.InstanceReference | 
                         Rhino.DocObjects.ObjectType.Surface | 
                         Rhino.DocObjects.ObjectType.Brep | 
                         Rhino.DocObjects.ObjectType.Extrusion | 
                         Rhino.DocObjects.ObjectType.Curve)
    
    go.AddOption("UseCPlane")
    
    while True:
        get_rc = go.Get()
        if get_rc == Rhino.Input.GetResult.Object:
            obj_ref = go.Object(0)
            obj_id = obj_ref.ObjectId
            pt = obj_ref.SelectionPoint()
            go.Dispose()
            # On recrée une structure similaire à ce que renvoie rs.GetObjectEx()
            # pour rester compatible avec la fonction getClickedPlaneFromObjectEx
            return "object", (obj_id, False, 0, pt, rs.CurrentView())
            
        elif get_rc == Rhino.Input.GetResult.Option:
            go.Dispose()
            return "cplane", None
            
        elif get_rc == Rhino.Input.GetResult.Cancel or get_rc == Rhino.Input.GetResult.Nothing:
            go.Dispose()
            return None, None

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
    is_relative = False
    
    if not objs:
        objs, is_relative = getWithOption("Select objects to translate")
        
    if objs: 
        # SÉLECTION ORIGINE
        resTypeFrom, objFrom = getOriginDestWithOption("Select origin")
        
        if resTypeFrom == "object":
            planeFrom = getClickedPlaneFromObjectEx(objFrom)
        elif resTypeFrom == "cplane":
            print("Is the CPlane")
            planeFrom = rs.ViewCPlane()
        else:
            print("Is the WorldXYPlane")
            planeFrom = rs.WorldXYPlane()
        
        if planeFrom:
            # SÉLECTION DESTINATION
            resTypeDest, objDest = getOriginDestWithOption("Select destination")
            
            if resTypeDest == "object":
                planeDest = getClickedPlaneFromObjectEx(objDest)
                planeDest = planeDest if rs.IsBlockInstance(objDest[0]) else rs.RotatePlane(planeDest, 180, planeDest.XAxis)
            elif resTypeDest == "cplane":
                print("Is the CPlane")
                planeDest = rs.ViewCPlane()
            else:
                print("Is the WorldXYPlane")
                planeDest = rs.WorldXYPlane()
                
            if planeDest:
                if is_relative:
                    for obj in objs:
                        planeObj = getPlaneFromObject(obj)
                        planeXY = rs.WorldXYPlane()

                        relative_xform = rs.XformRotation1(planeXY, planeObj)
                        relative_planeDest = rs.PlaneTransform(planeDest, relative_xform)
                        
                        xform = rs.XformRotation1(planeObj, relative_planeDest)
                        rs.TransformObject(obj, xform)
                else:
                    xform = rs.XformRotation1(planeFrom, planeDest)
                    rs.TransformObjects(objs, xform)
                    
                rs.SelectObjects(objs)
                print("{} objets oriented".format(len(objs)))
                return 0

    return 0
    
RunCommand(True)

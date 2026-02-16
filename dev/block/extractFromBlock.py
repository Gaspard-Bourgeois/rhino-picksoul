import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def extractFromBlock():
    block = rs.GetObject("Select Block to extract objects from", rs.filter.instance, preselect=True)
    if not block: return

    blockName = rs.BlockInstanceName(block)
    objref = rs.coercerhinoobject(block)
    idef = objref.InstanceDefinition
    idefIndex = idef.Index
    
    XformBlock = rs.BlockInstanceXform(block)
    blockObjects = rs.BlockObjects(blockName)
    blockInstanceObjects = rs.TransformObjects(blockObjects, XformBlock, True)
    
    objs = rs.GetObjects("Select Objects to extract from Block", objects =blockInstanceObjects)
    rs.EnableRedraw(False)
    if objs:    
        newObjs = rs.CopyObjects(objs, [0, 0, 0])
        rs.SelectObjects(newObjs)
    rs.DeleteObjects(blockInstanceObjects)
    rs.EnableRedraw(True)
   
extractFromBlock()

"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs


def changeLayerInBlocks():
    
    objs = rs.GetObjects("Select block instances", 4096, preselect=True)
    if not objs:return
    
    targ = rs.GetLayer()
    if not targ:return
    
    b_b_names = list(set([rs.BlockInstanceName(id) for id in objs]))
    done = []
    
    def BlockDrill(b_b_names):
        while True:
            if len (b_b_names) > 0 :
                b_name = b_b_names.pop()
            else: break
            
            done.append(b_name)
            temp = rs.BlockObjects(b_name)
            rs.ObjectLayer(temp, targ)
            
            for tempId in temp:
                if rs.IsBlockInstance(tempId):
                    tempName = rs.BlockInstanceName(tempId)
                    if tempName not in b_b_names and tempName not in done:
                        b_b_names.append(tempName)
                        BlockDrill(b_b_names)
            
    BlockDrill(b_b_names)
    
if __name__ == "__main__": 
    changeLayerInBlocks()

"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 09/01/26
"""
import rhinoscriptsyntax as rs


def copyBlockColor():
    
    ids_dst = rs.GetObjects("Select block instances destination", 4096, preselect=True)
    if not ids_dst:return
    
    ids_src = rs.GetObject("Select block instances source", 4096, preselect=False)
    if not ids_src:return
    
    src_names = list(set([rs.BlockInstanceName(id) for id in [ids_src]]))
    dst_names = list(set([rs.BlockInstanceName(id) for id in ids_dst]))
    
    
    
    dict_color_src = {
    0 : 'Color from layer',
    1 : 'Color from object',
    2 : 'Color from material',
    3 : 'Color from parent'
    }

    def BlockDrill(names, _type="src"):
        global color_src
        global color
        while True:
            if len (names) > 0 :
                name = names.pop()
            else: break
            
            done.append(name)
            temp = rs.BlockObjects(name)
            if _type == "src":
                color = rs.ObjectColor(temp)
                color_src = rs.ObjectColorSource(temp)
                
                print("Couleur d'affichage copiee :", dict_color_src[color_src])
                if color_src == 1:
                    print("Couleur copiee :", color)
                    return
            else: 
                rs.ObjectColorSource(temp, color_src)
                if color_src == 1:
                    rs.ObjectColor(temp, color)
            for tempId in temp:
                if rs.IsBlockInstance(tempId):
                    tempName = rs.BlockInstanceName(tempId)
                    if tempName not in names and tempName not in done:
                        names.append(tempName)
                        BlockDrill(names)
    done = []      
    BlockDrill(src_names, _type="src")

    done = []
    BlockDrill(dst_names, _type= "dst")
    
if __name__ == "__main__": 
    copyBlockColor()

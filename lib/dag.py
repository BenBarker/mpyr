'''Functions for navigating maya nodes'''
import maya.cmds as cmds

def getLowestParent(nodeList):
    '''Given a list of nodes, get the topmost parent common to every node in the list.
    If no node parent is found the scene root (|) is returned.'''
    testList = []
    
    #exclude any node parented to another node in the nodeList.
    #They will automatically share the lowest parent.
    for node in nodelist:
        try:
            nodePar = cmds.listRelatives(node,p=True,fullPath=True)[0]

        except RuntimeError: #this is a root level node, common parent is scene root
            return ('|')
            
        #check immediate parent
        if nodePar in nodeList:
            continue
            
        #Check other parents (a little slower)
        splitPars = nodePar.split("|")[:-1]
        alreadyInList = False
        for par in splitPars:
            if par in nodeList:
                alreadyInList = True
                break
        if alreadyInList:
            continue
            
        #tests passed, add to list to be analyzed
        testList.append(node)
        
    #If only one node survives the test it was a simple tree. Return the root's parent.
    if len(testList) == 1:
        return cmds.listRelatives(testList[0],p=True)
        
    #else, we must test
    lowestPar = '|'
    #TODO test
    
def getCommonParent(node1,node2):
    '''return the common parent of both nodes'''
    fullPath1 = cmds.listRelatives(node1,fullPath=True,p=True)[0]
    fullPath2 = cmds.listRelatives(node2,fullPath=True,p=True)[0]
    for index,item in enumerate(fullPath1):
        if fullPath2[index] != item:
            return fullPath1[:index]
    return fullPath1
    

def getRootNodes(nodeList):
    '''given a list of dag nodes, return a list containing only those nodes parented to the
    scene root'''
    rootNodes = []
    for node in nodeList:
        par = cmds.listRelatives(node,p=True)
        if not par:
            nodeTypes = cmds.nodeType(node,i=True)
            if 'dagNode' in nodeTypes:
                rootNodes.append(node)
    return rootNodes
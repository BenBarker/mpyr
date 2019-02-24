'''functions for working with curves and surfaces'''
import maya.cmds as cmds

def curveFromNodes(nodeList):
    '''given a list of nodes make and return a 1-degree curve passing through those transforms'''
    positions = []
    for node in nodeList:
        positions.append(cmds.xform(node,q=True, t=True, ws=True))
    return cmds.curve(d = 1, p=positions)
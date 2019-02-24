'''helpers for working with maya deformers'''
import os
import xml.etree.ElementTree
import maya.cmds as cmds
import maya.mel as mel

def saveSkinWeights(mesh,path,force=False):
    '''wrapper for deformerWeights command, however will attempt to
    find skinCluster if none specified.
    mesh: input mesh or skinCluster node
    path: output path for xml file
    force: if False then file will no be overwritten
    remap: regular expression, passed through to command (see deformerWeights cmd docs)
    '''
    #check paths
    fileDir,fileName=os.path.split(path)
    if not os.path.exists(fileDir) and not os.path.isdir(fileDir):
        raise RuntimeError('Directory %s not found to save skin weights'%fileDir)
    if os.path.exists(path) and not force:
        raise RuntimeError('Skin weights file %s already exists, use force=True to overwrite'%path)
    if not cmds.objExists(mesh):
        raise RuntimeError('mesh or skincluster %s not found, cannot save weights'%mesh)
    #check/find skinCluster node
    skinCluster = None
    if cmds.nodeType(mesh) == 'skinCluster':
        skinCluster=mesh
    else:
        skinCluster = mel.eval('findRelatedSkinCluster("%s");'%mesh)
        if not skinCluster:
            raise RuntimeError('skinCluster not found on mesh %s'%mesh)

    cmds.deformerWeights(fileName,path=fileDir,deformer=skinCluster,export=True)

def loadSkinWeights(mesh,path):
    '''wrapper for deformerWeights command, however will parse xml,
    find joints, and create skinCluster if none is specified
    mesh: mesh or skinCluster node to load onto (if mesh, skinCluster will be created)
    path: path to xml file
    '''
    #check paths
    fileDir,fileName=os.path.split(path)
    if not os.path.exists(path) and not os.path.isfile(path):
        raise RuntimeError('Skin weights file %s not found'%path)

    if not cmds.objExists(mesh):
        raise RuntimeError('Node not found to load skinWeights: %s'%mesh)
    #check node name/type
    skinCluster=None
    if cmds.nodeType(mesh)=='skinCluster':
        skinCluster=mesh
    else:
        #create skinCluster
        joints=getJointsFromSkinFile(path)
        if not joints:
            raise RuntimeError('Could not find joints in skinweights xml:%s'%path)
        joints.append(mesh)
        skinCluster=cmds.skinCluster(*joints,tsb=True)[0]

    cmds.deformerWeights(fileName,path=fileDir,deformer=skinCluster,im=True)

def getJointsFromSkinFile(path):
    '''given a skinweights xml file return joint names in a list'''
    root = xml.etree.ElementTree.parse(path).getroot()
    joints=[]
    for weightHeader in root.findall('weights'):
        joints.append(weightHeader.get('source'))
    return joints


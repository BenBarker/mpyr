'''
library functions for working with rigs, useful for animation
tools, like on a marking menu.
'''
import maya.cmds     as cmds
import maya.OpenMaya as om

import rigmath   
import attr
import ctrl
import name

def getSelectedCtrls():
    '''return a list of selected ctrls'''
    sel = cmds.ls(sl=True) or []
    return [x for x in sel if ctrl.isCtrl(x)]

def getAllCtrlsByName(filter=None):
    '''return a list of all ctrls. Optional name filter'''
    ctrlList = []
    for obj in cmds.ls(type='curveShape'):
        par = cmds.listRelatives(obj,p=True)[0]
        if ctrl.isCtrl(par):
            if filter and not filter in par:
                continue
            ctrlList.append(par)
    return ctrlList
    
def getAllCtrlsByParent(obj):
    '''given an object return all ctrls underneath it (possibly including itself)'''
    ctrlList = []
    if ctrl.isCtrl(obj): ctrlList.append(obj)
    for child in cmds.listRelatives(obj,ad=True) or []:
        if ctrl.isCtrl(child): ctrlList.append(child)
    return ctrlList  
    
def getCharacter(obj):
    '''given an object in a character return the top node of the rig.
    Returns None if not found.'''
    fullName = cmds.ls(obj,l=True)[0]
    nameParts = fullName.split('|')
    nameParts.reverse()
    for part in nameParts:
        if cmds.objExists(part + ".isRig"):
            return part
    return None
 
def getLimbSet(ctrlName):
    '''given a ctrl, get the main object set for the limb'''
    return cmds.listSets(object=getCtrlSet(ctrlName))[0]

def getCtrlSet(ctrlName):
    '''given a ctrl, return the ctrl object set. This is the
    set under the limb set that is ctrlsFK, IK, etc.
    '''
    return cmds.listSets(object=ctrlName)[0]

def getLimbCtrls(ctrlName):
    '''given a ctrl return a list of all the ctrls in that limb'''
    ctrls = []
    limbSet = getLimbSet(ctrlName)
    allSets = cmds.sets(limbSet,q=True)
    for ctrlSet in allSets:
        for obj in cmds.sets(ctrlSet,q=True):
            if ctrl.isCtrl(obj):
                ctrls.append(obj)
    return ctrls
    
def getJointFromCtrl(ctrlName):
    '''given a ctrl find the joint it is driving'''
    #put nodeTypes and their output attrs here
    cnsAttrs = {
        'pointConstraint':['ctx','cty','ctz'],
        'orientConstraint':['crx','cry','crz'],
        'parentConstraint':['ctx','cty','ctz','crx','cry','crz']
        }
    for attr in ('t','r'):
        for axis in ('','x','y','z'):
            connections = cmds.listConnections('%s.%s%s'%(ctrlName,attr,axis),s=0,d=1) or []
            for connection in connections:
                #test direct connection
                if cmds.nodeType(connection) == 'joint':
                    return connection
                #test other nodes
                try:
                    for output in cnsAttrs[cmds.nodeType(connection)]:
                        drivenObj = cmds.listConnections(connection+"."+output, s=0,d=1)
                        if not drivenObj:
                            continue
                        elif cmds.nodeType(drivenObj[0]) == 'joint':
                            return drivenObj[0]
                except KeyError:
                    continue
    return None
    
def resetCtrl(ctrlName):
    '''reset the given ctrl'''
    for attr in ('s','r','t'):
        for axis in ('x','y','z'):
            dv = 0.0
            if attr == 's':
                dv = 1.0
            try:
                cmds.setAttr(ctrlName + ".%s%s"%(attr,axis),dv)
            except RuntimeError:
                pass
    #todo: user attrs
    
def resetSelectedCtrls():
    '''reset the current selection of ctrls'''
    for ctrlName in getSelectedCtrls():
        resetCtrl(ctrlName)
    
def resetLimb(ctrlName):
    '''given a ctrl reset all ctrls in that limb'''
    for lctrl in getLimbCtrls(ctrlName):
        resetCtrl(lctrl)
        
def resetSelectedLimb():
    '''reset all limbs involved in the current ctrl selection'''
    for ctrlName in getSelectedCtrls():
        resetLimb(ctrlName)
                
def resetCharacter(obj):
    '''given a obj in a character reset all ctrls in that character'''
    for charCtrl in getAllCtrlsByParent(getCharacter(obj)):
        resetCtrl(charCtrl)
        
def resetSelectedCharacter():
    '''reset the currently selected character(s)'''
    alreadyDone = []
    for ctrlName in getSelectedCtrls():
        character = getCharacter(ctrlName)
        if character in alreadyDone:
            continue
        alreadyDone.append(character)
        resetCharacter(ctrlName)
        
def addPickParent(ctrlName,parent):
    '''add a pickwalk parent to the given ctrl'''
    if not cmds.objExists(ctrlName + ".pickParents"):
        cmds.addAttr(ctrlName,ln='pickParents',at='message',multi=True)
    if not cmds.objExists(parent + ".pickChildren"):
        cmds.addAttr(parent,ln='pickChildren',at='message',multi=True)
    childIndex,parentIndex,idx = (0,0,0)
    childCons = cmds.listConnections(parent + ".pickChildren[%s]"%idx,s=0,d=1) or []
    if ctrlName in childCons:
        return
    childIndex = len(childCons)
    parCons = cmds.listConnections(ctrlName + ".pickParents[%s]"%idx,s=0,d=1) or []
    if parent in parCons:
        return
    parentIndex = len(parCons)
    cmds.connectAttr(
        parent + ".pickChildren[%s]"%childIndex, 
        ctrlName + ".pickParents[%s]"%parentIndex,
        f=True) 
    
def addPickChild(ctrlName,child):
    '''add a pickwalk child to the given ctrl'''
    addPickParent(child,ctrlName)
    
def getPickParents(ctrlName):
    '''return the given ctrl's pick Parents as a list'''
    if cmds.objExists(ctrlName + ".pickParents"):
        return cmds.listConnections(ctrlName + ".pickParents",s=1,d=0) or []
    return []
    
def getPickChildren(ctrlName):
    '''return the given ctrl's pick children as a list'''
    if cmds.objExists(ctrlName + ".pickChildren"):
        return cmds.listConnections(ctrlName + ".pickChildren",s=0,d=1) or []
    return []
    
def pickWalkUp(ctrls=None,add=False):
    '''performs a pickwalk up. If add = True the selection is added instead of replaced
    If no ctrl list is given then the current selection is used.
    '''
    if not ctrls:
        try:
            ctrls = cmds.ls(sl=True)
        except TypeError:
            return 
    newSelectionList = []
    if add:
        newSelectionList = cmds.ls(sl=True)
    for ctrlName in ctrls:
        pars = getPickParents(ctrlName)
        if pars:
            newSelectionList.extend(pars)
    if newSelectionList:
        cmds.select(newSelectionList,r=True)
    
        
def pickWalkDown(ctrls=None,add=False):
    '''performs a pickwalk down. If add=True the selection is added instead of replaced
    If no ctrl list is given the current selection is used
    '''
    if not ctrls:
        try:
            ctrls = cmds.ls(sl=True)
        except TypeError:
            return
    newSelectionList = []
    if add:
        newSelectionList = cmds.ls(sl=True)
    for ctrlName in ctrls:
        children = getPickChildren(ctrlName)
        if children:
            newSelectionList.extend(children)
    if newSelectionList:
        cmds.select(newSelectionList,r=True)
            
def mirrorCtrl(ctrlName):
    '''copy this ctrl's pose onto its mirror ctrl'''
    opCtrl = ctrl.findMirrorCtrl(ctrlName)
    if not opCtrl:
        return
    mirrorInfo = ctrl.getMirrorInfo(ctrlName)
    #print "mirrorInfo",mirrorInfo
    if not mirrorInfo:
        #print "no mirror info"
        return
    #mirror to opCtrl
    transmult = -1
    if opCtrl == ctrlName:
        transmult = 1
    for index,attr in enumerate(['tx','ty','tz']):
        try:
            cmds.setAttr(opCtrl+"."+attr, cmds.getAttr(ctrlName+"."+attr) * mirrorInfo[index]*transmult)
        except Exception, e:
            pass
    for index,attr in enumerate(['rx','ry','rz']):
        try:
            cmds.setAttr(opCtrl+"."+attr, cmds.getAttr(ctrlName+"."+attr) * mirrorInfo[index]*-1)
        except Exception, e:
            pass
            
def mirrorSelectedCtrls():
    '''mirror each ctrl that is selected'''
    for ctrlName in getSelectedCtrls():
        mirrorCtrl(ctrlName)
        
def mirrorLimb(ctrlName):
    '''given a ctrl copy its entire limb's pose onto the mirror limb'''
    for lctrl in getLimbCtrls(ctrlName):
        mirrorCtrl(lctrl)
        
def mirrorSelectedLimbs():
    '''mirror every limb involved in the current ctrl selection'''
    for ctrlName in getSelectedCtrls():
        mirrorLimb(ctrlName)
    
def selectLimb(ctrlName):
    '''given a ctrl select the entire limb ctrls'''
    cmds.select(getLimbCtrls(ctrlName),r=True)
    
def selectSelectedLimbs():
    '''select a limbs involved in the current ctrl selection'''
    selList = []
    for ctrlName in getSelectedCtrls():
        selList.extend(getLimbCtrls(ctrlName))
    list(set(selList))
    cmds.select(selList,r=True)
    
def selectCharacter(ctrlName):
    '''given a ctrl in a character select all ctrls in that character'''
    cmds.select(getAllCtrlsByParent(getCharacter(ctrlName)),r=True)
    
def selectSelectedCharacters():
    '''convert the current selection to characters'''
    selList = []
    alreadyDoneChars = []
    for ctrlName in getSelectedCtrls():
        charName = getCharacter(ctrlName)
        if charName in alreadyDoneChars:
            continue
        alreadyDoneChars.append(charName)
        selList.extend(getAllCtrlsByParent(charName))
    list(set(selList))
    cmds.select(selList,r=True)
    
def keyCtrl(ctrlName):
    '''add a keyframe to the ctrl'''
    cmds.setKeyframe(ctrlName,hierarchy='none',controlPoints=False,shape=False,breakdown=0)
    
def keyLimb(ctrlName):
    '''given a ctrl key the entire limb'''
    for kctrl in getLimbCtrls(ctrlName):
        keyCtrl(kctrl)
        
def keySelectedLimb():
    '''key every limb involved in the current selection'''
    for ctrlName in getSelectedCtrls():
        keyLimb(ctrlName)
        
def keySelectedCharacter():
    '''key every ctrl on every character involved in the current selection'''
    alreadyDoneChars = []
    for ctrlName in getSelectedCtrls():
        charName = getCharacter(ctrlName)
        if charName in alreadyDoneChars:
            continue
        alreadyDoneChars.append(charName)
        allCtrlsInChar = getAllCtrlsByParent(charName)
        for charCtrl in allCtrlsInChar:
            keyCtrl(charCtrl)
            
def snapIKFK(ikctrl, resetPV=False, pvPosMult= 2):
    '''
    Given an ik ctrl, snap the ik to the fk.  Uses messages on the ikctrl to find fk ctrls.
    resetPV: If True, zero out the pv transforms 
    pvPosMult: increase distance of poleVector control. Doesn't affect IK solution, just distance.
    '''

    # Get the controls from the ik.message
    startFK = cmds.listConnections(ikctrl+".startFK")[0]
    midFK = cmds.listConnections(ikctrl+".midFK")[0]
    endFK = cmds.listConnections(ikctrl+".endFK")[0]
    
    pv = cmds.listConnections(ikctrl+".pv")[0]
    
    #Align IK ctrl to end FK ctrl straight up
    cmds.xform(ikctrl,ws=True,m=cmds.xform(endFK,q=True,ws=True,m=True))
    
    ## Pole Vector ##
    # Get vector info as array
    sVecRaw = cmds.xform(startFK, worldSpace=True, q=True, t=True)
    mVecRaw = cmds.xform(midFK, worldSpace=True, q=True, t=True)
    eVecRaw = cmds.xform(endFK, worldSpace=True, q=True, t=True)
    
    # Make the array a vector
    sVec = om.MVector(sVecRaw[0], sVecRaw[1], sVecRaw[2])
    mVec = om.MVector(mVecRaw[0], mVecRaw[1], mVecRaw[2])
    eVec = om.MVector(eVecRaw[0], eVecRaw[1], eVecRaw[2])
    
    midPoint = ( eVec + sVec ) / 2
    pvPos = ( mVec - midPoint ) * pvPosMult + midPoint
    
    #Move the PV Ctrl
    if resetPV:
        pvzero = pv.replace("Ctrl", "Zero")
        attr.unlockAndShow(pvzero, ["t", "r"])
        cmds.xform(pvzero, t=(pvPos[0],pvPos[1],pvPos[2]), worldSpace=True)
        cmds.xform(pvzero, ro=(0,0,0), worldSpace=True)
        attr.lockAndHide(pvzero, ["t", "r"])
    else:
        cmds.move(pvPos[0], pvPos[1], pvPos[2], pv)
    
    #Turn on IK
    attrctrl = cmds.listConnections(ikctrl+".attrCtrl")[0]
    cmds.setAttr(attrctrl+".ik", 1)
    
    return True
    
def snapFKIK(fkctrl):
    ''' given an fk ctrl, snap all of the fkctrls to the ik joints.  
    Uses messages on the ikctrl to find fk ctrls. 
    '''
    startIK = cmds.listConnections(fkctrl+".startIK")[0]
    midIK = cmds.listConnections(fkctrl+".midIK")[0]
    endIK = cmds.listConnections(fkctrl+".endIK")[0]
    
    startFK = cmds.listConnections(fkctrl+".startFK")[0]
    midFK = cmds.listConnections(fkctrl+".midFK")[0]
    endFK = cmds.listConnections(fkctrl+".endFK")[0]
    
    ik = cmds.listConnections(fkctrl+".IK")[0]
        
    cmds.xform(startFK,ws=True,m=cmds.xform(startIK,q=True,ws=True,m=True))
    cmds.xform(midFK,ws=True,m=cmds.xform(midIK,q=True,ws=True,m=True))
    cmds.xform(endFK,ws=True,m=cmds.xform(endIK,q=True,ws=True,m=True))
    
    # Turn on FK
    attrctrl = cmds.listConnections(fkctrl+".attrCtrl")[0]
    cmds.setAttr(attrctrl+".ik", 0)
    
def snapSelectedIKFKCtrl():
    '''Snap IK to FK'''
    sel = cmds.ls(sl=True)[0]
    attrctrl = cmds.listConnections(sel+".attrCtrl")[0]
    
    if sel.find("FK") != -1:
        snapIKFK(cmds.listConnections(attrctrl+".IK")[0])
    else:
        snapFKIK(cmds.listConnections(attrctrl+".startFK")[0])
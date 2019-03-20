'''
library functions for working with rigs, useful for animation
tools, like on a marking menu.
'''
import maya.cmds as cmds

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
        if cmds.objExists(part+'.isRig'):
            return part
    return None

def getLimbNode(ctrlName):
    '''given a ctrl (or any node parented under a limb) return the limb node transform'''
    #walk up hierarchy looking for named limb node
    fullName = cmds.ls(ctrlName,long=True)[0]
    allPars = fullName.split('|')
    allPars.reverse()
    for par in allPars:
        if par.endswith(name.LIMBNAME):
            return par
    return None

def getLimbNodeShape(ctrlName):
    '''given an object in the limb return the instanced shape node that holds animatable
    limb attributes'''
    limbNode = getLimbNode(ctrlName)
    if limbNode:
        return cmds.listRelatives(limbNode,s=True)[0]
    return None

def getCtrlSet(ctrlName):
    '''given a ctrl, return the ctrl object set. This is the
    set under the limb set that contains the ctrlsFK and ctrlsIK sets
    '''
    currentSets = cmds.listSets(object=ctrlName)

    for objSet in currentSets:
        #if the current set is ctrlsIK or ctrlsFK set, walk up one
        if objSet.endswith(name.CTRLSETFK) or objSet.endswith(name.CTRLSETIK):
            return cmds.listSets(object=objSet)[0]
        elif objSet.endswith(name.CTRLSET):
            return objSet
    return None

def getCtrlSetFK(ctrlName):
    '''given a ctrl, return the FK ctrl object set. A more specific version
    of getCtrlSet
    '''
    ctrlSet = getCtrlSet(ctrlName)
    contents = cmds.sets(ctrlSet,q=True)
    for objset in contents:
        if objset.endswith(name.CTRLSETFK):
            return objset
    return None

def getCtrlSetIK(ctrlName):
    '''given a ctrl, return the IK ctrl object set. A more specific version
    of getCtrlSet
    '''
    ctrlSet = getCtrlSet(ctrlName)
    contents = cmds.sets(ctrlSet,q=True)
    for objset in contents:
        if objset.endswith(name.CTRLSETIK):
            return objset
    return None

def getLimbCtrls(ctrlName):
    '''given a ctrl return a list of all the ctrls in that limb'''
    ctrls = []
    limbSet = getCtrlSet(ctrlName)
    allSets = cmds.sets(limbSet,q=True)
    if not allSets:
        raise RuntimeError("Limb ctrls set not found, check ctrl set names")
    for ctrlSet in allSets:
        for obj in cmds.sets(ctrlSet,q=True):
            if ctrl.isCtrl(obj):
                ctrls.append(obj)
    return ctrls
    
def getJointFromCtrl(ctrlName):
    '''given a ctrl find the joint it is driving, attempts to look through constraints'''
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
                        drivenObj = cmds.listConnections(connection+'.'+output, s=0,d=1)
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
                cmds.setAttr(ctrlName+'.%s%s'%(attr,axis),dv)
            except RuntimeError:
                pass
    for udAttr in cmds.listAttr(ctrlName,ud=True) or []:
        fullname = '%s.%s'%(ctrlName,udAttr)
        if not cmds.addAttr(fullname,q=True,k=True): #skip nonkeyable attributes
            continue
        #float cast in try/except to skip/supress warnings for non numeric attrs
        try:
            float(cmds.getAttr(fullname))
            default = cmds.addAttr(fullname,q=True,defaultValue=True)
            cmds.setAttr(fullname,default)
        except (TypeError,RuntimeError),e:
            continue
        
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
    if not cmds.objExists(ctrlName+'.pickParents'):
        cmds.addAttr(ctrlName,ln='pickParents',at='message',multi=True)
    if not cmds.objExists(parent+'.pickChildren'):
        cmds.addAttr(parent,ln='pickChildren',at='message',multi=True)
    childIndex,parentIndex,idx = (0,0,0)
    childCons = cmds.listConnections(parent+'.pickChildren[%s]'%idx,s=0,d=1) or []
    if ctrlName in childCons:
        return
    childIndex = len(childCons)
    parCons = cmds.listConnections(ctrlName+'.pickParents[%s]'%idx,s=0,d=1) or []
    if parent in parCons:
        return
    parentIndex = len(parCons)
    cmds.connectAttr(
        parent+'.pickChildren[%s]'%childIndex, 
        ctrlName+'.pickParents[%s]'%parentIndex,
        f=True) 
    
def addPickChild(ctrlName,child):
    '''add a pickwalk child to the given ctrl'''
    addPickParent(child,ctrlName)

def addSnapParent(ctrlName,parent):
    '''designate the parent(s) as the snap target for IK/FK snapping. 
    creates a msg attribute that the tools follow later.
    Multiple snap parents are only used for ik aim controls.
    '''
    if not cmds.objExists(ctrlName+'.snapParents'):
        cmds.addAttr(ctrlName,ln='snapParents',at='message',multi=True)
    if not cmds.objExists(parent+'.snapChildren'):
        cmds.addAttr(parent,ln='snapChildren',at='message',multi=True)
    childIndex,parentIndex= (0,0)
    childCons = cmds.listConnections(ctrlName+'.snapParents',s=1,d=0) or []
    if parent in childCons: #already connected
        return
    childIndex = len(childCons)
    parCons = cmds.listConnections(parent+'.snapChildren',s=0,d=1) or []
    parentIndex = len(parCons)
    cmds.connectAttr(
        parent+'.snapChildren[%s]'%parentIndex, 
        ctrlName+'.snapParents[%s]'%childIndex,
        f=True) 

def getPickParents(ctrlName):
    '''return the given ctrl's pick Parents as a list'''
    if cmds.objExists(ctrlName+'.pickParents'):
        return cmds.listConnections(ctrlName+'.pickParents',s=1,d=0) or []
    return []
    
def getPickChildren(ctrlName):
    '''return the given ctrl's pick children as a list'''
    if cmds.objExists(ctrlName+'.pickChildren'):
        return cmds.listConnections(ctrlName+'.pickChildren',s=0,d=1) or []
    return []

def addMirrorInfo(ctrl):
    '''given a ctrl add mirror info attributes to the ctrl, so poses can be mirrored.
    This method needs to do a dot product on each axis and set the mirror info based on
    if the axes point towards or away. Then it sets the mirror info attr to be 1 or -1
    based on that test (per axis). This is used later to mirror poses.

    Channel box attributes are copied over, and depending on the -1 or 1 they are reversed
    or straight copied.

    Mirror Info is added by the base rig class at the very end of building.
    '''
    other = findMirrorCtrl(ctrl)
    if not other:
        return
    mirrorInfo = [1,1,1]
    oXform = rigmath.Transform(other)
    cXform = rigmath.Transform(ctrl)
    cXform.reflect()
    cx = cXform.xAxis()
    cy = cXform.yAxis()
    cz = cXform.zAxis()
    ox = oXform.xAxis()
    oy = oXform.yAxis()
    oz = oXform.zAxis()
    
    if cx.dot(ox) <= 0:
        mirrorInfo[0] = -1
    if cy.dot(oy) <= 0:
        mirrorInfo[1] = -1
    if cz.dot(oz) <= 0:
        mirrorInfo[2] = -1
    
    if not cmds.objExists(ctrl+'.mirrorInfo'):
        cmds.addAttr(ctrl,ln='mirrorInfo',at='double3',k=False)
        cmds.addAttr(ctrl,ln='mirrorInfoX',at='double',parent='mirrorInfo',k=False)
        cmds.addAttr(ctrl,ln='mirrorInfoY',at='double',parent='mirrorInfo',k=False)
        cmds.addAttr(ctrl,ln='mirrorInfoZ',at='double',parent='mirrorInfo',k=False)
    
    cmds.setAttr(ctrl+'.mirrorInfo', mirrorInfo[0], mirrorInfo[1], mirrorInfo[2])

def getMirrorInfo(node):
    '''returns a list of the node's mirror info data, or None if attr not found'''
    if not cmds.objExists(node+'.mirrorInfo'):
        return None
    return cmds.getAttr(node+'.mirrorInfo')[0]

def findMirrorCtrl(node):
    '''return the mirror node for this node. 
    Return None if none found. Returns the same node on center nodes, since those get
    mirrored in place.
    '''
    nameOfCtrl = name.Name(node)
    preMirror = nameOfCtrl.get(noCheck=True)
    nameOfCtrl.mirror()
    postMirror = nameOfCtrl.get(noCheck=True)
    mirroredCtrlName = node.replace(preMirror,postMirror)
    if cmds.objExists(mirroredCtrlName):
        return mirroredCtrlName
    return None
    
def mirrorCtrl(ctrlName):
    '''copy this ctrl's pose onto its mirror ctrl'''
    opCtrl = findMirrorCtrl(ctrlName)
    if not opCtrl:
        return
    mirrorInfo = getMirrorInfo(ctrlName)
    if not mirrorInfo:
        return
    #mirror to opCtrl
    for index,attr in enumerate(['tx','ty','tz']):
        try:
            cmds.setAttr(opCtrl+'.'+attr, cmds.getAttr(ctrlName+'.'+attr) * mirrorInfo[index])
        except RuntimeError, e:
            pass #silently skip locked attrs
    for index,attr in enumerate(['rx','ry','rz']):
        try:
            cmds.setAttr(opCtrl+'.'+attr, cmds.getAttr(ctrlName+'.'+attr) * mirrorInfo[index]*-1)
        except RuntimeError, e:
            pass #silently skip locked attrs
            
def mirrorSelectedCtrls():
    '''mirror each ctrl that is selected'''
    for ctrlName in getSelectedCtrls():
        mirrorCtrl(ctrlName)
        
def mirrorLimb(ctrlName):
    '''given a ctrl copy its entire limb's pose onto the mirror limb'''
    for lctrl in getLimbCtrls(ctrlName):
        mirrorCtrl(lctrl)

    #copy over limb attributes (like FKIK switches)
    limbAttrNode = getLimbNodeShape(ctrlName)
    otherLimbNode = findMirrorCtrl(ctrlName)
    if limbAttrNode and otherLimbNode and (limbAttrNode!=otherLimbNode):
        for attr in cmds.listAttr(limbAttrNode,ud=True) or []:
            try:
                cmds.setAttr('%s.%s'%(otherLimbNode,attr), cmds.getAttr('%s.%s'%(limbAttrNode,attr)))
            except RuntimeError:
                print 'failed to mirror limb attribute %s.%s'%(limbAttrNode,attr)

def mirrorSelectedLimbs():
    '''mirror every limb involved in the current ctrl selection'''
    for ctrlName in getSelectedCtrls():
        mirrorLimb(ctrlName)

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

def getAimVector(start,mid,end,distance=0.5):
    '''Given three points (like shoulder,elbow,wrist joints) compute vector for aim
    location. This can be used to create/snap IK aim in a way that won't move an existing
    chain. Distance is a cosmetic multiplier.
    Returns Vector object of aim position.
    '''
    startV = rigmath.Vector(start)
    midV = rigmath.Vector(mid)
    endV = rigmath.Vector(end)
    chainV = endV-startV
    upperV = midV-startV
    chainLength = chainV.length()
    chainV.normalize()
    upperV.normalize()
    chainNormal = chainV.cross(upperV)
    elbowV = chainNormal.cross(chainV)
    elbowV.normalize()

    #throw error if the chain isn't bent. Snapping becomes unpredictable.
    #This might still need to be lowered.
    print(abs(chainV.dot(upperV)))
    if abs(chainV.dot(upperV)) > 0.998:
        raise RuntimeError("Cannot calculate aim, is chain hyper extended?")

    aimV = elbowV*chainLength*distance #get an aethetic distance from the chain
    aimV += midV 
    return aimV
            
def snapIKFK(ikctrl):
    '''Given an ik ctrl, snap the ik to the fk for that limb.  Uses messages on the ikctrl to find fk ctrls.
    pvPosMult: increase distance of poleVector control. Doesn't affect IK solution, just distance.
    '''
    # get all IK ctrls
    ikCtrlSet = getCtrlSetIK(ikctrl) or [ikctrl]
    allIKCtrls = cmds.sets(ikCtrlSet,q=True)

    #loop through twice, first doing end ctrls, then doing aims
    results = dict()
    for ctrl in allIKCtrls:
        if not cmds.objExists(ctrl+'.snapParents'):
            results[ctrl]=None
            continue
        snapParents = cmds.listConnections(ctrl+'.snapParents',s=1,d=0) or []
        #if there is one snap parent this is an end effector ctrl
        #do a simple snap
        if len(snapParents)==1:
            results[ctrl]=cmds.xform(snapParents[0],q=True,ws=True,m=True)
            

    for ctrl in allIKCtrls:
        if not cmds.objExists(ctrl+'.snapParents'):
            results[ctrl]=None
            continue
        snapParents = cmds.listConnections(ctrl+'.snapParents',s=1,d=0) or []
        #Use three parents to compute aim position
        if len(snapParents)==3:
            aimV = getAimVector(snapParents[0],snapParents[1],snapParents[2])
            aimXform = rigmath.Transform(aimV)
            results[ctrl]=aimXform.get()

    #bug fix for some IK limbs that need multiple snaps to reach the goal
    #This is because IK hierarchies can be arbitrary, and it's difficult to determine
    #which controls move others, so this takes an iterative approach
    for i in range(4):
        for ctrl,value in results.iteritems():
            if not value:
                resetCtrl(ctrl)
            else:
                cmds.xform(ctrl,ws=True,m=value)

    # Turn on IK
    limbNode = getLimbNodeShape(allIKCtrls[0])
    cmds.setAttr(limbNode+'.'+name.FKIKBLENDATTR,1)

def snapFKIK(fkctrl):
    ''' given an fk ctrl, snap all of the fkctrls to the ik joints.  
    Uses messages on the ikctrl to find fk ctrls. 
    '''
    # get all IK ctrls
    fkCtrlSet = getCtrlSetFK(fkctrl) or [fkctrl]
    allFKCtrls = cmds.sets(fkCtrlSet,q=True)

    #loop through getting transforms, then apply them.
    results = dict()
    for ctrl in allFKCtrls:
        if not cmds.objExists(ctrl+'.snapParents'):
            results[ctrl]=None 
            continue
        snapParents = cmds.listConnections(ctrl+'.snapParents',s=1,d=0) or []
        if len(snapParents)==1:
            results[ctrl]=cmds.xform(snapParents[0],q=True,ws=True,m=True)
            
    for ctrl,value in results.iteritems():
        if not value:
            resetCtrl(ctrl)
        else:
            cmds.xform(ctrl,ws=True,m=value)
    
    # Turn on FK
    limbNode = getLimbNodeShape(allFKCtrls[0])
    cmds.setAttr(limbNode+'.'+name.FKIKBLENDATTR,0)
    
def snapSelectedIKFKCtrl():
    '''Snap IK to FK'''
    sel = cmds.ls(sl=True)[0]
    attrctrl = cmds.listConnections(sel+'.attrCtrl')[0]
    
    if sel.find('FK') != -1:
        snapIKFK(cmds.listConnections(attrctrl+'.IK')[0])
    else:
        snapFKIK(cmds.listConnections(attrctrl+'.startFK')[0])
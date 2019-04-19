'''helper functions for joint navigation/manipulation'''
import maya.cmds as cmds
import rigmath
import dag

def getTopJoint(node):
    '''given a node get the highest parent joint
    Raises RuntimeError on failure.
    '''
    allParents = cmds.listRelatives(node,p=True,f=True)
    if  allParents:
        parList = allParents[0].split('|')
        for par in parList:
            if not cmds.objExists(par):
                continue
            if cmds.nodeType(par) == 'joint':
                return par
    if cmds.nodeType(node) == 'joint':
        return node
    else:
        raise RuntimeError("'%s' has no parent joints nor is it a joint" % node)

def getJointList(startJoint,endJoint):
    '''return a list representing the chain between a given start and end joint'''
    allParents = cmds.listRelatives(endJoint,p=True,f=True)
    if not allParents:
        raise RuntimeError("'%s' has no parents, not part of chain." % endJoint)
        
    parList = allParents[0].split('|')
    if not startJoint in parList:
        raise RuntimeError("'%s' not a parent of '%s'" % (startJoint,endJoint))
    startIndex = parList.index(startJoint)
    jointList = parList[startIndex:]
    jointList.append(endJoint)
    return jointList

def getLongAxis(joint):
    '''given a joint return the axis ('x','y', or 'z') with the largest translate value.
    On oriented joints this will be the "down" axis of the joint as well'''
    axes='xyz'
    translates=[abs(x) for x in cmds.getAttr(joint+'.t')[0]]
    return axes[translates.index(max(translates))]

def getDownAxis(joint):
    '''given a joint return the axis ('x','y', or 'z') that points towards child.
    On oriented joints this will be the same as the long axis, but if orientation is
    not know this function is slower but still produces an accurate result. 
    Joints at the end of the chain will use their parent instead to determine downAxis. 
    Negative axes aren't specified, function just returns x y or z.'''
    axes='xyz'
    target = cmds.listRelatives(joint,type='joint')
    if not target:
        target = cmds.listRelatives(joint,p=True,type='joint')  
    if not target:
        raise RuntimeError("no child or parent joints on %s, cannot determine downAxis"%joint)
    thisVector=rigmath.Vector(joint)
    thisXform=rigmath.Transform(joint)
    targVector=rigmath.Vector(target[0])
    diff=thisVector-targVector
    diff.normalize()

    #compare alignment of local axes of transform to diff vector
    dots=[]
    for axis in (thisXform.xAxis(),thisXform.yAxis(),thisXform.zAxis()):
        dots.append(abs(diff.dot(axis)))
    return axes[dots.index(max(dots))]

def getChainLength(startJoint,endJoint):
    '''given a start and end joint return the length of the chain.'''
    joints=getJointList(startJoint,endJoint)
    distance=0.0
    for idx,joint in enumerate(joints):
        if idx==0:
            continue
        par=rigmath.Vector(joints[idx-1])
        cur=rigmath.Vector(joint)
        distance+=(par-cur).length()
    return distance
    
def getEndJoint(startJoint):
    '''return the lowest end joint of a given startJoint. Quits at a branch.'''
    endJoint = None
    while True:
        children = cmds.listRelatives(startJoint,type='joint')
        if not children:
            return endJoint
        if len(children) > 1:
            return endJoint
        startJoint = children[0]
        endJoint = startJoint
    return endJoint
    
def rotToOrient(jnt):
    '''copy rotation to orient, zeroes the joint basically'''
    #first get everything into rot
    orientToRot(jnt)
    
    oldOrder = cmds.getAttr(jnt + ".rotateOrder")
    rotOrders = ['xyz','yzx','zxy','xzy','yxz','zyx']
    cmds.xform(jnt,p=True,roo='xyz')
    oldRot = cmds.getAttr(jnt + ".rotate")[0]
    
    cmds.setAttr(jnt + ".jointOrient",oldRot[0],oldRot[1],oldRot[2])
    cmds.setAttr(jnt + ".rotate",0,0,0)
    
    cmds.xform(jnt,p=True,roo=rotOrders[oldOrder])
    
def orientToRot(jnt):
    '''copy orient to rotation'''
    origTransform = rigmath.Transform(jnt)
    cmds.setAttr(jnt + '.jointOrient',0,0,0)
    cmds.xform(jnt,ws=True,m=origTransform.get())
    
    
def orientJoint(joint,upObj=None,downAxis='x',upAxis='z'):
    '''orient a given joint. 
    Joint will point at it's child or -1 it's parent if no child or many children.
    UpAxis will be pointed at the upObj (which can also be a Vector), or if none then
    world up.
    '''
    if not upObj:
        upObj = rigmath.Vector(0,1e10,0)
    else:
        upObj = rigmath.Vector(upObj)
        
    par = cmds.listRelatives(joint,p=True,type='joint')
    children = cmds.listRelatives(joint,type='joint')
    if not par or not children or len(children) > 1:
        print 'end joint'
        cmds.setAttr(joint + ".jointOrient",0,0,0)
        cmds.setAttr(joint + ".rotate",0,0,0)
        return
    par = par[0]
    fosterPar = cmds.group(em=True,n='TEMPPAR',p=par)
    aimTarget = cmds.group(em=True,n='TEMPCHILD',p=fosterPar)
    upTarget = cmds.group(em=True,n='TEMPAIM')
    cmds.xform(fosterPar,ws=True,m=cmds.xform(par,q=True,ws=True,m=True))
    cmds.xform(aimTarget,ws=True,m=cmds.xform(children[0],q=True,ws=True,m=True))
    cmds.parent(children,fosterPar)
    
    
    cmds.setAttr(joint + ".jointOrient",0,0,0)

    aimCns = cmds.aimConstraint(aimTarget,joint,
        aimVector = (1,0,0),
        upVector = (0,1,0),
        worldUpType = 'object',
        worldUpObject = upTarget,
        maintainOffset=False
        )[0]
    #would prefer to use upVector instead of upObj, but doesn't seem to be updating?
    cmds.move(upObj.x,upObj.y,upObj.z,upTarget) 
        
    cmds.parent(children,joint)
    cmds.delete([fosterPar,aimTarget,aimTarget,aimCns])
    rotToOrient(joint)
    
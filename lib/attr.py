'''helpers for getting/setting/making/locking attributes on maya nodes'''
import maya.cmds as cmds

def hideAnimChannels(obj,lock=False):
        '''hide anim channels on given obj'''
        for attr in ('s','r','t'):
            for axis in ('x','y','z'):
                cmds.setAttr(obj + ".%s%s"%(attr,axis), keyable=False,channelBox=False,lock=lock)
        cmds.setAttr(obj + ".v", keyable=False,channelBox=False)
        
def matchAttr(src,target,attr):
    '''match the attr on the target to the same attr on src. Will work through locks.'''
    if not cmds.objExists(src + "." + attr):
        raise RuntimeError("Source object.attr not found: %s.%s"%(obj,attr))
    srcType = cmds.getAttr(src + "." + attr,type=True)
    
    if not cmds.objExists(target + "." + attr):
        raise RuntimeError("target object.attr not found: %s.%s"%(obj,attr))
    targetType = cmds.getAttr(target + "." + attr,type=True)
    
    if not srcType == targetType:
        raise RuntimeError("src and target attrs not the same type")
        
    locked = False
    if cmds.getAttr(target + "." + attr, lock=True):
        locked = True
        cmds.setAttr(target + "." + attr, lock=False)
        
    if srcType == 'string':
        val = cmds.getAttr(src + '.%s' % attr)
        print 'setting target to ' , target, attr,val
        cmds.setAttr(target + ".%s" % attr, val, type='string')
    else:
        if attr in 'srt':
            for axis in 'xyz ':
                cmds.setAttr(target + ".%s%s"%(attr,axis), cmds.getAttr(src + "%s.%s"%(attr,axis)))
        else:
            cmds.setAttr(target + ".%s"%attr, cmds.getAttr(src + ".%s"%attr))
    
    if locked:
        cmds.setAttr(target + "." + attr, lock=True)

def lockAndHide(obj, attrs):
    '''given an object and a list of attrs, lock and hide those attrs'''
    for aa in attrs:
        cmds.setAttr(obj+"."+aa, k=False, l=True )
        if (aa=="r"):
            cmds.setAttr(obj+".rx", k=False, l=True )
            cmds.setAttr(obj+".ry", k=False, l=True )
            cmds.setAttr(obj+".rz", k=False, l=True )
        if (aa=="t"):
            cmds.setAttr(obj+".tx", k=False, l=True )
            cmds.setAttr(obj+".ty", k=False, l=True )
            cmds.setAttr(obj+".tz", k=False, l=True )
        if (aa=="s"):
            cmds.setAttr(obj+".sx", k=False, l=True )
            cmds.setAttr(obj+".sy", k=False, l=True )
            cmds.setAttr(obj+".sz", k=False, l=True )

def unlockAndShow(obj, attrs):
    '''given an object and a list of attrs, unlock and show those attrs'''
    for aa in attrs:
        cmds.setAttr(obj+"."+aa, k=True, l=False )
        if (aa=="r"):
            cmds.setAttr(obj+".rx", k=True, l=False )
            cmds.setAttr(obj+".ry", k=True, l=False )
            cmds.setAttr(obj+".rz", k=True, l=False )
        if (aa=="t"):
            cmds.setAttr(obj+".tx", k=True, l=False )
            cmds.setAttr(obj+".ty", k=True, l=False )
            cmds.setAttr(obj+".tz", k=True, l=False )
        if (aa=="s"):
            cmds.setAttr(obj+".sx", k=True, l=False )
            cmds.setAttr(obj+".sy", k=True, l=False )
            cmds.setAttr(obj+".sz", k=True, l=False )

def connectWithReverse(src,targ,force=False):
    '''Given a source 'obj.attr' and a target 'obj.attr', connect with a reverse between.
    Returns the created reverse node. Input should be between 0 and 1
    '''
    revNode = cmds.createNode('reverse', n=src.replace('.','_')+"_reverse")
    cmds.connectAttr(src,revNode+'.inputX')
    cmds.connectAttr(revNode+'.outputX',targ,f=force)
    return revNode

def connectWithMult(src, targ, mult=-1,force=False):
    '''Given a source 'obj.attr' and a target 'obj.attr', connect with and multiplier between.
    Returns the created multiplyDivide node. mult defaults to -1
    '''
    mdNode = cmds.createNode("multiplyDivide", n=src.replace('.','_')+"_multiply")
    cmds.setAttr(mdNode+".input2X", mult)
    cmds.connectAttr(src, mdNode+".input1X")
    cmds.connectAttr(mdNode+".outputX", targ,f=force)
    return mdNode

def connectWithAdd(src,targ,add=1,force=False):
    '''Given a source 'obj.attr' and a target 'obj.attr', connect with an addition between.
    Returns the created addDoubleLinear node. add defaults to 1
    '''
    addNode = cmds.createNode('addDoubleLinear',n=src.replace('.','_')+"_adder")
    cmds.setAttr(addNode+'.input2',add)
    cmds.connectAttr(src,addNode+'.input1')
    cmds.connectAttr(addNode+'.output',targ,f=force)
    return addNode


def addAttrSwitch(attr, type="long", max=1, min=0, value=0, keyable=True, niceName="", node="", lock=False ):
    '''Add a default 0-1 animatable attribute to a node and return the attr name'''
    attr = attr.split(".")
    if len(attr) > 1:
        node = attr[0]
        attr = attr[1]
    else:
        if cmds.objExists(node) != True:
            raise RuntimeError( "Error attribute.add(): Invalid node specified.")
        attr = attr[0]
    argDict = {'ln':attr,'k':keyable,'at':type}
        
    if max:
        argDict['max'] = max
    if min:
        argDict['min'] = min
    if niceName:
        argDict['nn']=niceName
    if type=="message":
        cmds.addAttr(node, ln=attr, at=type)
    else:    
        cmds.addAttr(node, **argDict )
    newattr = "%s.%s" % (node, attr)  
    
    try:
        cmds.setAttr(newattr, value)
    except RuntimeError:
        pass
        
    cmds.setAttr(newattr, l=lock)
    return newattr
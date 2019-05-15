'''helper functions for working with contraints'''
import maya.cmds as cmds

def blendConstraint(driver1,driver2,driven,blendAttr,cnsType='parent', **kwargs):
    '''given two drivers, a driven, and an attribute that goes from 0-1, make a blended 
    constraint setup. All other keyword arguments are passed through to the maya cns command.

    BlendAttr should be a string in the 'node.attrName' format. 
    The attr will be created if it doesn't exist.

    blend 0 = driver1, and blend 1 = driver2
    Returns the cns node.
    '''
    cnsFuncFac = {
        'parent':cmds.parentConstraint,
        'point':cmds.pointConstraint,
        'orient':cmds.orientConstraint,
        'scale':cmds.scaleConstraint,
        'aim':cmds.aimConstraint,
        }

    try:
        cnsFunc = cnsFuncFac[cnsType.lower()]
    except KeyError:
        raise TypeError('Unknown cns type %s'%cnsType)

    if not cmds.objExists(blendAttr):
        obj,attr = blendAttr.split('.')
        cmds.addAttr(obj,ln=attr,at='float',min=0,max=1,dv=1,k=True)

    #make the constraint
    cns = cnsFunc(driver1,driver2,driven,**kwargs)[0]
    cns = cmds.rename(cns,driven + "_blendCns%s"%cnsType.capitalize())

    #hook attr straight to w0
    cmds.connectAttr(blendAttr, cns + ".w1")

    #make reverse and hook to w1
    revNode = cmds.createNode('reverse',n=cns + "_Rev")
    cmds.connectAttr(blendAttr, revNode + ".inputX")
    cmds.connectAttr(revNode + ".outputX", cns + ".w0")

    return cns
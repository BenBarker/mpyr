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

def surfaceConstraint(self,obj,surf,path,stretchAmountNode,percentage):
    '''Given an object and a NURBS surface, attach object to surface.
    Returns created nodes like (poinOnSurface,aimCns)
    '''
    #Make nodes
    aimCns = cmds.createNode('aimConstraint',n=obj + "Cns")
    moPath = cmds.createNode('motionPath', n=obj + "MoPath")
    slider = cmds.createNode('addDoubleLinear',n=obj + "Slider")
    cmds.setAttr(moPath + ".uValue", percentage)
    closePnt = cmds.createNode('closestPointOnSurface', n=obj + "ClsPnt")
    posNode1 = cmds.pointOnSurface(surf,
        constructionHistory=True,
        normal=True,
        normalizedNormal=True, 
        normalizedTangentU=True, 
        normalizedTangentV=True, 
        parameterV=0.5, 
        parameterU=0.5, 
        turnOnPercentage=True
    ) 
    
    #Connect motion Path to closest point, then closest point to surface info node
    cmds.setAttr(moPath + ".fractionMode", 1) #distance instead of param
    cmds.connectAttr(path + ".worldSpace[0]", moPath + ".geometryPath")
    cmds.connectAttr(surf + ".worldSpace[0]", closePnt + ".inputSurface")
    cmds.connectAttr(moPath + ".xCoordinate", closePnt + ".ipx")
    cmds.connectAttr(moPath + ".yCoordinate", closePnt + ".ipy")
    cmds.connectAttr(moPath + ".zCoordinate", closePnt + ".ipz")
    cmds.connectAttr(closePnt + ".result.u", posNode1 + ".u")
    cmds.connectAttr(closePnt + ".result.v", posNode1 + ".v") 
    
    #Create Stretch Setup using stretchAmountNode node
    stretchCtrl = cmds.createNode("multDoubleLinear", n=obj + "StretchCtrl")
    cmds.setAttr(stretchCtrl + ".i1", percentage)
    cmds.connectAttr(stretchAmountNode + ".outputX",stretchCtrl + ".i2")
    cmds.connectAttr(stretchCtrl + ".o", slider + ".i1")
    cmds.connectAttr(slider + ".o", moPath + ".uValue")
    
    #Hook up surface info attrs to aimCns to calculate rotation values
    #Then hook pointOnSurface and aimCns to locator
    posNode1 = cmds.rename(posNode1,obj + 'SurfInfo')
    cmds.setAttr(aimCns + ".worldUpType", 3)
    cmds.connectAttr(posNode1 + ".position", obj + ".translate")
    cmds.connectAttr(posNode1 + '.tv',aimCns + '.target[0].targetTranslate')
    cmds.connectAttr(posNode1 + '.tu',aimCns + '.worldUpVector')
    for axis in ('X','Y','Z'):
        cmds.connectAttr(aimCns + ".constraintRotate" + axis, obj + ".rotate" + axis)
    cmds.parent(aimCns,obj) #just for tidyness, doesn't matter
    return (posNode1,aimCns,moPath,slider)
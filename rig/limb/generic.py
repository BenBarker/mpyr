'''generic limbs. Offsets, etc.'''

import maya.cmds as cmds
import mpyr.lib.rigmath as mpMath
import mpyr.lib.rig as mpRig
import mpyr.lib.joint as mpJoint
import mpyr.lib.nurbs as mpNurbs
import mpyr.lib.attr as mpAttr
import limbBase

class WorldOffset(limbBase.Limb):
    '''A character's root offset. 
    This is a special limb in that it's always built by the
    rig base class, on every character, and has no startJoint. It serves as a layout
    control and also as the 'world parent' of anything else in the rig.
    '''

    def begin(self):
        '''since this is a special limb, hardcode some names'''
        self.name.loc = 'M'
        self.name.part = 'World'
        limbBase.Limb.begin(self)
       
    def build(self):
        #make pyramids for world offsets
        ctrlXform = mpMath.Transform()
        ctrlXform.scale(2)
        zero, c1 = self.addCtrl('01',type='FK',shape='pyramid',parent=self.limbNode,shapeXform=ctrlXform)
        
        ctrlXform.scale(0.7)
        zero, c2 = self.addCtrl('02',type='FK',shape='pyramid',parent=c1,shapeXform=ctrlXform)
        
        ctrlXform.scale(0.7)
        zero, c3 = self.addCtrl('03',type='FK',shape='pyramid',parent=c2,shapeXform=ctrlXform)

        mpRig.addPickParent(c3,c2)
        mpRig.addPickParent(c2,c1)
        
class FKOffset(limbBase.Limb):
    '''simple offset control. One control driving one joint.
    Attrs:
     - translate: Offset will drive joints translate as well as rotate. Defalt True
     - useConstraint: use constraints instead of rotate connection. Slower, but sometimes
                      needed for good behavior when parent rotation is needed. Default True.
    '''
    def __init__(self):
        limbBase.Limb.__init__(self)
        self.translate = True
        self.useConstraint = True
        
    def begin(self):
        limbBase.Limb.begin(self)
        #sanity checks on start and endJoint
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)

    def addPin(self):
        self.pin = self.addPinParent()

    def build(self):
        self.addPin()
        
        zero,c1 = self.addCtrl('01',type='FK',shape='sphere',parent=self.pin,xform=self.startJoint)
        
        if self.useConstraint:
            cmds.orientConstraint(c1,self.startJoint,mo=True)
        else:
            for attr in ['rx','ry','rz']:
                cmds.connectAttr(c1+'.'+attr, self.startJoint+'.'+attr,f=True)
        if self.translate:
            cmds.pointConstraint(c1,self.startJoint,mo=True)
        cmds.parentConstraint(self.pin,zero,mo=True)

class FKOffsetBlend(FKOffset):
    '''version of FKOffset that uses a blended pin setup instead of a simple pin setup.
    useConstraint is forced True in this case.
    '''
    def addPin(self):
        self.pin = self.addPinBlend()

    def build(self):
        self.useConstraint = True #must be true for blend to work
        FKOffset.build(self)

class FKChain(limbBase.Limb):
    '''simple FK chain, given a start and endjoint create FK ctrls between'''
    def begin(self):
        limbBase.Limb.begin(self)

        #sanity checks on start and endJoint
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError('invalid endJoint: %s' % self.endJoint)
    def build(self):
        self.addPinBlend()
        self.addFKChain(self.startJoint,self.endJoint,self.pinBlend)

class FKCurlChain(FKChain):
    '''simple FK chain with addition of a 'curl' ctrl at the base that lets you rotate all ctrls
    at once.
    '''
    def build(self):
        FKChain.build(self)
        #add offset between each ctrl
        curls=list()
        for idx,ctrl in enumerate(self.ctrls):
            #get zero null:
            zero=cmds.listRelatives(ctrl,p=1)[0]
            self.name.desc='Curl%02d'%idx
            curlNull=cmds.group(em=True,n=self.name.get(),p=zero)
            cmds.xform(curlNull,ws=True,m=cmds.xform(zero,q=True,ws=True,m=True))
            cmds.parent(ctrl,curlNull)
            curls.append(curlNull)
        #make curl ctrl
        curlZero,curlCtrl = self.addCtrl('curl',type='FK',shape='spoon',parent=self.pinParent,xform=self.ctrls[0],size=3.5)
        mpAttr.lockAndHide(curlCtrl,'t')

        #connect curl ctrl
        for curl in curls:
            for axis in 'xyz':
                cmds.connectAttr(curlCtrl+'.r%s'%axis,curl+'.r%s'%axis)
         
class FKIKChain(limbBase.Limb):
    '''Simple FK and IK chain, with FKIK blend, meant for at least three joints (not single chain IK)
    Requires startJoint and endJoint
    '''
    def begin(self):
        limbBase.Limb.begin(self)

        #sanity checks on start and endJoint
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError('invalid endJoint: %s' % self.endJoint)

    def build(self):
        self.addPinBlend()
        self.addFKIKChain(self.startJoint,self.endJoint,self.pinBlend,self.pinWorld)

class FKTree(limbBase.Limb):
    '''Recursively rigs a joint chain with FK offsets. Requires a parent joint, rigs parent and all children.'''
    def begin(self):
        limbBase.Limb.begin(self)
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
    def build(self):
        self.addPinBlend()
        self.makeCtrl(self.startJoint,self.pinBlend)

    def makeCtrl(self,startJoint,parent):
        '''recursive function to build ctrls'''
        ctrlXform = mpMath.Transform()
        ctrlXform.scale(0.3,0.3,0.3)
        zero,c1 = self.addCtrl('%02d'%len(self.ctrls),type='FK',shape='box',parent=parent,xform=startJoint,shapeXform=ctrlXform)
        cmds.parentConstraint(c1,startJoint,mo=True)
        children = cmds.listRelatives(startJoint,type='joint') or []
        for child in children:
            childZero,childCtrl = self.makeCtrl(child,c1)
            mpRig.addPickParent(childCtrl,c1)
        return (zero,c1)

class NurbsStrip(limbBase.Limb):
    '''Limb that uses a NURBS strip to drive the joints.
    Attributes:
    numCtrls: The number of ctrls to make on the strip, default 5
    numSpans: the number of spans of the strip, default 5. Long strips may need more
    uMin: Where on the strip to begin placing ctrls, defaults 0. Range 0-1
    uMax: Where on the strip to end placing ctrls, defaults 1. Range 0-1
    '''
    def __init__(self):
        limbBase.Limb.__init__(self)
        self.stripWidth=1.0
        self.numCtrls=5
        self.numSpans=8
        self.uMin=0
        self.uMax=1


    def begin(self):
        limbBase.Limb.begin(self)
        #sanity checks
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError('invalid endJoint: %s' % self.endJoint)

    def build(self):
        self.addPinParent()
        self.addAttrLimb(ln='noStretch', at='float',min=0,max=1,dv=0,k=True,s=1)
        self.addAttrLimb(ln='slideAlong', at='float',min=-1,max=1,dv=0,k=True,s=1)
        jointList = mpJoint.getJointList(self.startJoint,self.endJoint)
        if len(jointList) < 2:
            raise RuntimeError('NurbsStrip requires at least 2 joints in chain. Got %s'%len(jointList))

        #Create NURBS strip by making curves along joints, and a cross section crv, then extruding
        crv=mpNurbs.curveFromNodes(jointList)
        crvShape=cmds.listRelatives(crv,s=1)[0]
        crossCurve = cmds.curve(d=1,p=[(0,0,-0.5 * self.stripWidth),(0,0,0.5 * self.stripWidth)],k=(0,1))
        cmds.select([crossCurve,crv],r=1)
        surf = cmds.extrude(ch=False,po=0,et=2,ucp=1,fpt=1,upn=1,rotation=0,scale=1,rsp=1)[0]
        cmds.delete([crv,crossCurve])
        self.name.desc='driverSurf'
        surf = cmds.rename(surf, self.name.get())
        cmds.parent(surf,self.noXform)

        #Rebuild strip to proper number of spans
        cmds.rebuildSurface(surf,ch=0,rpo=1,rt=0,end=1,kr=0,kcp=0,kc=1,sv=self.numSpans,su=0,du=1,tol=0.01,fr=0,dir=2)

        #make live curve on surface down the middle 
        #this is used later for noStretch
        curvMaker = cmds.createNode('curveFromSurfaceIso', n = surf+"CurveIso")
        cmds.setAttr(curvMaker + ".isoparmValue", 0.5)
        cmds.setAttr(curvMaker + ".isoparmDirection", 1)
        cmds.connectAttr(surf + ".worldSpace[0]", curvMaker + ".inputSurface")
        offsetCrvShp = cmds.createNode("nurbsCurve", n=crv + "_driverSurfCrvShape")
        offsetCrv = cmds.listRelatives(p=1)[0]
        offsetCrv = cmds.rename(offsetCrv,crv + "_driverSurfCrv")
        cmds.connectAttr(curvMaker + ".outputCurve", offsetCrvShp + ".create")
        cmds.parent(offsetCrv, self.noXform)

        #Measure curve length and divide by start length 
        #to get a normalized value that is useful later to control stretch
        crvInfo = cmds.createNode('curveInfo', n=offsetCrv + "Info")
        cmds.connectAttr(offsetCrv + ".worldSpace[0]", crvInfo + ".ic")
        arcLength = cmds.getAttr(crvInfo + ".al")
        stretchAmountNode = cmds.createNode('multiplyDivide', n=offsetCrv + "Stretch")
        cmds.setAttr(stretchAmountNode + ".op" , 2) #divide
        cmds.setAttr(stretchAmountNode + ".input1X", arcLength)
        cmds.connectAttr( crvInfo + ".al",stretchAmountNode + ".input2X")

        #Stretch Blender blends start length with current length
        #and pipes it back into stretchAmoundNode's startLength, so user can turn
        #stretch behavior on or off
        stretchBlender = cmds.createNode('blendColors', n =offsetCrv + "StretchBlender")
        cmds.setAttr(stretchBlender + ".c1r", arcLength)
        cmds.connectAttr(crvInfo + ".al", stretchBlender + ".c2r")
        cmds.connectAttr(stretchBlender + ".opr", stretchAmountNode + ".input1X")
        cmds.connectAttr(self.limbNode + ".noStretch",stretchBlender + ".blender")

        #attach joints to surface
        closestPoint = cmds.createNode('closestPointOnSurface',n='tempClose')
        cmds.connectAttr(surf + ".worldSpace[0]", closestPoint + ".inputSurface")
        for idx,jnt in enumerate(jointList):
            self.name.desc = 'jnt%02dOffset'%idx
            locator = cmds.spaceLocator(n=self.name.get())[0]
            cmds.setAttr(locator+'.localScale',self.stripWidth,self.stripWidth,self.stripWidth)
            cmds.parent(locator,self.noXform)
            #Use closest point to to find jnt's percent along the curve
            cmds.setAttr(closestPoint+'.ip',*cmds.xform(jnt,q=True, t=True, ws=True))
            percentage = cmds.getAttr(closestPoint+'.r.v')
            #attach to surface
            posNode,aimCnss,moPath,slider = self.attachObjToSurf(locator,surf,offsetCrv,stretchAmountNode,percentage)

            cmds.connectAttr(self.limbNode + ".slideAlong", slider + ".i2")
            cmds.parentConstraint(locator,jnt,mo=True)
        cmds.delete(closestPoint)

        #add controls.These drive new joints which skinCluster the NURBS strips
        stripJoints = []
        stripJointParent = cmds.createNode('transform',n=crv + "_stripJoints",p=self.noXform)
        ctrlParent = cmds.createNode('transform',n=crv+"_Ctrls",p=self.pinParent)
        cmds.xform(ctrlParent,ws=True,m=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1])
        
        prevCtrl=None
        for i in range(self.numCtrls):
            ctrlXform=mpMath.Transform(jointList[0])
            zero,ctrl = self.addCtrl('Ctrl%02d'%i,type='FK',shape='box',parent=ctrlParent,xform=ctrlXform)
            ctrlXform.scale(0.8,0.8,0.8)
            tZero,tCtrl=self.addCtrl('TweakCtrl%02d'%i,type='FK',shape='cross',parent=ctrl,xform=ctrlXform)
            
            #Make the new joint for the control to drive
            cmds.select(clear=True)
            self.name.desc='StripJnt%02d'%i
            jnt = cmds.joint(p=(0,0,0),n=self.name.get())
            cmds.parentConstraint(tCtrl,jnt,mo=False)
        
            #briefly attach ctrls to strip to align them
            percentage = float(i)/(self.numCtrls-1.0)
            if i > 0 and i < self.numCtrls-1:
                percentage = self.uMin + (percentage * (self.uMax-self.uMin))
            cmds.delete(self.attachObjToSurf(zero,surf,offsetCrv,stretchAmountNode,percentage))
            cmds.parent(jnt,stripJointParent)
            stripJoints.append(jnt)

            if prevCtrl:
                cmds.parent(zero,prevCtrl)
                mpRig.addPickParent(ctrl,prevCtrl)
            prevCtrl=ctrl
        
        #skin strip to controls
        #Can get some different behavior by chaning the strip's weights
        #or perhaps using dual quat. mode on the skinCluster
        skinObjs = stripJoints + [surf]
        cmds.skinCluster(skinObjs,
            bindMethod=0, #closest Point
            sm=0, #standard bind method
            ih=True, #ignore hierarchy
        )    
        
    def attachObjToSurf(self,obj,surf,path,stretchAmountNode,percentage):
        '''Given an object and a surface, attach object.
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



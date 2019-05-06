'''Leg Limbs, such as biped five joint leg'''
import math
import maya.cmds as cmds
import mpyr.lib.rigmath as mpMath
import mpyr.lib.joint as mpJoint
import mpyr.lib.name as mpName
import mpyr.lib.attr as mpAttr
import mpyr.lib.rig as mpRig
import mpyr.lib.ctrl as mpCtrl
import limbBase

class LegFKIK(limbBase.Limb):
    '''Leg with three joints, hip/knee/ankle, and a foot with ball and toetip.
    Startjoint = hip and endjoint=toe tip
    An optional 'heel' attribute can be specified to position the heel pivot, otherwise it will be guessed.
    '''
    def __init__(self,*args,**kwargs):
        limbBase.Limb.__init__(self,*args,**kwargs)
        self.heel = None

    def begin(self):
        limbBase.Limb.begin(self)

        #sanity checks
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError('invalid endJoint: %s' % self.endJoint)

    def build(self):
        jointList = mpJoint.getJointList(self.startJoint,self.endJoint)
        if len(jointList) < 5:
            raise RuntimeError('LegFKIK requires at least 5 joints in chain: hip/knee/ankle/ball/toetip. Got %s'%len(jointList))
        
        #start with standard blend setup and FKIKChain
        self.addPinBlend()
        legCtrls = self.addFKIKChain(jointList[0],jointList[-3],self.pinBlend,self.pinWorld)

        #add FK offsets to ball
        ballFKZero,ballFKCtrl = self.addCtrl('%02d'%len(jointList[:-2]),type='FK',shape='sphere',parent=legCtrls[-3],xform=jointList[-2])
        mpAttr.lockAndHide(ballFKCtrl,'t')
        cmds.orientConstraint(ballFKCtrl,jointList[-2],mo=True)

        #addFKIKChain returns list with [...,lastFK,IKAim,IKEnd], so grabbing last FK for pick parent:
        mpRig.addPickParent(ballFKCtrl,legCtrls[-3])

        #create classic 'reverse foot' setup
        if self.heel:
            heelPos = mpMath.Transform(self.heel)
        else:
            rigLog.warning('No ".heel" joint specified on LegFKIK, guessing pivot')
            #take the ball->toe length, double it, and go back from the ball that much
            heelOffset = mpMath.Vector(jointList[-2]) #ball
            heelOffset -= mpMath.Vector(jointList[-1]) #minus toe
            heelOffset *= 2
            heelOffset + mpMath.Vector(jointList[-2]) #add back to ball
            heelPos = mpMath.Transform(jointList[-2]) #heel equal ball plus our new vector
            heelPos += heelOffset

        #Make ik single chains for ball and toe
        self.name.desc = 'ikHandleBall'
        ballHandle,ballEffector = cmds.ikHandle(n=self.name.get(),solver='ikSCsolver',sj=jointList[-3],ee=jointList[-2])
        self.name.desc = 'ikHandleToe'
        toeHandle,toeEffector = cmds.ikHandle(n=self.name.get(),solver='ikSCsolver',sj=jointList[-2],ee=jointList[-1])
        
        self.name.desc = 'ballEffector'
        ballEffector = cmds.rename(ballEffector,self.name.get())
        cmds.parent(ballHandle,self.noXform)
        self.name.desc = 'toeEffector'
        toeEffector = cmds.rename(toeEffector,self.name.get())
        cmds.parent(toeHandle,self.noXform)

        #Make foot controls
        #These transforms are for cosmetic SRT of the foot controls
        anklePos = mpMath.Vector(jointList[-3])
        heelVec = mpMath.Vector(heelPos)
        footCtrlXform = mpMath.Transform()
        footCtrlXform.scale(2,0.4,4)
        footCtrlXform.translate(0,heelVec.y-anklePos.y,0)
        toeCtrlXform = mpMath.Transform()
        toeCtrlXform.setFromEuler(0,90,0)

        footZero,footCtrl = self.addCtrl('Foot',shape='cube',type='IK',parent=self.pinWorld,xform=mpMath.Vector(jointList[-3]),shapeXform=footCtrlXform)
        heelZero,heelCtrl = self.addCtrl('Heel',shape='circle',type='IK',parent=footCtrl,xform=heelPos,shapeXform=toeCtrlXform)
        toeTipZero,toeTipCtrl = self.addCtrl('ToeTip',shape='circle',type='IK',parent=heelCtrl,xform=jointList[-1],shapeXform=toeCtrlXform)
        ballZero,ballCtrl = self.addCtrl('Ball',shape='circle',type='IK',parent=toeTipCtrl,xform=jointList[-2],shapeXform=toeCtrlXform)

        cmds.parentConstraint(ballCtrl,ballHandle,mo=True)
        cmds.parentConstraint(toeTipCtrl,toeHandle,mo=True)

        #Blend already exists, but this will grab the right attr
        FKIKblender = self.addAttrLimb(ln=mpName.FKIKBLENDATTR, at='float',min=0,max=1,dv=0,k=True)
        cmds.connectAttr(FKIKblender, ballHandle+'.ikBlend')
        cmds.connectAttr(FKIKblender, toeHandle+'.ikBlend')

        #constrain legIK endctrl to new foot ctrl
        ankleIKCtrl = legCtrls[-1]
        mpAttr.unlockAndShow(ankleIKCtrl,'r')
        cmds.parentConstraint(ballCtrl,ankleIKCtrl,mo=True)

        #swap out foot for old IK handle ctrl
        #First retrieve effector, handle, aim, and endNull from IK system
        effector,handle=mpJoint.getIKNodes(jointList[-3])
        handleCns = cmds.listConnections(handle+'.tx',s=1,d=0)[0]
        endNull = cmds.listConnections(handleCns+'.target[0].targetTranslate',s=1,d=0)[0]
        endNullCns = cmds.listConnections(endNull+'.tx',s=1,d=0)[0]
        aimCtrl = legCtrls[-2]
        aimCtrlZero = cmds.listRelatives(aimCtrl,p=True)[0]

        #delete old aimCtrl blend cns
        cmds.delete(cmds.listConnections(aimCtrlZero+'.tx',s=1,d=0)[0])
        cmds.pointConstraint(self.pinWorld,footCtrl,aimCtrlZero,mo=True)

        #delete old IK ctrl and wire IK to new foot ctrl
        cmds.delete(endNullCns)
        cmds.parentConstraint(ballCtrl,endNull,mo=True)
        self.deleteCtrl(legCtrls[-1])

        #add new pickwalk/snap info
        mpRig.addPickParent(footCtrl,legCtrls[-2])
        mpRig.addPickParent(ballCtrl,footCtrl)
        mpRig.addPickParent(toeTipCtrl,ballCtrl)
        mpRig.addPickParent(heelCtrl,toeTipCtrl)

        #Make some nulls to act as snap targets. This is because IK and FK controls might have different axis order or initial positions.
        self.name.desc='ikAnkleSnapTarget'
        ikAnkleSnapTarget = cmds.group(em=True,n=self.name.get(),p=legCtrls[-3]) 
        cmds.xform(ikAnkleSnapTarget,ws=True,m=cmds.xform(footCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(footCtrl,ikAnkleSnapTarget)

        self.name.desc='ikBallSnapTarget'
        ikBallSnapTarget = cmds.group(em=True,n=self.name.get(),p=ballFKCtrl) 
        cmds.xform(ikBallSnapTarget,ws=True,m=cmds.xform(ballCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(ballCtrl,ikBallSnapTarget)

        self.name.desc='fkBallSnapTarget'
        fkBallSnapTarget = cmds.group(em=True,n=self.name.get(),p=ballCtrl) 
        cmds.xform(fkBallSnapTarget,ws=True,m=cmds.xform(ballFKCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(ballFKCtrl,fkBallSnapTarget)
        
        self.name.desc='ikToeSnapTarget'
        ikToeSnapTarget = cmds.group(em=True,n=self.name.get(),p=ballFKCtrl) 
        cmds.xform(ikToeSnapTarget,ws=True,m=cmds.xform(toeTipCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(toeTipCtrl,ikToeSnapTarget)

        #add new ctrls to vis switch
        for ctrl in (footCtrl,heelCtrl,toeTipCtrl,ballCtrl):
            shape = cmds.listRelatives(ctrl,s=True)[0]
            mpAttr.connectWithAdd(FKIKblender,shape+'.v',0.4999999)
        for ctrl in [ballFKCtrl]:
            shape = cmds.listRelatives(ctrl,s=True)[0]
            adder = mpAttr.connectWithAdd(FKIKblender,shape+'.v',-0.4999999)
            revNode = mpAttr.connectWithReverse(adder+'.output',shape+'.v',force=True)

        #cleanup
        for item in [ballHandle,toeHandle,handle]:
            mpAttr.visOveride(item,0)


class DogLeg(limbBase.Limb):
    '''Leg with three joints, hip/knee/ankle, a ball and a toetip.
    Differs from normal leg in that ball moves with main IK, meaning only the 
    toe of the foot is planted on the ground.
    Under the hood this works by making a "driver joint" IK chain of three joints
    and tying part of the reverse foot into the driver chain.
    '''

    def __init__(self,*args,**kwargs):
        limbBase.Limb.__init__(self,*args,**kwargs)

    def begin(self):
        limbBase.Limb.begin(self)
        #sanity checks
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError('invalid endJoint: %s' % self.endJoint)  

    def build(self):
        jointList = mpJoint.getJointList(self.startJoint,self.endJoint)
        if len(jointList) < 5:
            raise RuntimeError('LegFKIK requires at least 5 joints in chain: hip/knee/ankle/ball/toetip. Got %s'%len(jointList))

        #Internally the dog leg is driven by a 3 joint ik system made here.
        #This three joint IK has the same total length as hip->ball joint chain.
        length=mpJoint.getChainLength(jointList[0],jointList[-2])
        halfLength=length/2.0

        hip=mpMath.Vector(jointList[0])
        knee=mpMath.Vector(jointList[1])
        ball=mpMath.Vector(jointList[-2])

        legBaseV=ball-hip
        legBaseMidV=legBaseV*0.5
        binormalLength=-1*math.sqrt(0.5*legBaseV.length()**2/halfLength**2)

        #Find the isoceles triange that is coplanar with the leg chain,
        #and whose tall legs sum to the same length as the dogleg.
        #The top vertex of this triangle is where we want the mid joint on our
        #three joint system
        kneeV=knee-hip
        kneeV.normalize()
        ballV=ball-hip
        ballV.normalize()
        chainNormal=kneeV.cross(ballV)
        chainNormal.normalize()
        chainBinorm=chainNormal.cross(kneeV)
        chainBinorm*=binormalLength
        midJointPos=(legBaseMidV+chainBinorm)+hip

        #make driver joints
        cmds.select(cl=True)
        self.name.desc='driverJoint01'
        driverJnt1=cmds.joint(n=self.name.get(),p=hip.get())
        self.name.desc='driverJoint02'
        driverJnt2=cmds.joint(n=self.name.get(),p=midJointPos.get())
        self.name.desc='driverJoint03'
        driverJnt3=cmds.joint(n=self.name.get(),p=ball.get())

        #start with standard blend setup and FKIKChain on hip->ankle
        self.addPinBlend()
        legCtrls = self.addFKIKChain(jointList[0],jointList[-3],self.pinBlend,self.pinWorld)
        ikAim=legCtrls[-2]
        ikEnd=legCtrls[-1]
        effector,handle=mpJoint.getIKNodes(jointList[-3])

        #add FK offsets to ball
        ballFKZero,ballFKCtrl = self.addCtrl('%02d'%len(jointList[:-2]),type='FK',shape='sphere',parent=legCtrls[-3],xform=jointList[-2])
        mpAttr.lockAndHide(ballFKCtrl,'t')
        cmds.orientConstraint(ballFKCtrl,jointList[-2],mo=True)
        mpRig.addPickParent(ballFKCtrl,legCtrls[-3])

        #Make IK Chain on driver joints
        oldpart = self.name.part
        self.name.part+="Driver"
        driverAimCtrl,driverEndCtrl = self.addIKChain(driverJnt1,driverJnt3,self.pinWorld)
        self.name.part=oldpart

        #set ctrl flags false on driver ctrls.
        #This way animators will never touch them and they won't snap/reset/etc.
        driverEndNull=cmds.listRelatives(driverEndCtrl,p=True)[0]
        driverAimNull=cmds.listRelatives(driverAimCtrl,p=True)[0]
        mpCtrl.setAsCtrl(driverEndCtrl,False)
        mpCtrl.setAsCtrl(driverAimCtrl,False)
        #and delete shapes so they aren't visible 
        for ctrl in (driverEndCtrl,driverAimCtrl):
            self.ctrls.remove(ctrl)
            cmds.delete(cmds.listRelatives(ctrl,s=True)[0])

        #make single chain on ankle->ball and ball->tip for ankle roll and toe tap
        self.name.desc = 'ikHandleBall'
        ballHandle,ballEffector = cmds.ikHandle(n=self.name.get(),solver='ikSCsolver',sj=jointList[-3],ee=jointList[-2])
        self.name.desc = 'ikHandleToe'
        toeHandle,toeEffector = cmds.ikHandle(n=self.name.get(),solver='ikSCsolver',sj=jointList[-2],ee=jointList[-1])
        
        self.name.desc = 'ballEffector'
        ballEffector = cmds.rename(ballEffector,self.name.get())
        cmds.parent(ballHandle,self.noXform)
        self.name.desc = 'toeEffector'
        toeEffector = cmds.rename(toeEffector,self.name.get())
        cmds.parent(toeHandle,self.noXform)

        #Make a ankle roll ctrl and toe tap ctrl
        #These transforms are for cosmetic SRT of the foot controls
        footCtrlXform = mpMath.Transform()
        footCtrlXform.scale(2,0.4,4)
        toeCtrlXform = mpMath.Transform()
        toeCtrlXform.setFromEuler(0,90,0)

        footZero,footCtrl = self.addCtrl('Foot',shape='cube',type='IK',parent=self.pinWorld,xform=mpMath.Vector(jointList[-2]),shapeXform=footCtrlXform)
        toeTipZero,toeTipCtrl = self.addCtrl('ToeTip',shape='circle',type='IK',parent=footCtrl,xform=jointList[-1],shapeXform=toeCtrlXform)
        ballZero,ballCtrl = self.addCtrl('Ball',shape='circle',type='IK',parent=toeTipCtrl,xform=jointList[-2],shapeXform=toeCtrlXform)

        #parent constrain single chains under new ctrls
        cmds.parentConstraint(ballCtrl,ballHandle,mo=True)
        cmds.parentConstraint(toeTipCtrl,toeHandle,mo=True)
        cmds.parentConstraint(footCtrl,driverEndNull,mo=True)

        #parent constrain ankle IK to new foot ctrls
        driverEffector,driverHandle=mpJoint.getIKNodes(driverJnt3)
        mpAttr.unlockAndShow(ikEnd,'r')
        ikEndNull=cmds.listRelatives(ikEnd,p=True)[0]
        cmds.parentConstraint(ballCtrl,ikEndNull,mo=True)
        cmds.parentConstraint(toeTipCtrl,driverHandle,mo=True)

        #parent constrain ball ctrl to driver knee joint
        cmds.parentConstraint(driverJnt2,ballZero,mo=True)

        #Blend already exists, but this will grab the right attr
        FKIKblender = self.addAttrLimb(ln=mpName.FKIKBLENDATTR, at='float',min=0,max=1,dv=0,k=True)
        cmds.connectAttr(FKIKblender, ballHandle+'.ikBlend')
        cmds.connectAttr(FKIKblender, toeHandle+'.ikBlend')

        #add new pickwalk/snap info
        mpRig.addPickParent(footCtrl,legCtrls[-2])
        mpRig.addPickParent(ballCtrl,footCtrl)
        mpRig.addPickParent(toeTipCtrl,ballCtrl)

        #Make some nulls to act as snap targets. This is because IK and FK controls might have different axis order or initial positions.
        self.name.desc='ikAnkleSnapTarget'
        ikAnkleSnapTarget = cmds.group(em=True,n=self.name.get(),p=jointList[-2]) 
        cmds.xform(ikAnkleSnapTarget,ws=True,m=cmds.xform(footCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(footCtrl,ikAnkleSnapTarget)

        self.name.desc='ikBallSnapTarget'
        ikBallSnapTarget = cmds.group(em=True,n=self.name.get(),p=ballFKCtrl) 
        cmds.xform(ikBallSnapTarget,ws=True,m=cmds.xform(ballCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(ballCtrl,ikBallSnapTarget)

        self.name.desc='fkBallSnapTarget'
        fkBallSnapTarget = cmds.group(em=True,n=self.name.get(),p=jointList[-2]) 
        cmds.xform(fkBallSnapTarget,ws=True,m=cmds.xform(ballFKCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(ballFKCtrl,fkBallSnapTarget)
        
        self.name.desc='ikToeSnapTarget'
        ikToeSnapTarget = cmds.group(em=True,n=self.name.get(),p=ballFKCtrl) 
        cmds.xform(ikToeSnapTarget,ws=True,m=cmds.xform(toeTipCtrl,ws=True,q=True,m=True))
        mpRig.addSnapParent(toeTipCtrl,ikToeSnapTarget)

        #add new ctrls to vis switch
        for ctrl in (footCtrl,toeTipCtrl,ballCtrl):
            shape = cmds.listRelatives(ctrl,s=True)[0]
            mpAttr.connectWithAdd(FKIKblender,shape+'.v',0.4999999)
        for ctrl in [ballFKCtrl]:
            shape = cmds.listRelatives(ctrl,s=True)[0]
            adder = mpAttr.connectWithAdd(FKIKblender,shape+'.v',-0.4999999)
            revNode = mpAttr.connectWithReverse(adder+'.output',shape+'.v',force=True)

        #cleanup
        for item in [ballHandle,toeHandle,handle]:
            mpAttr.visOveride(item,0)
        mpAttr.visOveride(driverJnt1,0)
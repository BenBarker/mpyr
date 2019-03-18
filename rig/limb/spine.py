'''Spine Limbs'''

import maya.cmds as cmds
import mpyr.lib.joint as mpJoint
import mpyr.lib.attr as mpAttr
import mpyr.lib.rig as mpRig
import mpyr.lib.nurbs as mpNurbs
import limbBase

class SpineFK(limbBase.Limb):
    '''Simple FK chain with "hips" offset on startJoint.
    '''
    def begin(self):
        limbBase.Limb.begin(self)

        #sanity checks
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError('invalid startJoint: %s' % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError('invalid endJoint: %s' % self.endJoint)

    def build(self):
        self.addPinWorld()
        jointList = mpJoint.getJointList(self.startJoint,self.endJoint)
        if len(jointList) < 2:
            raise RuntimeError('SpineFK requires at least 2 joints in chain. Got %s'%len(jointList))
        
        #start with FK chain on all joints
        self.addPinParent()
        spineCtrls = self.addFKChain(jointList[0],jointList[-1],self.pinWorld)

        #rewire first joint to have an extra offset
        mpAttr.breakConnections(jointList[0],'srt')
        zero,fkCtrl = self.addCtrl('hips',type='FK',shape='box',parent=spineCtrls[0],xform=jointList[0])
        cmds.pointConstraint(fkCtrl,jointList[0],mo=True)
        cmds.orientConstraint(fkCtrl,jointList[0],mo=True) #every joint driven by ori cns
        mpAttr.lockAndHide(fkCtrl,'t') 
        mpRig.addPickParent(spineCtrls[0],fkCtrl)
        mpAttr.unlockAndShow(spineCtrls[0],'t')

        #point constrain next control so spine stays locked when hips move
        cmds.pointConstraint(spineCtrls[1],jointList[1],mo=True)


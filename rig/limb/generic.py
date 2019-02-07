'''generic limbs. Offsets, etc.'''

import maya.cmds as cmds
import mpyr.lib.rigmath as mpMath
import limbBase

reload(limbBase)

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
        ctrlXform.scale(5)
        zero, c1 = self.addCtrl('01',type="FK",shape='pyramid',parent=self.limbNode,shapeXform=ctrlXform)
        
        ctrlXform.scale(0.7)
        zero, c2 = self.addCtrl('02',type="FK",shape='pyramid',parent=c1,shapeXform=ctrlXform)
        
        ctrlXform.scale(0.7)
        zero, c3 = self.addCtrl('03',type="FK",shape='pyramid',parent=c2,shapeXform=ctrlXform)
        
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
            raise RuntimeError("invalid startJoint: %s" % self.startJoint)

    def addPin(self):
        self.pin = self.addPinParent()

    def build(self):
        self.addPin()
        
        ctrlXform = mpMath.Transform(self.startJoint)
        zero,c1 = self.addCtrl('01',type="FK",shape='sphere',parent=self.pin,xform=self.startJoint)
        
        if self.useConstraint:
            cmds.orientConstraint(c1,self.startJoint,mo=True)
        else:
            for attr in ['rx','ry','rz']:
                cmds.connectAttr(c1 + "." + attr, self.startJoint + "." + attr,f=True)
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
         
class FKIKChain(limbBase.Limb):
    '''Simple FK and IK chain, with FKIK blend, meant for at least three joints (not single chain IK)
    Requires startJoint and endJoint
    '''
    def begin(self):
        limbBase.Limb.begin(self)

        #sanity checks on start and endJoint
        if not self.startJoint or not cmds.objExists(self.startJoint):
            raise RuntimeError("invalid startJoint: %s" % self.startJoint)
        if not self.endJoint or not cmds.objExists(self.endJoint):
            raise RuntimeError("invalid endJoint: %s" % self.endJoint)

    def build(self):
        self.addPinBlend()
        self.addFKIKChain(self.startJoint,self.endJoint,self.pinBlend,self.pinWorld)


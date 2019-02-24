'''test rig build script'''
import os
import maya.cmds as cmds
import mpyr.rig.rigbase as mpRigBase
import mpyr.rig.limb.generic as generic
reload(generic)
import mpyr.rig.limb.leg as legs
import mpyr.rig.limb.spine as spines

import logging
rigLog = logging.getLogger('rig')
rigLog.setLevel(logging.INFO)

class CharacterRig(mpRigBase.AnimRig):
    def __init__(self):
        mpRigBase.AnimRig.__init__(self)

        self.rigName = "Biped"

        #Skeleton paths can be specified by user, convention, or database.
        #For this example I keep it next to the .py file, so I find based
        #on __file__
        self.skeletonPath=os.path.join(os.path.split(__file__)[0],'bipedSkeleton.ma')
        self.geoPath = ''
        
    def build(self):
        self.importSkeleton()
        self.importGeo()

        #Create Limbs
        spine = generic.NurbsStrip()
        spine.name.part='Spine'
        spine.startJoint='Root'
        spine.endJoint='Spine_04'
        
        legL = legs.LegFKIK()
        legL.name.part = 'Leg'
        legL.name.loc = 'L'
        legL.startJoint = 'Leg_L_01'
        legL.endJoint = 'Foot_L_03'
        legL.heel = 'Foot_L_heel'
        legR = legL.mirror()

        armL = generic.FKIKChain()
        armL.name.part = 'Arm'
        armL.name.loc = 'L'
        armL.startJoint = 'Arm_L_01'
        armL.endJoint = 'Arm_L_03'
        armR = armL.mirror()

        handL = generic.FKTree()
        handL.name.part='Hand'
        handL.name.loc='L'
        handL.startJoint='Hand_L_01'
        handR = handL.mirror()

        self.addLimb(spine)
        self.addLimb(legL)
        self.addLimb(legR)
        self.addLimb(armL)
        self.addLimb(armR)
        self.addLimb(handL)
        self.addLimb(handR)

        #Wire Limbs
        legL > 'Root'
        legR > 'Root'
        armL > 'Clav_L_02'
        armR > 'Clav_R_02'
        handL > 'Arm_L_03'
        handR > 'Arm_R_03'
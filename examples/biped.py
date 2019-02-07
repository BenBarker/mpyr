'''test rig build script'''
import os
import maya.cmds as cmds
import mpyr.rig.rigbase as mpRigBase
import mpyr.rig.limb.generic as limbGen

reload(mpRigBase)
reload(limbGen)

import logging
rigLog = logging.getLogger('rig')
rigLog.setLevel(logging.DEBUG)

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
        pelvis = limbGen.FKOffset()
        pelvis.name.part='Main'
        pelvis.startJoint='Root'

        spine = limbGen.FKChain()
        spine.name.part='Spine'
        spine.startJoint='Spine_01'
        spine.endJoint='Spine_04'
        
        legL = limbGen.FKIKChain()
        legL.name.part = 'Leg'
        legL.name.loc = 'L'
        legL.startJoint = 'Leg_L_01'
        legL.endJoint = 'Foot_L_01'
        legR = legL.mirror()

        armL = limbGen.FKIKChain()
        armL.name.part = 'Arm'
        armL.name.loc = 'L'
        armL.startJoint = 'Arm_L_01'
        armL.endJoint = 'Arm_L_03'
        armR = armL.mirror()


        self.addLimb(pelvis)
        self.addLimb(spine)
        self.addLimb(legL)
        self.addLimb(legR)
        self.addLimb(armL)
        self.addLimb(armR)

        #Wire Limbs
        spine > 'Root'
        legL > 'Root'
        legR > 'Root'
        armL > 'Clav_L_02'
        armR > 'Clav_R_02'
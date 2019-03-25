'''test rig build script'''
import os
import maya.cmds as cmds
import mpyr.rig.rigbase as mpRigBase
import mpyr.rig.limb.generic as generic
import mpyr.rig.limb.leg as legs
import mpyr.rig.limb.spine as spines
import mpyr.lib.deformer as libDef
import mpyr.lib.ctrl as libCtrl

import logging
rigLog = logging.getLogger('rig')
rigLog.setLevel(logging.INFO)

class Rig(mpRigBase.AnimRig):
    def __init__(self):
        mpRigBase.AnimRig.__init__(self)

        #arbitrary name for top node and possibly other nodes.
        self.rigName = "Biped"

        #a cosmetic scale for ctrls and things
        self.rigScale=1.2

        #Skeleton paths can be specified by user, convention, or database.
        #For this example I keep it next to the .py file, so I find based
        #on __file__
        rigPath=os.path.dirname(__file__)
        self.skeletonPath=os.path.join(rigPath,'bipedSkeleton.ma')
        self.geoPath = os.path.join(rigPath,'heroMesh.ma')
        self.ctrlPath = os.path.join(rigPath,'ctrls.json')
        
    def build(self):
        self.importSkeleton()
        self.importGeo()

        #Anim rig can have skinned mesh or parented mesh, it's purely for cosmetics to help
        #the animator. In this case some weights are loaded and some mesh is parented.
        #This weight map was saved using the standard "Save weights maps" tool in Maya.
        libDef.loadSkinWeights('body',os.path.join(os.path.split(__file__)[0],'heroMeshWeights.xml'))
        for obj in ('hair','Eye_L_Mesh','Eye_R_Mesh'):
            cmds.parent(obj,'Head_01')

        #Instance and set up Limbs
        #spine = generic.NurbsStrip()
        #spine.numCtrls=8
        spine = spines.SpineFK()
        spine.name.part='Spine'
        spine.startJoint='Root'
        spine.endJoint='Spine_04'

        head = generic.FKCurlChain()
        head.name.part='Head'
        head.startJoint='Neck_01'
        head.endJoint='Head_01'
        
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

        #"addLimb" is what actually creates the limbs.
        self.addLimb(spine)
        self.addLimb(head)
        self.addLimb(legL)
        self.addLimb(legR)
        self.addLimb(armL)
        self.addLimb(armR)
        self.addLimb(handL)
        self.addLimb(handR)

        #Wire Limbs
        #For limbs with only local space the > operator connects them to a parent
        #For limbs with a blended local/world space the >> operator can change the 
        #world parent.
        #By default any world parents will be connected to the world limb, which
        #is built automatically.
        legL > 'Root'
        legR > 'Root'
        armL > 'Clav_L_02'
        armR > 'Clav_R_02'
        handL > 'Arm_L_03'
        handR > 'Arm_R_03'
        head > 'Spine_04'

        libCtrl.loadCtrlAppearance(self.ctrlPath)
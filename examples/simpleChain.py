'''A few simple limbs on a simple skeleton'''
import os
import maya.cmds as cmds
import rig.rigbase
import rig.limb.generic as limbGen

reload(rig.rigbase)
reload(limbGen)

class CharacterRig(rig.rigbase.AnimRig):
    def __init__(self):
        rig.rigbase.AnimRig.__init__(self)

        self.rigName = "Steve"

        #Skeleton paths can be specified by user, convention, or database.
        #For this example I keep it next to the .py file, so I find based
        #on __file__
        self.skeletonPath=os.path.join(os.path.split(__file__)[0],'simpleChainSkeleton.ma')
        self.geoPath = ''
        
    def build(self):
        self.importSkeleton()
        self.importGeo()

        offset = limbGen.FKOffset()
        offset.name.part = 'Main'
        offset.name.loc = 'L'
        offset.translate = True
        offset.startJoint = 'Root'
        self.addLimb(offset)
        
        offset2 = limbGen.FKOffsetBlend()
        offset2.name.part = 'Offset'
        offset2.name.loc = 'L'
        offset2.translate = True
        offset2.startJoint = 'Joint1'
        self.addLimb(offset2)

        offset2 > 'Root'
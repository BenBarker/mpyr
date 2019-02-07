'''Tools for performing rig actions, mirror limbs, reset etc.'''
import maya.cmds as cmds
import mpyr.lib.rig as mpRig
reload(mpRig)

class RigTools(object):
    def __init__(self):
        object.__init__(self)
        self.showWindow()
    
    def showWindow(self):
        window = cmds.window(title='Rig Tools')
        cmds.columnLayout()
        #Other Widgets\
        cmds.button(label='Reset Selected',width=500,command=self.resetSelected)
        cmds.button(label='Reset Limb',width=500,command=self.resetLimb)
        cmds.button(label='Reset Character',width=500,command=self.resetCharacter)

        cmds.button(label='Mirror Selection',width=500,command=self.mirrorSelection)
        cmds.button(label='Mirror Limb',width=500,command=self.mirrorLimb)

        cmds.button(label='Pickwalk Up',width=500,command=self.pickwalkUp)
        cmds.button(label='Pickwalk Dn',width=500,command=self.pickwalkDown)

        cmds.showWindow(window)

    def resetSelected(self,*args,**kwargs):
        for node in self.getSelection():
            mpRig.resetCtrl(node)

    def resetLimb(self,*args,**kwargs):
        for node in self.getSelection():
            mpRig.resetLimb(node)

    def resetCharacter(self,*args,**kwargs):
        for node in self.getSelection():
            mpRig.resetCharacter(node)

    def mirrorSelection(self,*args,**kwargs):
        for node in self.getSelection():
            mpRig.mirrorCtrl(node)

    def mirrorLimb(self,*args,**kwargs):
        for node in self.getSelection():
            mpRig.mirrorLimb(node)

    def pickwalkUp(self,*args,**kwargs):
        mpRig.pickWalkUp()

    def pickwalkDown(self,*args,**kwargs):
        mpRig.pickWalkDown()

    def getSelection(self):
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please make a selection")
        return sel



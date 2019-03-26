'''Importing this module creates a shelf with the mpyr tools'''
import maya.cmds as cmds
import maya.mel as mel

def createShelf():
    shelfName='MPYR'
    mel.eval('global string $gShelfTopLevel;')
    mainShelfLayout=mel.eval('$tmp=$gShelfTopLevel;')
    if cmds.shelfLayout(shelfName,exists=True):
        mel.eval('deleteShelfTab "%s";' % shelfName)
    #add new tab
    createdShelf=mel.eval('addNewShelfTab "%s";'%shelfName)
    cmds.shelfButton(annotation='Snap/Reset/Key Tools',
        image1='humanIK_CharCtrl.png',
        command='import mpyr.tools.rigTools;reload(mpyr.tools.rigTools);mpyr.tools.rigTools.RigTools()',
        parent=createdShelf 
        )
    cmds.shelfButton(annotation='Joint Orient Tool',
        image='kinInsert.png', 
        command='import mpyr.tools.jointTools;reload(mpyr.tools.jointTools);mpyr.tools.jointTools.JointOrientTool()',
        style='iconAndTextVertical',
        sic=True,
        parent=createdShelf 
        )
    cmds.shelfButton(annotation='Ctrl Appearance Editor',
        image='polyMoveVertex.png',#'HIKCharacter.png', 
        command='import mpyr.tools.ctrlShape;reload(mpyr.tools.ctrlShape);mpyr.tools.ctrlShape.SaveLoadCtrlShape()',
        parent=createdShelf 
        )

createShelf()




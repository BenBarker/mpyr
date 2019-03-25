'''Tools for save/load and edit curve control shapes. 
Saving out a .json ctrl appearance file lets you load it the next time the rig builds.
'''
import os
import sys
import subprocess
import tempfile
import maya.cmds as cmds
import mpyr.lib.rig as mpRig
import mpyr.lib.ctrl as mpCtrl
import mpyr.lib.fileIO as mpFile

class SaveLoadCtrlShape(object):
    '''UI to save/load/mirror/etc ctrl shapes. Wrapper for functions in lib/ctrl.py'''
    def __init__(self):
        object.__init__(self)
        self.widgets=dict()
        self.directory=''
        if cmds.optionVar(exists='Mpyr_SaveLoadCtrlShape_DefaultDir'):
            self.directory = cmds.optionVar(q='Mpyr_SaveLoadCtrlShape_DefaultDir')
        else:
            self.directory=cmds.workspace(q=True,dir=True)
        self.showWindow()
    
    def showWindow(self):
        window = cmds.window(title='Rig Tools',width=500)
        mainLayout=cmds.columnLayout(adj=True)
        #Other Widgets
        self.widgets['filePath']=cmds.textFieldButtonGrp(label='File:',
            adj=2,
            cw=(1,30),
            text=self.directory,
            buttonLabel='...',
            pht='path to ctrl appearance .json',
            cc=self.replaceSlashes,
            bc=self.pickFile,
            p=mainLayout)
        self.widgets['saveAllBut']=cmds.button(label='Save To File',p=mainLayout,command=self.saveFile)
        self.widgets['LoadBut']=cmds.button(label='Load from File',p=mainLayout,command=self.loadFile)
        cmds.separator(p=mainLayout)
        cmds.text(l='Helpers',al='left',fn='boldLabelFont',bgc=[0.2,0.2,0.2],p=mainLayout)
        
        rowLayoutCopyPaste=cmds.rowLayout(numberOfColumns=2,p=mainLayout,
            ad2=1,
            cl2=('center','center'),
            ct2=('both','both')
            )
        cmds.button(label='Copy',p=rowLayoutCopyPaste,command=self.copyShapes)
        cmds.button(label='Paste',p=rowLayoutCopyPaste,width=250,command=self.pasteShapes)
        cmds.button(label='Mirror Selected Ctrl',p=mainLayout,command=self.mirrorCtrl)

        rowLayoutShapePicker=cmds.rowLayout(numberOfColumns=2,p=mainLayout,
            ad2=1,
            cl2=('center','center'),
            ct2=('left','right')
            )
        cmds.button(label='Change selected shape to:',p=rowLayoutShapePicker,command=self.changeShape)
        self.widgets['shapePicker']=cmds.optionMenuGrp(label='',p=rowLayoutShapePicker,cw2=(0,300))
        for ctrlType in mpCtrl.CTRLTYPES:
            cmds.menuItem(label=ctrlType)

        cmds.button(label='Open file in editor',p=mainLayout,command=self.openFile)
        rowLayoutColors=cmds.rowLayout(numberOfColumns=3,p=mainLayout,
            ad3=2,
            cl3=('center','center','center'),
            ct3=('left','both','right')
            )
        cmds.button(label='Blue',p=rowLayoutColors,bgc=(0,1,1),width=166,command=self.leftColor)
        cmds.button(label='Yellow',p=rowLayoutColors,bgc=(1,1,0),width=166,command=self.midColor)
        cmds.button(label='Red',p=rowLayoutColors,bgc=(1,0,0),width=166,command=self.rightColor)

        cmds.showWindow(window)

    def pickFile(self,*args,**kwargs):
        fileFilter = "*.json"
        pickerReturn = cmds.fileDialog2(fileFilter=fileFilter,
            cap='Path to save/load ctrl appearance',
            dialogStyle=2,          #standard across all OSes
            fm=0,                   #ok if file doesn't exist
            dir=self.directory)
        pickerReturn=self.replaceSlashes(pickerReturn)
        #set the path
        cmds.textFieldButtonGrp(self.widgets['filePath'],e=True,text=pickerReturn)

    def leftColor(self,*args,**kwargs):
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select a ctrl")
        for obj in sel:
            mpCtrl.setColor(obj,"light blue")

    def midColor(self,*args,**kwargs):
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select a ctrl")
        for obj in sel:
            mpCtrl.setColor(obj,"yellow")

    def rightColor(self,*args,**kwargs):
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select a ctrl")
        for obj in sel:
            mpCtrl.setColor(obj,"red")

    def changeShape(self,*args,**kwargs):
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select a ctrl")
        shape=cmds.optionMenuGrp(self.widgets['shapePicker'],q=True,v=True)
        for obj in sel:
            mpCtrl.changeCtrlShape(obj,shape)
        cmds.select(sel,r=True)

    def copyShapes(self,*args,**kwargs):
        '''write current shape out to temp file'''
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select a ctrl")
        filePath=self.getTempFileName()

        mpCtrl.saveCtrlAppearance([sel[0]],filePath,search=sel[0],replace='TEMPNAME')
        print 'copied tmp ctrl shape to',filePath

    def pasteShapes(self,*args,**kwargs):
        '''load current shape from temp file'''
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select a ctrl")
        filePath=self.getTempFileName()
        mpCtrl.loadCtrlAppearance(filePath,search='TEMPNAME',replace=sel[0])
        print 'pasted tmp ctrl shape to',filePath
        cmds.select(sel,r=True)

    def mirrorCtrl(self,*args,**kwargs):
        sel=cmds.ls(sl=True) or []
        for obj in sel:
            mpCtrl.mirrorCtrlShape(obj)
        cmds.select(sel,r=True)

    def getTempFileName(self):
        path = tempfile.gettempdir()
        fileName = 'mpyr_ctrlAppearance_copy.json'
        fullPath = os.path.join(path,fileName)
        return fullPath

    def replaceSlashes(self,*args,**kwargs):
        '''Change path to unix style slashes. Maya can handle both so just easier to use Unix'''
        pathValue=cmds.textFieldButtonGrp(self.widgets['filePath'],q=True,text=True)
        pathValue=pathValue.replace('\\','/')
        cmds.textFieldButtonGrp(self.widgets['filePath'],e=True,text=pathValue)
        self.directory=pathValue

    def saveFile(self,*args,**kwargs):
        path=self.directory
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("Please select some ctrls")
        if not path.endswith('.json'):
            raise RuntimeError("Please specify a .json file (doesn't need to exist). EG: 'C:/ctrls.json'")
        if os.path.exists(path) and os.path.isdir(path):
            raise RuntimeError("Please specify a .json file (doesn't need to exist). EG: 'C:/ctrls.json'")
        directory,fileName=os.path.split(path)
        confirm='Yes'
        if os.path.exists(path):
            cmds.confirmDialog( title='File exists',message='overwrite?',button=['Yes','No'],defaultButton='Yes',cancelButton='No',dismissString='No' )
        if confirm=='Yes':
            mpFile.ensurePath(directory,force=True)
            mpCtrl.saveCtrlAppearance(sel,path,force=True)
            cmds.optionVar(sv=('Mpyr_SaveLoadCtrlShape_DefaultDir', self.directory))

    def loadFile(self,*args,**kwargs):
        path=self.directory
        confirm='Yes'
        if os.path.exists(path):
            confirm=cmds.confirmDialog( title='Load file?',message='This may overwrite current ctrls',button=['Yes','No'],defaultButton='Yes',cancelButton='No',dismissString='No')

        if confirm=='Yes':
            sel = cmds.ls(sl=True)
            if not os.path.exists(path) and not os.path.isfile(path):
                raise RuntimeError("Please specify a .json file (doesn't need to exist). EG: 'C:/ctrls.json'")
            mpCtrl.loadCtrlAppearance(path)

    def openFile(self,*args,**kwargs):
        if os.path.exists(self.directory) and os.path.isfile(self.directory) and self.directory.lower().endswith('json'):
            try:
                if sys.platform=='win32':
                    subprocess.call("start "+self.directory, shell=True)
                else:
                    subprocess.call("open "+self.directory, shell=True)
            except OSError, e:
                print "File open failed:", e
        else:
            print 'failed tests'
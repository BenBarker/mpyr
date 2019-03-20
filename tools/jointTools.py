'''Tools for performing rig actions, mirror limbs, reset etc.'''
import maya.cmds as cmds
import mpyr.lib.rigmath as rigmath
import mpyr.lib.rig as mpRig
reload(mpRig)

class JointTools(object):
    def __init__(self):
        object.__init__(self)
        self.widgets=dict()
        self.defaults=dict()
        self.plane=None

        #set defaults
        self.defaults['downAxis']=1
        self.defaults['upAxis']=2
        self.defaults['downNeg']=False
        self.defaults['upNeg']=False
        self.defaults['planeSize']=5


        self.showWindow()

    
    def showWindow(self):
        window = cmds.window(title='Joint Tools')
        
        cmds.scriptJob(uiDeleted=(window,self.deletePlaneButton))
        #Read stored options
        if cmds.optionVar(exists='Mpyr_JointTools_DownAxis'):
            defaultDown = cmds.optionVar(q='Mpyr_JointTools_DownAxis')
        else:
            defaultDown = self.defaults['downAxis']
        if cmds.optionVar(exists='Mpyr_JointTools_DownAxisNeg'):
            defaultDownNeg = cmds.optionVar(q='Mpyr_JointTools_DownAxisNeg')
        else:
            defaultDownNeg = self.defaults['downNeg']       
        if cmds.optionVar(exists='Mpyr_JointTools_UpAxis'):
            defaultUp = cmds.optionVar(q='Mpyr_JointTools_UpAxis')
        else:
            defaultUp = self.defaults['upAxis']      
        if cmds.optionVar(exists='Mpyr_JointTools_UpAxisNeg'):
            defaultUpNeg = cmds.optionVar(q='Mpyr_JointTools_UpAxisNeg')
        else:
            defaultUpNeg = self.defaults['upNeg']   
        if cmds.optionVar(exists='Mpyr_JointTools_PlaneSize'):
            defaultPlaneSize = cmds.optionVar(q='Mpyr_JointTools_PlaneSize')
        else:
            defaultPlaneSize = self.defaults['planeSize']       

        #Create widgets
        mainLayout=cmds.columnLayout(adj=True)
        #Axes widgets
        helpText='Pick which axes will point down and up on the joints'
        cmds.text(l='Axes',al='left',fn='boldLabelFont',bgc=[0.2,0.2,0.2],ann=helpText)
        rowLayout1=cmds.rowLayout("jtrl1",numberOfColumns=2,p=mainLayout,
            ad2=2,
            cl2=('center','center'),
            ct2=('both','both'),
            )
        self.widgets['downAxis']=cmds.radioButtonGrp(numberOfRadioButtons=3,label='Down:  ',
            labelArray3=['X','Y','Z'],
            cw=((1,50),(2,50),(3,50),(4,100)),
            adj=1,
            p=rowLayout1,
            sl=defaultDown)
        self.widgets['downNeg']=cmds.checkBox(label='Neg',p=rowLayout1,v=defaultDownNeg)

        rowLayout2=cmds.rowLayout("jtrl2",numberOfColumns=2,p=mainLayout,
            ad2=2,
            cl2=('center','center'),
            ct2=('both','both'),
            )
        self.widgets['upAxis']=cmds.radioButtonGrp(numberOfRadioButtons=3,label='Up',
            labelArray3=['X','Y','Z'],
            cw=((1,50),(2,50),(3,50),(4,100)),
            adj=1,
            p=rowLayout2,
            sl=defaultUp)
        self.widgets['upNeg']=cmds.checkBox(label='Neg',p=rowLayout2,v=defaultUpNeg)

        #Locator widgets
        cmds.separator(p=mainLayout)
        helpText='Select object to use as up vector for joints'
        cmds.text(l='Up Object:',al='left',fn='boldLabelFont',bgc=[0.2,0.2,0.2],p=mainLayout,ann=helpText)
        cmds.text(l='',al='left',bgc=[0.2,0.2,0.2],p=mainLayout,ann=helpText)
        sel = cmds.ls(sl=True)
        initialText = ''
        if sel:
            initialText = sel[0]
        self.widgets['locatorNameGrp'] = cmds.textFieldButtonGrp( 
            label='', 
            cw=((1,50),(2,200),(3,50)),
            text=initialText, 
            buttonLabel='<<<<',
            bc=self.locatorNameButton,
            p=mainLayout
            )

        #The main button
        cmds.separator(p=mainLayout)
        cmds.button(label='Align',command=self.alignJoints,p=mainLayout,bgc=(0.2,0.8,0.2),h=50)

        #Plane widgets
        cmds.separator(p=mainLayout)
        cmds.text(l='Helpers:',al='left',fn='boldLabelFont',bgc=[0.2,0.2,0.2],p=mainLayout)
        rowLayout3=cmds.rowLayout("jtrl3",numberOfColumns=2,p=mainLayout,
            ad2=1,
            cl2=('center','center'),
            ct2=('both','both')
            )
        cmds.button(label='Make Plane',command=self.makePlaneButton,p=rowLayout3)
        cmds.button(label='Delete Plane',command=self.deletePlaneButton,p=rowLayout3)
        self.widgets['planeSize']=cmds.intSliderGrp(l='size',cw=(1,30),
            min=1,max=200,ss=1.0,
            cc=self.planeSizeSlider,
            field=True,
            v=defaultPlaneSize,
            p=mainLayout)

        #Help and Restore
        cmds.separator(p=mainLayout)
        rowLayout4=cmds.rowLayout("jtrl4",numberOfColumns=2,p=mainLayout,
            ad2=1,
            cl2=('center','center'),
            ct2=('both','both')
            )
        self.widgets['helpButton']=cmds.button(label='Help',command=self.helpPromptButton,p=rowLayout4)
        cmds.button(label='Restore Defaults',command=self.setDefaultsButton,p=rowLayout4)
        cmds.showWindow(window)

    def setDefaultsButton(self,*args,**kwargs):
        '''sets the sliders to defaults'''
        cmds.radioButtonGrp(self.widgets['downAxis'],e=True,sl=self.defaults['downAxis'])
        cmds.radioButtonGrp(self.widgets['upAxis'],e=True,sl=self.defaults['upAxis'])
        cmds.checkBox(self.widgets['downNeg'],e=True,v=self.defaults['downNeg'])
        cmds.checkBox(self.widgets['upNeg'],e=True,v=self.defaults['upNeg'])

    def helpPromptButton(self,*args,**kwargs):
        '''pop up help dialog'''
        def checkboxPrompt():
            form = cmds.setParent(q=True)
            cmds.formLayout(form, e=True, width=300)
            t1 = cmds.text(l='Joint Layout Tool',fn='boldLabelFont',bgc=[0.2,0.2,0.2])
            t2 = cmds.text(align='left',l='1) Axes: pick desired axes for down direction and up direction.')
            t3 = cmds.text(align='left',l='2) Up Object: Position an "up object" (like a locator) where you want, and enter its name into this box.')
            t4 = cmds.text(align='left',l='3) Make Plane: A helper plane for snapping can be made by selecting three objects then hitting "Make Plane".')
            t5 = cmds.text(align='left',l='4) Hit button to align. Aligns all children until it hits a branch.\n')
            spacer=8
            top=5
            edge=5
            cmds.formLayout(form, edit=True,
                attachForm=[(t1, 'top', top), (t1, 'left', edge), (t1, 'right', edge),
                (t2,'left',edge),(t2,'right',edge),
                (t3,'left',edge),(t3,'right',edge),
                (t4,'left',edge),(t4,'right',edge),
                (t5,'left',edge),(t5,'right',edge)],
                attachNone=[(t5, 'bottom')],
                attachControl=[(t2, 'top', spacer, t1),
                (t3, 'top', spacer, t2),
                (t4, 'top', spacer, t3),
                (t5, 'top', spacer, t4)]
            )
        cmds.layoutDialog(ui=checkboxPrompt)

    def locatorNameButton(self,*args,**kwargs):
        '''pops the selection into the text field'''
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("select a object to use as up vector")
        cmds.textFieldButtonGrp(self.widgets['locatorNameGrp'],e=True,text=sel[0])

    def makePlaneButton(self,*args,**kwargs):
        '''make a construction plane based on select'''
        if self.plane and cmds.objExists(self.plane):
            cmds.delete(self.plane)
        sel = cmds.ls(sl=True)
        if not len(sel)>2:
            raise RuntimeError("Please select three objects to make a plane")
        first,middle,last=sel[:3]
        print first,middle,last
        #make dummy alignment object
        dummy=cmds.group(em=True,n='dummyPlaneObj')
        cmds.xform(dummy,ws=True,t=cmds.xform(middle,ws=True,q=True,t=True))
        cmds.delete(cmds.aimConstraint(first,dummy,
            offset=(0,0,0),
            aimVector=(1,0,0),
            upVector=(0,1,0),
            worldUpType='object',
            worldUpObject=last
            )
        )
        pos=cmds.xform(dummy,ws=True,q=True,t=True)
        rot=cmds.xform(dummy,ws=True,q=True,ro=True)
        plane=cmds.plane( p=pos, s=10, r=rot)
        cmds.delete(dummy)
        self.plane=plane
        self.planeSizeSlider()
        cmds.makeLive(self.plane)

    def deletePlaneButton(self,*args,**kwargs):
        if self.plane and cmds.objExists(self.plane):
            cmds.delete(self.plane)
        self.plane=None
        cmds.makeLive(none=True)

    def planeSizeSlider(self,*args,**kwargs):
        if self.plane and cmds.objExists(self.plane):
            planeSize=cmds.intSliderGrp(self.widgets['planeSize'],q=True,v=True)
            cmds.setAttr(self.plane+'.sx',planeSize)
            cmds.setAttr(self.plane+'.sy',planeSize)

    def alignJoints(self,*args,**kwargs):
        downAxis=cmds.radioButtonGrp(self.widgets['downAxis'],q=True,v=True)
        upAxis=cmds.radioButtonGrp(self.widgets['upAxis'],q=True,v=True)
        downNeg=cmds.checkBox(self.widgets['downNeg'],q=True,v=True)
        upNeg=cmds.checkBox(self.widgets['upNeg'],q=True,v=True)
        planeSize=cmds.intSliderGrp(self.widgets['planeSize'],q=True,v=True)

        #store option vars for next time
        cmds.optionVar( iv=('Mpyr_JointTools_DownAxis', downAxis))
        cmds.optionVar( iv=('Mpyr_JointTools_DownAxisNeg', downNeg))
        cmds.optionVar( fv=('Mpyr_JointTools_UpAxis', upAxis))
        cmds.optionVar( iv=('Mpyr_JointTools_UpAxisNeg', upNeg))
        cmds.optionVar( iv=('Mpyr_JointTools_PlaneSize', planeSize))



'''Tools for joint orient workflow'''
import maya.cmds as cmds
import mpyr.lib.joint as mpJoint

class JointOrientTool(object):
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
        self.defaults['upObject']=''

        self.showWindow()

    def showWindow(self):
        '''UI creation method'''
        window = cmds.window(title='Joint Tools',menuBar=True)
        
        #Delete helper plane when window is closed:
        cmds.scriptJob(uiDeleted=(window,self.deletePlaneButton))
        
        #Read stored options, if they don't exist use defaults
        defaultDown = self.defaults['downAxis']
        defaultDownNeg = self.defaults['downNeg']
        defaultUp = self.defaults['upAxis']
        defaultUpNeg = self.defaults['upNeg']
        defaultPlaneSize = self.defaults['planeSize']
        defaultUpObject = self.defaults['upObject']
        if cmds.optionVar(exists='Mpyr_JointTools_DownAxis'):
            defaultDown = cmds.optionVar(q='Mpyr_JointTools_DownAxis')
        if cmds.optionVar(exists='Mpyr_JointTools_DownAxisNeg'):
            defaultDownNeg = cmds.optionVar(q='Mpyr_JointTools_DownAxisNeg')
        if cmds.optionVar(exists='Mpyr_JointTools_UpAxis'):
            defaultUp = cmds.optionVar(q='Mpyr_JointTools_UpAxis')  
        if cmds.optionVar(exists='Mpyr_JointTools_UpAxisNeg'):
            defaultUpNeg = cmds.optionVar(q='Mpyr_JointTools_UpAxisNeg')
        if cmds.optionVar(exists='Mpyr_JointTools_PlaneSize'):
            defaultPlaneSize = cmds.optionVar(q='Mpyr_JointTools_PlaneSize') 
        if cmds.optionVar(exists='Mpyr_JointTools_PlaneSize'):
            storedUpObj = cmds.optionVar(q='Mpyr_JointTools_UpObject')
            if cmds.objExists(storedUpObj):
                defaultUpObject=storedUpObj
               
        #Create widgets
        menu=cmds.menu( label='Help', helpMenu=True,p=window)
        cmds.menuItem(label='Instructions',c=self.helpPromptButton,p=menu)
        cmds.menuItem(label='Restore Defaults',c=self.setDefaultsButton,p=menu)

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
        self.widgets['upAxis']=cmds.radioButtonGrp(numberOfRadioButtons=3,label='Up:    ',
            labelArray3=['X','Y','Z'],
            cw=((1,50),(2,50),(3,50),(4,100)),
            adj=1,
            p=rowLayout2,
            sl=defaultUp)
        self.widgets['upNeg']=cmds.checkBox(label='Neg',p=rowLayout2,v=defaultUpNeg)

        #Locator widgets
        cmds.separator(p=mainLayout)
        helpText='Select object to use as up vector for joints'
        cmds.text(l='Up Object',al='left',fn='boldLabelFont',bgc=[0.2,0.2,0.2],p=mainLayout,ann=helpText)
        self.widgets['locatorNameGrp']=cmds.textFieldButtonGrp( 
            label='', 
            cw=((1,10),(2,250),(3,50)),
            text=defaultUpObject, 
            buttonLabel='<<<<',
            bc=self.locatorNameButton,
            p=mainLayout)

        #The main button
        cmds.separator(p=mainLayout)
        cmds.button(label='Orient Joint Chain',command=self.alignJoints,p=mainLayout,bgc=(0.7,1.0,0.7),h=50)

        #Plane widgets
        cmds.separator(p=mainLayout)
        cmds.text(l='Helpers',al='left',fn='boldLabelFont',bgc=[0.2,0.2,0.2],p=mainLayout)
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
        cmds.separator(p=mainLayout)
        cmds.button(label='Tweak Joint',command=self.tweakButton,p=mainLayout)
        cmds.showWindow(window)

    def setDefaultsButton(self,*args,**kwargs):
        '''sets the UI sliders to defaults'''
        cmds.radioButtonGrp(self.widgets['downAxis'],e=True,sl=self.defaults['downAxis'])
        cmds.radioButtonGrp(self.widgets['upAxis'],e=True,sl=self.defaults['upAxis'])
        cmds.checkBox(self.widgets['downNeg'],e=True,v=self.defaults['downNeg'])
        cmds.checkBox(self.widgets['upNeg'],e=True,v=self.defaults['upNeg'])

    def helpPromptButton(self,*args,**kwargs):
        '''Help dialog'''
        def helpFormUI():
            form = cmds.setParent(q=True)
            cmds.formLayout(form, e=True, width=300)
            t1=cmds.text(l='Joint Orient Tool',fn='boldLabelFont',bgc=[0.2,0.2,0.2])
            t2=cmds.text(l='This tool allows you to orient joints using a helper object to set the up vector, \nand optionally a contruction plane to snap your helper to. The workflow is:')
            t3=cmds.text(align='left',l='1) Axes: pick desired axes for down direction and up direction.\n   "Down" is the joint axis that will point at its child.\n   "Up" is the joint axis that will point at the "up object".')
            t4=cmds.text(align='left',l='2) Up Object: Create and position an "up object" (like a locator) where you want,\n    and enter its name into this box. Use "<<<<" to grab current selection.')
            t5=cmds.text(align='left',l='3) Select root of chain you wish to align and hit the "Orient Joint Chain" button.\n    This aligns the selected joint and all child joints until it hits a joint with more than 1 child.\n    I work by unparenting my joint chains as needed, orienting them, then reparenting.')
            t6=cmds.text(align='left',l='Helpers',bgc=[0.2,0.2,0.2])
            t7=cmds.text(align='left',l='Make Plane: Lets you select any three objects then push "Make Plane" to create a live helper grid.\n    For example grabbing the three joints of an arm and running this will make a grid on the "plane" of that arm.\n    You can then snap joints or your up object to this grid if needed.\n    "Size" adjusts the grid size. Delete button makes plane not "live" and deletes.')
            t8=cmds.text(align='left',l='Tweak Joint: Makes a locator at the selected joint that you can rotate to directly manipulate joint orient.\n    When you are done simply delete locator.')
            spacer=8
            top=5
            edge=5
            cmds.formLayout(form, edit=True,
                attachForm=[(t1, 'top', top), (t1, 'left', edge), (t1, 'right', edge),
                (t2,'left',edge),(t2,'right',edge),
                (t3,'left',edge),(t3,'right',edge),
                (t4,'left',edge),(t4,'right',edge),
                (t5,'left',edge),(t5,'right',edge),
                (t6,'left',edge),(t6,'right',edge),
                (t7,'left',edge),(t7,'right',edge),
                (t8,'left',edge),(t8,'right',edge)],
                attachNone=[(t8, 'bottom')],
                attachControl=[(t2, 'top', spacer, t1),
                (t3, 'top', spacer, t2),
                (t4, 'top', spacer, t3),
                (t5, 'top', spacer, t4),
                (t6, 'top', spacer, t5),
                (t7, 'top', spacer, t6),
                (t8, 'top', spacer, t7)],
            )
        cmds.layoutDialog(ui=helpFormUI)

    def locatorNameButton(self,*args,**kwargs):
        '''Pops the selection into the text field'''
        sel = cmds.ls(sl=True)
        if not sel:
            raise RuntimeError("select a object to use as up vector")
        cmds.textFieldButtonGrp(self.widgets['locatorNameGrp'],e=True,text=sel[0])

    def makePlaneButton(self,*args,**kwargs):
        '''Make a construction plane based on selected objects'''
        if self.plane and cmds.objExists(self.plane):
            cmds.delete(self.plane)
        sel = cmds.ls(sl=True)
        if not len(sel)>2:
            raise RuntimeError("Please select three objects to make a plane")
        first,middle,last=sel[:3]
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
        '''Deletes the helper plane. Also called on window close.'''
        if self.plane and cmds.objExists(self.plane):
            cmds.delete(self.plane)
        self.plane=None
        cmds.makeLive(none=True)

    def planeSizeSlider(self,*args,**kwargs):
        '''Resizes the helper plane'''
        if self.plane and cmds.objExists(self.plane):
            planeSize=cmds.intSliderGrp(self.widgets['planeSize'],q=True,v=True)
            cmds.setAttr(self.plane+'.sx',planeSize)
            cmds.setAttr(self.plane+'.sy',planeSize)

    def tweakButton(self,*args,**kwargs):
        '''Make a helper gizmo to rotate orient'''
        sel=cmds.ls(sl=True)
        if not sel or not cmds.nodeType(sel[0])=='joint':
            raise RuntimeError("Select a joint to tweak")
        joint=sel[0]
        
        #make a locator that matches joint orient/parent
        locator=cmds.spaceLocator(n='JointTweak')[0]
        cmds.xform(locator,t=cmds.xform(joint,ws=True,q=True,t=True))
        jointPar=cmds.listRelatives(joint,p=True)
        if jointPar:
            cmds.parent(locator,jointPar)
        cmds.setAttr(locator+'.localScale',3,3,3)
        jointOri=cmds.getAttr(joint+'.jointOrient')[0]
        cmds.setAttr(locator+'.r',*jointOri)

        #connect tweak to joint ori
        cmds.connectAttr(locator+'.r',joint+'.jointOrient')

    def alignJoints(self,*args,**kwargs):
        '''Main function, called by Orient Joint Chain button, aligns the joints.'''
        downAxis=cmds.radioButtonGrp(self.widgets['downAxis'],q=True,sl=True)
        upAxis=cmds.radioButtonGrp(self.widgets['upAxis'],q=True,sl=True)
        downNeg=cmds.checkBox(self.widgets['downNeg'],q=True,v=True)
        upNeg=cmds.checkBox(self.widgets['upNeg'],q=True,v=True)
        planeSize=cmds.intSliderGrp(self.widgets['planeSize'],q=True,v=True)
        upObject=cmds.textFieldButtonGrp(self.widgets['locatorNameGrp'],q=True,text=True)

        #store option vars for next time
        cmds.optionVar( iv=('Mpyr_JointTools_DownAxis', downAxis))
        cmds.optionVar( iv=('Mpyr_JointTools_DownAxisNeg', downNeg))
        cmds.optionVar( iv=('Mpyr_JointTools_UpAxis', upAxis))
        cmds.optionVar( iv=('Mpyr_JointTools_UpAxisNeg', upNeg))
        cmds.optionVar( fv=('Mpyr_JointTools_PlaneSize', planeSize))
        cmds.optionVar( sv=('Mpyr_JointTools_UpObject', upObject))

        #Sanity checking inputs
        if downAxis==upAxis:
            raise RuntimeError("Please select different axes for down and up")
        if not cmds.objExists(upObject):
            raise RuntimeError("Up Object not found in scene")

        #sometimes axis widget returns 0,1,or 2, sometimes str. So always convert to string
        axisNames='xyz'
        if isinstance(downAxis,int):
            downAxis=axisNames[downAxis-1]
        if isinstance(upAxis,int):
            upAxis=axisNames[upAxis-1]
        if downNeg:
            downAxis='-'+downAxis
        if upNeg:
            upAxis='-'+upAxis

        #Gather joints in the chain
        sel=cmds.ls(sl=True)
        if not sel or not cmds.nodeType(sel[0])=='joint':
            raise RuntimeError("Please select a joint to orient")
        #create list to hold joints
        jointList=[sel[0]]
        #go through chain, stopping when there are no children or a branch
        while True:
            children = cmds.listRelatives(jointList[-1],children=True,type='joint') or []
            if len(children) != 1:
                break
            jointList.append(children[0])

        if len(jointList)==1:
            raise RuntimeError("Only one joint in chain. Cannot orient a joint with no children, skipping.")

        for joint in jointList:
            #Before we do anything make sure joint rotate order is xyz. 
            #jointOrient is always xyz, so to combine them we need rotation order to be in the same order.
            rotOrder=cmds.xform(joint,q=True,roo=True)
            cmds.xform(joint,p=True,roo='xyz')

            #orient
            mpJoint.orientJoint(joint,upVector=upObject,downAxis=downAxis,upAxis=upAxis)
            
            #restore rotation order
            cmds.xform(joint,p=True,roo=rotOrder)

        print("Joint orient complete")



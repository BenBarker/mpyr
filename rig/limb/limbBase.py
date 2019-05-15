'''Base classes for limbs

Limbs are units or blocks of a rig that can be chained together to create
a full character. They hold the code where the ctrls, constraints, ik solvers, etc. are
actually created and attached that make the rig. One, twenty, or hundreds of limbs
could work together in a rig to move the skeleton in an animator friendly way.

The base Limb class implements the most generic limb. It hooks onto at least one incoming
transform via it's 'pinParent' or 'pinWorld', and it drives one more more joints given via
it's startJoint (and perhaps endJoint) attribute(s).

It also maintains name info, can make controls, and constrain things together.
It does book keeping with object sets after building so tools can be easily written to snap,
reset, or otherwise manipulate the ctrls it makes.

Like Rigs (see rigbase.py), Limbs have a begin, build, and end phase for setup, creation,
and cleanup. Setup and cleanup are implemented on the base class in this module, with
creation handled by child classes.

The child subclasses are kept in their own modules, such as generic.py. There could
easily be leg.py, arm.py, head.py, or anything that is logical for organization.
They should all inherit from Limb or some intermediate class.
'''
import logging
import inspect
import copy
import maya.cmds as cmds

import mpyr.lib.attr as mpAttr
import mpyr.lib.name as mpName
import mpyr.lib.ctrl as mpCtrl
import mpyr.lib.cns as  mpCns
import mpyr.lib.rigmath as mpMath
import mpyr.lib.joint as mpJoint
import mpyr.lib.rig as mpRig
import mpyr.lib.cache as mpCache

RIGLOG = logging.getLogger('rig.limb')

class Limb(object):
    '''This is a virtual base class for all other limbs.
    All implemented limbs should inherit from this class or it's children.
    Limbs are used inside a build script, by instancing them and then passing them
    to the rig's addLimb() method.

    Attributes:
    Most of these will be 'None' when limb is initialized and only populated after a limb
    is built unless otherwise noted.
    - name: the limb's name object. TDs usually set the 'part' and 'loc' in the build
            script, but they are initialized to 'Limb' and 'M'.
    - startJoint: the first (possibly only) joint driven by the limb. Set by the
                  TD in the rig build script.
    - endJoint: the last joint driven by a limb, which when taken with startJoint
                may form a chain. May be optional. Set in build script.
    - startCtrl: The first ctrl of the limb. If not set explicitly will be set to ctrl
                 driving the startJoint, failing that the first ctrl made. Used when
                 setting up pickwalk between limbs.
    - endCtrl: The last ctrl of the limb. If not set explicitly will be set to ctrl
               driving the endJoint, failing that the last ctrl made. Used when
               setting up pickwalk between limbs.
    - rig: the rig object this limb is being built under. This is set when the limb is
           built via calling 'addLimb' by a rig object during a build script.
    - limbNode: the top level transform node of the limb. Set when the limb begins
                building, and used frequently internally to parent things under the limb.
    - noXform: a group made under the limbNode that has 'inheritsTransform' off. Set
               when the limb begins, it gives a usefull place to keep nodes that
               shouldn't move or be touched by animators.
    - ctrls: a list of all ctrls made during limb build. Ctrls are added by the addCtrl
             method.
    - pinParent: a transform that is constrained to other objects to drive
                 the limb's local space. Almost all limbs have a pinParent.
                 It is created when the limb calls addPinParent, and gets
                 constrained to the limb's parent by the TD when they 'wire'
                 the limb with the '>' operator.
    - pinWorld: similar to pinParent, but takes a 'world' transform that the limb
                can use to do blending or worldspace behavior. Not all limbs have
                a pinWorld. TD's can wire a limb's pinWorld with the '>>' operator,
                but any unwired pinWorlds get automatically wired to the worldOffset
                when rig building finishes.
    '''
    def __init__(self):
        object.__init__(self)
        self.name = mpName.Name()
        self.name.part = 'Limb'
        self.name.loc = 'M'

        self.startJoint = None
        self.endJoint = None

        self.startCtrl = None
        self.endCtrl = None

        self.rig = None
        self.limbNode = None
        self.noXform = None
        self.ctrls = []
        
        self.pinParent = None
        self.pinWorld = None
        self.pinBlend=None

    def __repr__(self):
        return '%s %s_%s' % (self.__class__.__name__, self.name.part, self.name.loc)
        
    def __gt__(self,other):
        '''Override greater than (>) to do pinParent constraining'''
        RIGLOG.info('wiring %s',self)
        #Check pinParent
        if not self.pinParent or not cmds.objExists(self.pinParent):
            raise RuntimeError('Cannot wire, .pinParent not found on limb %s'%self)
        
        #If 'other' is a limb, find endJoint or fallback to startJoint:
        drivingNode=other
        if isinstance(other,Limb):
            if hasattr(other,'endJoint'):
                drivingNode=other.endJoint
            elif hasattr(other, 'startJoint'):
                drivingNode=other.startJoint
            RIGLOG.debug('wiring found driver %s',drivingNode,)
        #if that didn't work, see if 'other' is just a node:
        if cmds.objExists(drivingNode):
            RIGLOG.debug('wiring limb to %s',drivingNode,)
            cmds.parentConstraint(drivingNode,self.pinParent,mo=True)

        #Try and setup pickwalk across limbs
        #If other is a limb use its 'endCtrl'
        if isinstance(other,Limb):
            if self.startCtrl and other.endCtrl:
                RIGLOG.debug('wiring pickParent from %s to %s',self.startCtrl,other.endCtrl)
                mpRig.addPickParent(self.startCtrl,other.endCtrl)
        #Otherwise grab whatever is driving 'other' and see if it's a ctrl
        elif cmds.objExists(other):
            endCtrl=mpRig.getCtrlFromJoint(other)
            print 'endCtrl:',endCtrl
            if mpCtrl.isCtrl(endCtrl):
                RIGLOG.debug('wiring pickParent from %s to %s',self.startCtrl,endCtrl)
                mpRig.addPickParent(self.startCtrl,endCtrl)
            else:
                RIGLOG.debug('wiring could not find pickParent on %s, skipping',other)
        else:
            RIGLOG.debug('wiring found no pickParent to connect from %s to %s',self,other)

            
    def __rshift__(self,other):
        '''Override rshift (>>) to do pinWorld constraining'''
        RIGLOG.info('wiring %s pinWorld to %s',self,other)
        if cmds.objExists(self.pinWorld):
            cmds.parentConstraint(other,self.pinWorld,mo=True)
        else:
            raise RuntimeError('Cannot constrain, .pinWorld not found on limb obj')
            
    def addPinParent(self):
        '''Creates a transform to act as an 'incoming parent' hook for the limb.
        Sets the .pinParent attr on the limb to this object, and returns it.
        '''
        RIGLOG.debug('adding pin parent')
        self.name.desc = mpName.PINPARENT
        self.pinParent = cmds.group(em=True,n=self.name.get(),p=self.limbNode)
        #try to move the pinParent to start joint, for a sensible pivot
        if self.startJoint:
            cmds.xform(self.pinParent,ws=True,m=cmds.xform(self.startJoint,ws=True,q=True,m=True))
        return self.pinParent
        
    def addPinWorld(self):
        '''Creates a transform to act as an 'incoming world' hook for the limb.
        Sets the .pinWorld attr on the limb to this object, and returns it.
        '''
        RIGLOG.debug('adding pin world')
        self.name.desc = mpName.PINWORLD
        self.pinWorld = cmds.group(em=True,n=self.name.get(),p=self.limbNode)
        if self.startJoint:
            cmds.xform(self.pinWorld,ws=True,m=cmds.xform(self.startJoint,ws=True,q=True,m=True))
        return self.pinWorld

    def addPinBlend(self):
        '''Creates a world pin and a parent pin, then makes a blendPin that blends
        between them. Sets a .pinBlend attr on the limb and also returns it.
        '''
        RIGLOG.debug('added pin blend setup')
        blender = self.addAttrLimb(ln=mpName.LIMBBLENDATTR, at='float',min=0,max=1,dv=0,k=True)
        self.addPinParent()
        self.addPinWorld()
        self.name.desc = mpName.PINBLEND
        self.pinBlend = cmds.group(em=True,n=self.name.get(),p=self.limbNode)
        cmds.parentConstraint(self.pinParent,self.pinBlend,skipRotate=('x','y','z'))
        mpCns.blendConstraint(
            self.pinParent,
            self.pinWorld,
            self.pinBlend,
            blender,
            cnsType='orient',
            mo=True
        )
        cmds.parent(self.pinParent,self.pinWorld)
        return self.pinBlend
        
    def create(self):
        '''This method builds the limb by calling the creation methods in the correct 
        order.
        '''
        RIGLOG.info('begin limb %s',self)
        self.begin()
        RIGLOG.debug('limb build')
        self.build()
        RIGLOG.debug('ending limb build')
        self.end()
        RIGLOG.info('limb build complete')
        
    def begin(self):
        '''Limb build setup. Make a top level node, some nodes that are on all limbs'''
        self.getLimbNode()
        
        #create a noXform node
        self.name.desc='NoXform'
        self.noXform = cmds.createNode('transform', n=self.name.get(), p=self.limbNode)
        cmds.setAttr(self.noXform+'.inheritsTransform', 0)
        
    def end(self):
        '''Runs at end of limb creation'''
        self.instanceLimbNodeShape()
        mpAttr.visOveride(self.noXform,0)
        self.setStartEndCtrls()
        
    def build(self):
        raise NotImplementedError('You must implement a "build" method in your Limb class')
        
    def addCtrl(self,name,type='FK',shape='sphere',size=1.0,segments=13,parent=None,color=None,shapeXform=None,xform=None):
        '''Adds a ctrl to this limb.
        A wrapper for lib.addCtrl, but hooks ctrl vis up to limb, and adds name suffix.

        name should be simple, like '01', or 'Upper'. The limb takes care of the rest.
        
        The name convention used here is specified in mpName, which is also used 
        to sort controls after building into sets by rigBase.Rig.addLimbSets().
        '''
        RIGLOG.debug('Adding %s control %s',type,name)
        if type == 'FK':
            self.name.desc = name + mpName.FKCTRL
        elif type == 'IK':
            self.name.desc = name + mpName.IKCTRL
        else:
            self.name.desc = name + mpName.CTRL
            
        #scale size by rigScale, if it exists
        if self.rig:
            size *= self.rig.rigScale
            
        #Make the ctrl
        if not parent:
            parent = self.limbNode
        zero,control = mpCtrl.addCtrl(self.name.get(),
            shape=shape,
            size=size,
            segments=segments,
            parent=parent,
            color=color,
            shapeXform=shapeXform,
            xform=xform)
            
        #add this ctrl to the limb's ctrls list
        self.ctrls.append(control)

        #If vis switch exists, connect here
        if cmds.objExists(self.limbNode+'.controls'):
            cmds.connectAttr(self.limbNode+'.controls', zero +'.v')

        return(zero,control)

    def deleteCtrl(self,ctrl):
        '''removed a ctrl nodes and info from limb'''
        RIGLOG.debug('deleting control %s',ctrl)
        zeroNode = cmds.listRelatives(ctrl,p=1)[0]
        cmds.delete(ctrl)
        cmds.delete(zeroNode)
        self.ctrls.remove(ctrl)
        
    def getLimbNode(self):
        '''make or return the top level node for the limb'''
        #if already exists exit
        if self.limbNode:
            return
        #else, create:
        self.name.desc = mpName.LIMBNAME
        self.limbNode = cmds.createNode('transform',n=self.name.get())

        #add empty shape node to store any attributes created by addAttrLimb
        cmds.createNode('mesh',p=self.limbNode,n=self.limbNode+mpName.LIMBSHAPE)
        
        if self.rig:
            cmds.parent(self.limbNode,self.rig.limbNode)
            
        # create visibility attrs
        mpAttr.addAttrSwitch(self.limbNode+'.controls', value=1)

    def addAttrLimb(self,*args,**kwargs):
        '''Adds an attribute to an empty shape node parented to the top transform of 
        the limb (the 'limbNode'). This shape node is instanced under all the limb's ctrls
        after building, so these attributes will be available in the channel box no matter
        what ctrl is selected. If attribute already exists it is simply returned.
        All args just passed to addAttr, except the node name (which is automatic)
        '''
        limbNodeShape = self.getLimbNodeShape()
        #I'd like to return the attr name instead of addAttr's default None,
        #so pull it out of the kwargs and return
        attrName = kwargs.get('ln',kwargs.get('longName',None))
        RIGLOG.debug('adding limb attribute %s',attrName)
        fullName = limbNodeShape+'.'+attrName
        if cmds.objExists(fullName):
            return fullName
        cmds.addAttr(limbNodeShape,*args,**kwargs)
        return fullName

    def getLimbNodeShape(self):
        '''Returns the empty shape node under the limbNode.'''
        return cmds.listRelatives(self.limbNode,s=True)[0]

    def instanceLimbNodeShape(self):
        '''Instance the shape under the limbNode under all limb ctrls.
        This gives animators easy access to limb node attrs no matter what ctrl they select.
        '''
        limbShape = self.getLimbNodeShape()
        RIGLOG.debug('instancing limbNode shape %s under ctrls',limbShape)
        for ctrl in self.ctrls:
            if not mpCtrl.isCtrl(ctrl):
                continue
            inst = cmds.instance(limbShape)
            instShape = cmds.listRelatives(inst,s=True)[0]
            cmds.parent('%s|%s'%(inst[0],instShape),ctrl,s=True,r=True)
            cmds.delete(inst)

    def addFKChain(self,startJoint,endJoint,parent):
        '''Create chain of FK ctrls on given joints, returns list of created ctrls
        - parent = parent of the first ctrl
        '''
        RIGLOG.debug('adding FKChain')
        jointList = mpJoint.getJointList(startJoint,endJoint)
        ctrlParent = parent
        fkCtrls = []
        prevCtrl = None
        for idx,joint in enumerate(jointList):
            zero,fkCtrl = self.addCtrl('%02d'%idx,type='FK',shape='sphere',parent=ctrlParent,xform=joint)
            #first ctrl should do translation of joint, so chain moves with ctrls
            if idx == 0:
                cmds.pointConstraint(fkCtrl,joint,mo=True)
            cmds.orientConstraint(fkCtrl,joint,mo=True) #every joint driven by ori cns
            ctrlParent = fkCtrl
            mpAttr.lockAndHide(fkCtrl,'t') #translate not needed on fk chain
            fkCtrls.append(fkCtrl)
            if prevCtrl:
                mpRig.addPickParent(fkCtrl,prevCtrl) #for pickwalk later
            prevCtrl = fkCtrl
            mpRig.addSnapParent(fkCtrl,joint) #for snapping FK to IK
        return fkCtrls

    def addIKChain(self,startJoint,endJoint,worldParent):
        '''Create an IK RP solver on a chain with end and aim ctrls. Requires three or more joints in chain.
        Also creates a "stub" joint with an SC solver at the end of the chain, so that the last joint's
        rotation is blended between the IK end ctrl and the last FK ctrl properly.
        - worldParent = Drives IK translate and rotate.
        Returns list of [IKAim,IKEnd] ctrls
        '''
        jointList = mpJoint.getJointList(startJoint,endJoint)
        if len(jointList)<3:
            raise RuntimeError('FKIKChain needs at least three joints')
        #Create IK Chain
        RIGLOG.debug('Adding IK Chain')
        self.name.desc = 'iKHandle'
        handle,effector = cmds.ikHandle(n=self.name.get(),solver='ikRPsolver',sj=startJoint,ee=endJoint)
        self.name.desc = 'effector'
        effector = cmds.rename(effector,self.name.get())
        cmds.parent(handle,self.noXform)

        #-find the location of the aim
        midJointIdx = int(len(jointList)/2)
        midJoint = jointList[midJointIdx]
        midV = mpMath.Vector(midJoint)
        endV = mpMath.Vector(endJoint)
        aimV = mpRig.getAimVector(startJoint,midJoint,endJoint)

        aimZero,aimCtrl = self.addCtrl('aim',type='IK',shape='cross',parent=worldParent,xform=aimV)
        endZero,endCtrl = self.addCtrl('end',type='IK',shape='cube',parent=worldParent,xform=endV)

        #make an 'end null' to have a buffer between the last ctrl and the handle
        self.name.desc = 'IKEnd'
        endNull = cmds.group(em=True,n=self.name.get(),p=self.noXform)
        cmds.xform(endNull,ws=True,m=cmds.xform(endCtrl,ws=True,q=True,m=True))

        #constrain everything
        cmds.parentConstraint(endCtrl,endNull,mo=True)
        cmds.parentConstraint(endNull, handle,mo=True)
        cmds.poleVectorConstraint(aimCtrl,handle)

        #make the aim float between end and root of ik system
        cmds.pointConstraint(endCtrl,worldParent,aimZero,mo=True)

        #IK ctrl pickwalks
        mpRig.addPickParent(aimCtrl,endCtrl)
        mpRig.addPickParent(endCtrl,aimCtrl)

        return(aimCtrl,endCtrl)

    def addFKIKChain(self,startJoint,endJoint,localParent,worldParent):
        '''Create a chain of FK ctrls with a blended IKRP solver. Requires three or more joints in chain.
        Also creates a "stub" joint with an SC solver at the end of the chain, so that the last joint's
        rotation is blended between the IK end ctrl and the last FK ctrl properly.
        - localParent = drives translation of FK chain always, rotation when local space is on. IK ignores.
        - worldParent = drives rotation when 'world' space is blended on. Drives IK translate and rotate.
        Returns list of [FkCtrl1,FKCtrl2,...,IKAim,IKEnd]
        '''
        jointList = mpJoint.getJointList(startJoint,endJoint)
        if len(jointList)<3:
            raise RuntimeError('FKIKChain needs at least three joints')
        fkCtrls = self.addFKChain(startJoint,endJoint,localParent)
        aimCtrl,endCtrl = self.addIKChain(startJoint,endJoint,worldParent)

        #lock mid ctrls axes so the FK system can only rotate on one plane.
        #This is needed so the IK system, which is always on a plane, can snap to the FK system
        #First find which axis will be locked by checking its local axes against the 
        #normal vector of the chain. The highest dot product is the most parallel.
        #Note: I may need to lock joint DoF as well, sometimes Maya injects tiny rotation values there
        #when in IK mode.
        midJointIdx = int(len(jointList)/2)
        midJoint = jointList[midJointIdx]
        startV = mpMath.Vector(startJoint)
        midV = mpMath.Vector(midJoint)
        endV = mpMath.Vector(endJoint)
        chainMid = midV-startV
        chainEnd = endV-startV
        chainMid.normalize()
        chainEnd.normalize()
        chainNormal=chainMid.cross(chainEnd)
        chainNormal.normalize()
        axes=['x','y','z']
        for ctrl in fkCtrls[1:-1]:
            ctrlXform = mpMath.Transform(ctrl)
            dots = list()
            dots.append(abs(ctrlXform.xAxis().dot(chainNormal)))
            dots.append(abs(ctrlXform.yAxis().dot(chainNormal)))
            dots.append(abs(ctrlXform.zAxis().dot(chainNormal)))
            del axes[dots.index(max(dots))]
            for axis in axes:
                mpAttr.lockAndHide(ctrl,['r%s'%axis])
            
        #constrain fk ctrls to local/world
        firstFKZero = cmds.listRelatives(fkCtrls[0],p=True)[0]
        cmds.parentConstraint(localParent,firstFKZero,mo=True)

        #make a stub joint and an SCIKsolver
        #This is using Maya's built in 'ikBlend' blends rotate on the last joint
        self.name.desc='ikStub'
        cmds.select(cl=True)
        stubJoint = cmds.joint(n=self.name.get())
        cmds.parent(stubJoint,endJoint)
        stubPos = endV+((endV-midV)*0.5)
        cmds.xform(stubJoint,t=stubPos.get(),ws=True)
        self.name.desc = 'iKStubHandle'
        stubHandle,stubEffector = cmds.ikHandle(n=self.name.get(),solver='ikSCsolver',sj=endJoint,ee=stubJoint)
        self.name.desc = 'stubEffector'
        stubEffector = cmds.rename(stubEffector,self.name.get())
        cmds.parent(stubHandle,self.noXform)
        cmds.parentConstraint(endCtrl,stubHandle,mo=True)
        mpCache.flag(stubJoint,False) #don't want stub joints saved in jointSRTs

        #Construct the blend
        FKIKblender = self.addAttrLimb(ln=mpName.FKIKBLENDATTR, at='float',min=0,max=1,dv=0,k=True)
        effector,handle=mpJoint.getIKNodes(endJoint)
        cmds.connectAttr(FKIKblender, handle+'.ikBlend')
        cmds.connectAttr(FKIKblender, stubHandle+'.ikBlend')

        #switch ctrl vis
        for ctrl in (aimCtrl,endCtrl):
            shape = cmds.listRelatives(ctrl,s=True)[0]
            mpAttr.connectWithAdd(FKIKblender,shape+'.v',0.4999999)
        for ctrl in fkCtrls:
            shape = cmds.listRelatives(ctrl,s=True)[0]
            adder = mpAttr.connectWithAdd(FKIKblender,shape+'.v',-0.4999999)
            mpAttr.connectWithReverse(adder+'.output',shape+'.v',force=True)
        
        #setup IK->FK snapping messages
        #Since the IK end ctrl and the last FK ctrl can have totally different oris,
        #make a null matching the IK's ori under the FK ctrl to act as a snap target
        self.name.desc='ikEndSnap'
        endSnapNull=cmds.group(em=True,n=self.name.get(),p=fkCtrls[-1])
        cmds.xform(endSnapNull,ws=True,m=cmds.xform(endCtrl,q=True,ws=True,m=True))
        mpRig.addSnapParent(endCtrl, endSnapNull) 
        mpRig.addSnapParent(aimCtrl, fkCtrls[0])
        mpRig.addSnapParent(aimCtrl, fkCtrls[1])
        mpRig.addSnapParent(aimCtrl, fkCtrls[2])

        #cleanup
        for hideObject in (handle,stubHandle,stubJoint):
            cmds.setAttr(hideObject+'.v',0)
            mpAttr.lockAndHide(hideObject,'v')

        fkCtrls.extend([aimCtrl,endCtrl])
        return fkCtrls

    def mirror(self):
        '''Return a copy of this limb with attributes mirrored.
        Attempts to mirror string attributes using the naming convention, mirrors Name objects,
        and tries to mirror iterables containing strings.
        Limbs with funky attributes should implement their own mirror if needed.
        '''
        RIGLOG.debug('mirroring limb')
        leftToken = mpName.SEP + mpName.LEFT + mpName.SEP
        rightToken = mpName.SEP + mpName.RIGHT + mpName.SEP
        
        newLimb = self.__class__()
        for attr,data in inspect.getmembers(self):
            if attr.startswith('_'):
                continue
            if type(data) == 'instanceMethod' or type(data)== 'NoneType':
                continue
            value = data
            try:
                #if it's a string replace any 'lefts' or 'rights' and copy
                if isinstance(value,basestring): #string attr
                    if leftToken in value:
                        newLimb.__dict__[attr] = value.replace(leftToken,rightToken)
                    elif rightToken in value:
                        newLimb.__dict__[attr] = value.replace(rightToken,leftToken)
                    else:
                        newLimb.__dict__[attr] = value
                #if it's a Name object make a new one, and copy with flipped left or right
                elif isinstance(value,mpName.Name):
                    newName = mpName.Name(value)
                    newName.mirror()
                    newLimb.__dict__[attr] = newName
                #if it's a number straight copy
                elif type(value) in ('int','float','double','long'):
                    newLimb.__dict__[attr] = value
                #if it's an iterable copy, then search values for lefts and rights
                elif type(value) in ('list','tuple'):
                    copiedIterable = copy.copy(value)
                    for item in copiedIterable:
                        if isinstance(item,basestring):
                            if leftToken in item:
                                item = item.replace(leftToken,rightToken)
                            elif rightToken in item:
                                item = item.replace(rightToken,leftToken)
                    newLimb.__dict__[attr] = copiedIterable


            except TypeError: #if something goes wrong, straight copy
                newLimb.__dict__[attr] = value

        return newLimb

    def setStartEndCtrls(self):
        '''sets the startCtrl and endCtrl properties if they have not already been set.
        These properties are used to hook up pickwalk between limbs. If the limb author
        did not set these attributes this method attempts to guess, first by looking at
        what drives the start and end joints, then simply using the first and last members
        of the .ctrls list.'''
        RIGLOG.info('checking %s startCtrl and endCtrl',self)
        #If this is already set then return
        if self.startCtrl and self.endCtrl:
            RIGLOG.debug('startCtrl and endCtrl already set')
            return
        #Check ctrls to see if they drive start and end joints:
        for ctrl in self.ctrls:
            joint=mpRig.getJointFromCtrl(ctrl)
            #This can fail with exotic ctrl->joint connections, so if that's the case
            #then bail. Only checking straightforward connections (FK ctrls mostly)
            if not joint: 
                continue
            if not self.startCtrl:
                if joint==self.startJoint:
                    self.startCtrl=ctrl
                    RIGLOG.debug('startCtrl set to %s',ctrl)
            if not self.endCtrl:
                if joint==self.endJoint:
                    self.endCtrl=ctrl
                    RIGLOG.debug('endCtrl set to %s',ctrl)
        #fallback, simply use first and last ctrls
        if not self.startCtrl:
            self.startCtrl=self.ctrls[0]
            RIGLOG.debug('startCtrl fallback to %s',self.ctrls[0])
        if not self.endCtrl:
            self.endCtrl=self.ctrls[-1]
            RIGLOG.debug('endCtrl fallback to %s',self.ctrls[-1])   
        
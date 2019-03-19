'''Base classes for limbs

Limbs are units or blocks of a rig that can be chained together to create
a full character. They hold the code where the ctrls, constraints, ik solvers, etc. are
actually created and attached that make the rig. One, twenty, or hundreds of limbs 
could work together in a rig to move the skeleton in an animator friendly way.

The base Limb class implements the most generic limb. It hooks onto at least one incoming 
transform via it's 'pinParent' or 'pinWorld', and it drives one more more joints given via
it's startJoint (and perhaps endJoint) attribute(s).

It also maintains name info, can make controls, and constrain things together. 
It does book keeping with object sets after building so animation tools can be easily written to snap, 
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

rigLog = logging.getLogger('rig.limb')

class Limb(object):
    '''This is a virtual base class for all other limbs.
    All implemented limbs should inherit from this class or it's children.
    Limbs are used inside a build script, by instancing them and then passing them
    to the rig's addLimb() method.

    Attrs:
    - name: the limb's name object. TDs usually set the 'part' and 'loc' in the build
            script, but they are initialized to 'Limb' and 'M'.
    - startJoint: the first (possibly only) joint driven by the limb. Set by the
                  TD in the rig build script.
    - endJoint: the last joint driven by a limb, which when taken with startJoint
                may form a chain. May be optional.
    - rig: the rig object this limb is being built under. Set when called 
           with 'addLimb' by a rig object.
    - limbNode: the top level transform node of the limb. Set when the limb begins
                building, and used frequently internally to parent things under the limb.
    - noXform: a group made under the limbNode that has 'inheritsTransform' off. Set
               when the limb begins, it gives a usefull place to keep nodes that 
               shouldn't move or be touched by animators.
    - ctrls: a list of all ctrls made during limb build.
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
        
        self.rig = None
        self.limbNode = None
        self.noXform = None
        self.ctrls = []
        
        self.pinParent = None
        self.pinWorld = None

    def __repr__(self):
        return '%s %s_%s' % (self.__class__.__name__, self.name.part, self.name.loc)
        
    def __gt__(self,other):
        '''Override greater than (>) to do pinParent constraining'''
        rigLog.info('wiring %s pinParent to %s'%(self,other))
        if self.pinParent and cmds.objExists(self.pinParent):
            cmds.parentConstraint(other,self.pinParent,mo=True)
        else:
            raise RuntimeError('Cannot constrain, .pinParent not found on limb obj')
            
    def __rshift__(self,other):
        '''Override rshift (>>) to do pinWorld constraining'''
        rigLog.info('wiring %s pinWorld to %s'%(self,other))
        if cmds.objExists(self.pinWorld):
            cmds.parentConstraint(other,self.pinWorld,mo=True)
        else:
            raise RuntimeError('Cannot constrain, .pinWorld not found on limb obj')
            
    def addPinParent(self):
        '''Creates a transform to act as an 'incoming parent' hook for the limb.
        Sets the .pinParent attr on the limb to this object, and returns it.
        '''
        rigLog.debug('adding pin parent')
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
        rigLog.debug('adding pin world')
        self.name.desc = mpName.PINWORLD
        self.pinWorld = cmds.group(em=True,n=self.name.get(),p=self.limbNode)
        if self.startJoint:
            cmds.xform(self.pinWorld,ws=True,m=cmds.xform(self.startJoint,ws=True,q=True,m=True))
        return self.pinWorld

    def addPinBlend(self):
        '''Creates a world pin and a parent pin, then makes a blendPin that blends
        between them. Sets a .pinBlend attr on the limb and also returns it.
        '''
        rigLog.debug('added pin blend setup')
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
        rigLog.info('begin limb %s'%self)
        self.begin()
        rigLog.debug('limb build')
        self.build()
        rigLog.debug('ending limb build')
        self.end()
        rigLog.info('limb build complete')
        
    def begin(self):
        '''Limb build setup. Make a top level node, some nodes that are on all limbs'''
        self.getLimbNode()
        
        #create a noXform node
        self.name.desc='NoXform'
        self.noXform = cmds.createNode('transform', n=self.name.get(),   p=self.limbNode)
        cmds.setAttr(self.noXform+'.inheritsTransform', 0)
        
    def end(self):
        '''Runs at end of limb creation'''
        self.instanceLimbNodeShape()
        mpAttr.visOveride(self.noXform,0)
        
    def build(self):
        raise NotImplementedError('You must implement a "build" method in your Limb class')
        
    def addCtrl(self,name,type='FK',shape='sphere',size=1.0,segments=13,parent=None,color=None,shapeXform=None,xform=None):
        '''Adds a ctrl to this limb.
        A wrapper for lib.addCtrl, but hooks ctrl vis up to limb, and adds name suffix.

        name should be simple, like '01', or 'Upper'. The limb takes care of the rest.
        
        The name convention used here is specified in mpName, which is also used 
        to sort controls after building into sets by rigBase.Rig.addLimbSets().
        '''
        rigLog.debug('Adding %s control %s'%(type,name))
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
        rigLog.debug('deleting control %s'%ctrl)
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
        shape = cmds.createNode('mesh',p=self.limbNode,n=self.limbNode+mpName.LIMBSHAPE)
        
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
        rigLog.debug('adding limb attribute %s'%attrName)
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
        rigLog.debug('instancing limbNode shape %s under ctrls'%limbShape)
        for ctrl in self.ctrls:
            inst = cmds.instance(limbShape)
            instShape = cmds.listRelatives(inst,s=True)[0]
            cmds.parent('%s|%s'%(inst[0],instShape),ctrl,s=True,r=True)
            cmds.delete(inst)

    def addFKChain(self,startJoint,endJoint,parent):
        '''Create chain of FK ctrls on given joints, returns list of created ctrls
        - parent = parent of the first ctrl
        '''
        rigLog.debug('adding FKChain')
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

        #constrain fk ctrls to local/world
        firstFKZero = cmds.listRelatives(fkCtrls[0],p=True)[0]
        cmds.parentConstraint(localParent,firstFKZero,mo=True)

        #Create IK Chain
        rigLog.debug('Adding IK Chain')
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

        #make a stub joint and SCIKsolver so the last ctrl will rotate the last joint
        #in IK mode
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
        cmds.parentConstraint(endNull,stubHandle,mo=True)
        mpCache.flag(stubJoint,False) #don't want stub joints saved in jointSRTs

        #constrain everything
        cmds.parentConstraint(endCtrl,endNull,mo=True)
        cmds.parentConstraint(endNull, handle,mo=True)
        cmds.poleVectorConstraint(aimCtrl,handle)

        #make the aim float between end and root of ik system
        cmds.pointConstraint(endCtrl,worldParent,aimZero,mo=True)

        #Construct the blend
        FKIKblender = self.addAttrLimb(ln=mpName.FKIKBLENDATTR, at='float',min=0,max=1,dv=0,k=True)
        cmds.connectAttr(FKIKblender, handle+'.ikBlend')
        cmds.connectAttr(FKIKblender, stubHandle+'.ikBlend')

        #switch ctrl vis
        for ctrl in (aimCtrl,endCtrl):
            shape = cmds.listRelatives(ctrl,s=True)[0]
            mpAttr.connectWithAdd(FKIKblender,shape+'.v',0.4999999)
        for ctrl in fkCtrls:
            shape = cmds.listRelatives(ctrl,s=True)[0]
            adder = mpAttr.connectWithAdd(FKIKblender,shape+'.v',-0.4999999)
            revNode = mpAttr.connectWithReverse(adder+'.output',shape+'.v',force=True)
        
        mpRig.addPickParent(aimCtrl,endCtrl)
        mpRig.addPickParent(endCtrl,aimCtrl)

        #setup IK->FK snapping messages
        mpRig.addSnapParent(endCtrl, fkCtrls[-1]) 
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
        rigLog.debug('mirroring limb')
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
                            if valuleftToken in item:
                                item = item.replace(leftToken,rightToken)
                            elif rightToken in item:
                                item = item.replace(rightToken,leftToken)
                    newLimb.__dict__[attr] = copiedIterable


            except TypeError: #if something goes wrong, straight copy
                newLimb.__dict__[attr] = value

        return newLimb


        
        
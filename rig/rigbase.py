'''Rig base classes.

These classes outline a build process that consists of a preparation phase 
(begin), the building of the rig (build), and a cleanup (end) phase. They also 
implement all the helper methods required to make that process consistent, 
while allowing you to customize rig setup to suit your facility. 

Ideally, after extending these or the other base classes to conform to your pipeline, 
your character TDs need only to write a subclass that implements the 'build' method. 
This script is their 'character rig', and should be run any time a rig change is needed.
 
To build a rig their sub class should be instanced in Maya and a call made to
the .create() method. 
'''

import os
import getpass
import logging
import maya.cmds as cmds

import mpyr.lib.dag as mpDag
import mpyr.lib.ctrl as mpCtrl
import mpyr.lib.attr as mpAttr
import mpyr.lib.name as mpName
import mpyr.lib.rig as mpRig
import mpyr.lib.cache as mpCache
import mpyr.rig.limb.generic as limbGen

RIGLOG = logging.getLogger('rig')

class Rig(object):
    '''This is a virtual base class for all other rigs, and is where most of the generic
    rigging code is implemented. Actual rigs should inherit from a more specific subclass
    such as AnimRig

    Attrs:
    - rigScale: Used by various functions to scale cosmetic appearances. Defaults to 1.
    - limbs: a list populated during build of all limbs in the rig. The first limb 
             is always the world offset.
    - rigNode: the top group node of the rig, created during build.
    - rigName: the default name of the rig, set either by the TD or by setRigNameDefault()
    - rootJoint: the rootJoint of the rig's skeleton, set automatically when importSkeleton 
                 is called.
    - geoPath: An optional path used to import a geometry.ma file during build. Set by a 
               TD before build.
    - weightPath: an optional path to import deformer weights. Set by a TD before build.
    - skeletonPath: a path to the skeleton. Set by a TD before build.
    - rigVersion: an optional attribute that will be stored on the rig for bookkeeping.
                  Set by a TD before build.

    '''  
    def __init__(self):
        object.__init__(self)
        RIGLOG.debug('init')
        
        #This is a cosmetic setting for ctrl sizes and whatnot.
        self.rigScale = 1
        
        #this list gets appended to when limbs are added
        self.limbs = []
        
        #These properties are filled in as the rig builds
        self.rigNode = None      #the top transform for the rig, all things parented under this
        self.rigName = None      #the name of the rig. Default set in setRigNameDefault
        self.rootJoint = ''      #the root joint of the skeleton
        self.limbNode = None     #The transform that limbs are parented under
        self.geoNode = None      #The transform that geometry is parented under
        self.skeletonNode = None #The transform that the skeleton is parented under
        self.masterSet = None    #The top level object set
        self.ctrlSet = None      #The object set that will hold all the ctrls that are built
        self.cacheSet = None     #The object set that will hold all cacheable nodes
        self.loadSet = None      #The object set that will hold all nodes that can receive cache


        #Attrs set before build, used to import files/weights/etc. Can be set automatically based
        #on pipeline standards or a database.
        self.geoPath = ''
        self.weightPath = ''
        self.skeletonPath = ''
        
        self.rigVersion = ''    #bookkeeping for pipeline, stored as an attr on the rigNode. Set if
        
    def __repr__(self):
        return '%s %s' % (self.__class__.__name__, self.rigName)

    def create(self):
        '''Builds the rig by calling the creation methods in the correct 
        order.
        '''
        RIGLOG.info('beginning rig build')
        self.begin()
        RIGLOG.info('building rig')
        self.build()
        RIGLOG.info('ending build')
        self.end()
        RIGLOG.info('rig complete')
        
    def begin(self):
        '''Pre build actions'''
        cmds.file(new=True, f=True)

        RIGLOG.debug('making rig nodes')
        self.setRigNameDefault()  
        self.addRigNode()
        self.addMasterSet()
        
        #Make some top level nodes
        self.limbNode = cmds.createNode('transform', n='limbs', p=self.rigNode)
        self.geoNode = cmds.createNode('transform', n='geo', p=self.rigNode)
        self.skeletonNode = cmds.createNode('transform', n='skel', p=self.rigNode)
        
        # Setup visibility attrs 
        plumin  = cmds.createNode('plusMinusAverage', n=self.rigNode+'Vis_plumin')
        
        #This kind of geo/skeleton/mesh hiding or showing mechanism is optional.
        #Some animators like it, some prefer ctrl+h, some prefer layers, etc.
        #geo
        geoattr = self.rigNode+'.geoVis'
        cmds.addAttr(self.rigNode, ln='geoVis', at='enum', en='off:on:template:reference:seg', k=True,dv=1 )
        cmds.setAttr( self.geoNode+'.overrideEnabled', 1 )
        cmds.connectAttr( geoattr, self.geoNode+'.overrideVisibility' )
        cmds.setAttr( plumin+'.operation', 2 )
        cmds.setAttr( plumin+'.input1D[1]', 1 )
        cmds.connectAttr( geoattr, plumin+'.input1D[0]' )
        cmds.connectAttr( plumin+'.output1D', self.geoNode+'.overrideDisplayType' )
        cmds.setAttr(geoattr, 1 )

        # rig
        rigattr = self.rigNode+'.rigVis'
        cmds.addAttr(self.rigNode, ln='rigVis', at='long', max=1, min=0, k=True,dv=1)
        cmds.setAttr(rigattr, 1)
        cmds.setAttr(self.limbNode+'.overrideEnabled', 1)
        cmds.connectAttr(rigattr, self.limbNode+'.overrideVisibility')
    
        # skel
        skelattr = self.rigNode+'.skelVis'
        cmds.addAttr(self.rigNode, ln='skelVis', at='long', max=1, min=0, k=True,dv=1)
        cmds.setAttr(self.skeletonNode+'.overrideEnabled', 1)
        cmds.connectAttr(skelattr, self.skeletonNode+'.overrideVisibility')

        #create the world offset
        offset = limbGen.WorldOffset()
        self.addLimb(offset)
        
        # rig book keeping attrs.
        # these can be useful later when debugging scenes, to know
        # where things came from and when.
        cmds.addAttr(self.rigNode,
            ln='rigVersion', 
            dt='string', 
            keyable=False
            )
        cmds.setAttr(self.rigNode+'.rigVersion', self.rigVersion, type='string')

        cmds.addAttr(self.rigNode,
            ln='buildDate', 
            dt='string', 
            keyable=False
            )
        cmds.setAttr(self.rigNode+'.buildDate', cmds.date(), type='string')

        cmds.addAttr(self.rigNode,
            ln='builtBy', 
            dt='string', 
            keyable=False
            )
        cmds.setAttr(self.rigNode+'.builtBy', getpass.getuser(), type='string')


    def build(self):
        '''All build actions. This is a virtual method, it should be implemented by 
        rig build classes that inherit from this object'''
        raise NotImplementedError("You must implement a 'build' method in your Rig class")
        
    def end(self):
        '''Post build actions'''
        #Add object sets for caching
        self.addCacheSet()
        self.addLoadSet()

        #Add object sets used for animation tools
        self.addLimbSets()
        self.addAllCtrlSet()

        #lock and cleanup
        self.lock()
        self.cleanupDanglingLimbs()

        #add mirror info to every ctrl since we are in root pose now
        for limbObj in self.limbs:
            for ctrlNode in limbObj.ctrls:
                mpRig.addMirrorInfo(ctrlNode)

        
    def setRigNameDefault(self):
        '''If nothing has set rigName this sets it to the class name. Override this function if
        you want the default name for your studio's rigs to be different.
        '''
        if not self.rigName:
            default = self.__class__.__name__
            RIGLOG.warning('rig name not set, using default class name %s', default)
            self.rigName = default
        
    def addRigNode(self):
        '''Creates the top level group node for a rig. All other rig DAG nodes will be
        parented underneath this node. When this node is made it is set to self.rigNode.
        This node is named after the rig.rigName attribute.
        '''
        if cmds.objExists(self.rigName):
            raise RuntimeError('Could not create main rig node. Node of name %s already exists.', self.rigName)
        self.rigNode = cmds.createNode('transform',n=self.rigName)
        mpAttr.addAttrSwitch(self.rigNode+'.isRig',keyable=False,type='bool',value=1)
        RIGLOG.debug('created root node %s', self.rigNode)

        return self.rigNode
        
    def importSkeleton(self):
        '''Import the file specified with .skeletonPath'''
        self.getFile(self.skeletonPath,underGroup=True,underGroupName=self.skeletonNode)

        #set root joint attr if not yet set
        if not self.rootJoint:
            children = cmds.listRelatives(self.skeletonNode,type='joint') or []
            for child in children:
                if mpName.ROOTJOINT in child.lower():
                    self.rootJoint = child
                    break
        if not self.rootJoint:
            RIGLOG.warning('root joint not found in imported skeleton %s', self.skeletonPath)

    def importGeo(self):
        '''Import the file specified with .geoPath'''
        if self.geoPath:
            self.getFile(self.geoPath,underGroup=True,underGroupName=self.geoNode)
        
               
    def getFile(self,fileName,underGroup=True,underGroupName=None):
        '''Manage file imports in Maya. Given a path, import that file. This is also the 
        place to implement resource types. For example, if you want users to be able to call
        getFile('skeleton'), implement the code here that finds skeleton files in your
        production database.
        
        By default this method groups the imported nodes, which it puts under the rig group. 
        The underGroupName flag can be used to override the name of this new group,
        otherwise the file name is used. If it is set to False then no group is made. The
        new nodes are still parented under the main rig node.
        
        If no group is made the root nodes are returned. If a group is made the group is 
        returned.
        '''
        RIGLOG.info('importing file %s', fileName)

        if not os.path.exists(fileName):
            raise IOError('File path %s not found, cannot getFile', fileName)
        fullPath = fileName
        filePath,fileName = os.path.split(fullPath)
        splitFileName = fileName.split('.')
        fileName = '.'.join(splitFileName[:-1]) #some people use dots in fileNames a lot
        
        #Import file
        nodeList = self.fileImport(fullPath)
        rootNodes = mpDag.getRootNodes(nodeList)
        
        RIGLOG.debug('file import done, %s new root nodes', len(rootNodes))
        
        #if underGroup=False simply return a list of new nodes that are root nodes
        if not underGroup:
            for node in rootNodes:
                cmds.parent(node,self.rigNode)
            RIGLOG.debug('file imported under rigNode %s', self.rigNode)
            return rootNodes
        
        #If underGroup=True we must make the group. First, determine what name it will be.
        if not underGroupName:
            underGroupName = fileName
            
        #Create group and parent nodes
        if not cmds.objExists(underGroupName):
            cmds.group(n=underGroupName,em=True,p=self.rigNode)
            
        for node in rootNodes:
            cmds.parent(node,underGroupName)
        
        RIGLOG.info('file imported under group %s', underGroupName)
        return underGroupName

            
    def fileImport(self,filePath):
        '''Imports a given file. Implement new file imports by extending this method.
        This method returns a list of nodes imported.
        '''
        fpLower = filePath.lower()
        if fpLower.endswith('.ma'):
            return cmds.file(filePath,i=True,rnn=True,type='mayaAscii')
        elif fpLower.endswith('.mb'):
            return cmds.file(filePath,i=True,rnn=True,type='mayaBinary')
        else:
            raise IOError('Unknown file type, cannot getFile %s' % filePath)
            
    def lock(self):
        '''Lock and hide nodes that shouldn't be touched'''
        RIGLOG.info('locking rig')

        cmds.setAttr(self.rigNode+'.rigVersion', lock=True)
        cmds.setAttr(self.rigNode+'.buildDate', lock=True)
        cmds.setAttr(self.rigNode+'.builtBy', lock=True)

        for node in (self.limbNode,self.geoNode,self.skeletonNode,self.rigNode):
            mpAttr.lockAndHide(node,['t','r','s','v'])
        for limb in self.limbs:
            mpAttr.lockAndHide(limb.limbNode,['t','r','s','v'])

    def cleanupDanglingLimbs(self):
        '''Clean up pinParents and pinWorlds not constrained after build.
        See if they are connected to something, and if not constrain to
        the world offset.
        '''
        RIGLOG.info('constraining floating limbs')
        for limb in self.limbs:
            if limb.pinWorld:
                #check for cns
                cnx = cmds.listConnections(limb.pinWorld+'.tx',s=1,d=0)
                if not cnx:
                    #cns to the last ctrl of the first limb (the world offset)
                    RIGLOG.debug('limb %s not constrained, attaching to world', limb)
                    cmds.parentConstraint(self.limbs[0].ctrls[-1],limb.pinWorld,mo=True)
            elif limb.pinParent:
                #check for cns
                cnx = cmds.listConnections(limb.pinParent+'.tx',s=1,d=0)
                if not cnx:
                    #cns to the last ctrl of the first limb (the world offset)
                    RIGLOG.debug('limb %s not constrained, attaching to world', limb)
                    cmds.parentConstraint(self.limbs[0].ctrls[-1],limb.pinParent,mo=True)
            
    def addMasterSet(self):
        '''Creates the top level object set for the rig'''
        self.masterSet = cmds.sets(em=True,n=self.rigNode+'_MASTERSET')
        
    def addCacheSet(self):
        '''Creates the object set that can hold objects that should be cached'''
        self.cacheSet = cmds.sets(em=True,n=self.rigNode+'_CACHESET')
        cmds.sets(self.cacheSet,add=self.masterSet)
        
    def addLoadSet(self):
        '''Creates an object set that holds objects that should receive a cache'''
        self.loadSet = cmds.sets(em=True,n=self.rigNode+'_LOADSET')
        cmds.sets(self.loadSet,add=self.masterSet)
        
    def addLimbSets(self):
        '''Goes through all built limbs and creates ctrl sets for each one. Run at end
        of rig building by end() function.

        The IK and FK sets are used for easily switching IK and FK on controls. The other
        'ctrls' set is just used to dump everything else, so with all three sets together 
        every control can easily be found by animation tools.
        
        FK/IK ctrls are sorted into sets by name. It's specified here, and when the ctrls are made, 
        by the convention in lib/name.py
        '''
        RIGLOG.info('adding limb ctrl sets')
        for limb in self.limbs:
            ctrls = []
            fkCtrls = []
            ikCtrls = []
            allNodes = cmds.listRelatives(limb.limbNode,ad=True)
            for node in allNodes:
                if mpCtrl.isCtrl(node):
                    if node.endswith(mpName.FKCTRL):
                        fkCtrls.append(node)
                    elif node.endswith(mpName.IKCTRL):
                        ikCtrls.append(node)
                    else:
                        ctrls.append(node)
            limbSet = cmds.sets(em=True,n=limb.limbNode+'_'+mpName.CTRLSET)
            cmds.sets(limbSet,add=self.masterSet)
            if fkCtrls:
                fkSet = cmds.sets(em=True,n=limb.limbNode+'_'+mpName.CTRLSETFK)                            
                cmds.sets(fkSet,add=limbSet)
                cmds.sets(fkCtrls,add=fkSet)
            if ikCtrls:
                ikSet = cmds.sets(em=True,n=limb.limbNode+'_'+mpName.CTRLSETIK)  
                cmds.sets(ikSet,add=limbSet)
                cmds.sets(ikCtrls,add=ikSet)
            if ctrls:
                ctrlSet = cmds.sets(em=True,n=limb.limbNode+'_'+mpName.CTRLSET)  
                cmds.sets(ctrlSet,add=limbSet)
                cmds.sets(ctrls,add=ctrlSet)

    def addAllCtrlSet(self):
        '''create a set with all ctrl, called when limb building is done'''
        allCtrls=[]
        for limb in self.limbs:
            allNodes = cmds.listRelatives(limb.limbNode,ad=True)
            for node in allNodes:
                if mpCtrl.isCtrl(node):
                    allCtrls.append(node)
        self.ctrlSet=cmds.sets(em=True,n=self.rigNode+'_'+mpName.ALLCTRLSET)
        cmds.sets(self.ctrlSet,add=self.masterSet) 
        cmds.sets(allCtrls,add=self.ctrlSet)
                
        
    def addLimb(self,limbObj):
        '''build the given limb obj and add it to the rig'''
        limbObj.rig = self
        RIGLOG.info('adding limb %s', limbObj)
        limbObj.create()
        self.limbs.append(limbObj)
        
        
class AnimRig(Rig):
    '''An AnimRig uses controls to drive joints. This is the primary rig of an animation
    pipeline. It is the rig that animators use. It may deform mesh, or it may
    only produce joint data for use in a game engine or by a DeformRig.
    
    Barring mocap skeletons, AnimRigs usually have an empty loadSet, since they are 
    driven by animators. Their cacheSet may have mesh, joints, or both depending on
    your pipeline's requirements.
    
    It is up to your pipeline to find the contents of these sets and handle the caching 
    appropriately. They are only provided for convenience.
    '''
    def addCacheSet(self):
        Rig.addCacheSet(self)
        
        #add skeleton to cache set
        joints = cmds.listRelatives(self.skeletonNode,type='joint',ad=True)
        if joints:
            for jnt in joints:
                #if joint explicitly flagged not to cache then skip it
                if mpCache.isFlagged(jnt) and not mpCache.getFlag(jnt):
                    continue
                RIGLOG.debug('flagging %s to cache', jnt)
                cmds.sets(jnt,add=self.cacheSet)
                mpCache.flag(jnt,True)

    
class DeformRig(Rig):
    '''A DeformRig reads joint SRT data and uses it to deform mesh. It is an accessory 
    to an AnimRig.
    
    If mesh is really heavy, or requires simulation, you may with to implement those 
    deformers on a DeformRig instead of an AnimRig. By baking joint SRTs off of an anim 
    rig and handling deformations on the DeformRig instead, the AnimRig can remain fast 
    and keep animation scenes clean.
    
    Deform rigs usually have the skeleton joints in the loadSet, and any mesh to be 
    cached in the cacheSet.
    '''
    def addLoadSet(self):
        Rig.addLoadSet(self)
        
        #add skeleton to load set
        joints = cmds.listRelatives(self.skeletonNode,type='joint',ad=True)
        for jnt in joints:
            cmds.sets(jnt,add=self.loadSet)
    
    def addCacheSet(self):
        Rig.addCacheSet(self)
        
        #add mesh to cache set
        meshNodes = cmds.listRelatives(self.geoNode,type='transform',ad=True)
        for meshNode in meshNodes:
            #if mesh explicitly flagged not to cache then skip it
            if mpCache.isFlagged(meshNode) and not mpCache.getFlag(meshNode):
                continue
            RIGLOG.debug('flagging %s to cache', meshNode)
            cmds.sets(meshNode,add=self.cacheSet)
            mpCache.flag(meshNode,True)
    
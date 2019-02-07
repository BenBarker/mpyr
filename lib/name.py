'''Naming convention spec
The rest of the rigging scripts should use these defaults/classes when trying to parse
names. That way if the naming convention needs to change it only needs to change here.
'''
import maya.cmds as cmds

#defaults for general naming convention
SEP = '_'
LEFT = 'L'
RIGHT = 'R'
MID = 'M'
LOC = MID
PART = 'Main'
DESC = '01'

#Defaults for rig nodes and attributes
PINPARENT = 'pinParent'             #transform created by addPinParent in limbBase
PINWORLD = 'pinWorld'               #transform created by addPinWorld in limbBase
PINBLEND = 'pinBlend'               #transform created by addPinBlend in limbBase
ROOTJOINT = 'root'                  #case insensitive pattern, used by rigBase.importSkeleton to verify the root joint
LIMBNAME = 'LIMB'                   #suffix added to limb nodes
LIMBSHAPE = 'Attrs'                 #suffix added to limb node shapes, that animators will see in channel box.
LIMBBLENDATTR = 'localWorldBlend'   #default name for pinBlend attribute
FKCTRL = 'FKCTRL'                   #name suffixes for ctrls
IKCTRL = 'IKCTRL'
CTRL = 'CTRL'
OBJSET = 'SET'                     #name suffixes for ctrl object sets on limbs
CTRLSET = 'CTRLS'
CTRLSETFK = 'CTRLSFK'
CTRLSETIK = 'CTRLSIK'
FKIKBLENDATTR = 'FKIK'              #any attr that blends IK/FK 

def getLocation(node):
    '''given a node, return the location string. Return None if not found'''
    ctrlNameParts = node.split(SEP)
    for part in ctrlNameParts:
        if part in (LEFT,RIGHT,MID):
            return part
    return None


class Name(object):
    '''Helps manage naming with the Part_Loc_Desc name scheme. 
    For example 'Arm_R_joint05FK'
    Also enforces duplicate name checking when names are fetched, but that can be
    disabled.
    
    '''
    def __init__(self,*args):
        #defaults:
        self.sep = SEP
        self.loc = LOC
        self.part = PART
        self.desc = DESC
        
        if len(args) == 3:
            self.part = args[0]
            self.loc = args[1]
            self.desc = args[2]
        elif len(args) == 1:
            self.parse(args[0])            
        
    def get(self,noCheck=False):
        '''return the name as a string'''
        if not self.part or not self.loc or not self.desc:
            raise RuntimeError("invalid name: '%s _ %s _ %s" % (self.part,self.loc,self.desc))
        strName = self.sep.join([self.part,self.loc,self.desc])
        if cmds.objExists(strName) and noCheck == False:
            raise RuntimeError("can't name already exists: %s" % strName)
        return strName

    def mirror(self):
        '''flip the location from one side to another, useful when mirroring a limb'''
        if self.loc == LEFT:
            self.loc = RIGHT
        elif self.loc == RIGHT:
            self.loc = LEFT
        
    def parse(self,obj):
        '''given an object, attempt to set this object based on its name'''
        #try another name object:
        if isinstance(obj,Name):
            self.sep = obj.sep
            self.loc = obj.loc
            self.part = obj.part
            self.desc = obj.desc
        #if not, try a string:
        else:
            nameParts = obj.split(self.sep)
            locIdx = None
            if len(nameParts) > 1:
                if LEFT in nameParts:
                    self.loc = LEFT
                    locIdx = nameParts.index(self.loc)
                elif RIGHT in nameParts:
                    self.loc = RIGHT
                    locIdx = nameParts.index(self.loc)
                else:
                    self.loc = MID
            else:
                self.desc = nameParts[0]
                     
            if locIdx:
                self.part = ''.join(nameParts[:locIdx])
                self.desc = ''.join(nameParts[locIdx+1:])
        
            
            
        
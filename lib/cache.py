'''Library for caching joints/mesh'''
import mpyr.lib.name as mpName
import maya.cmds as cmds

def getFlag(obj):
    '''returns cache flag value on object, False if not flagged'''
    attrName = '%s.%s'%(obj,mpName.CACHEATTR)
    if not isFlagged(obj):
        return False
    return cmds.getAttr(attrName)

def isFlagged(obj):
    '''returns if object is flagged, NOT value of flag, just if flag attr exists'''
    attrName = '%s.%s'%(obj,mpName.CACHEATTR)
    return cmds.objExists(attrName)

def flag(obj,value=True):
    '''flag an object for caching'''
    attrName = '%s.%s'%(obj,mpName.CACHEATTR)
    if not isFlagged(obj):
        cmds.addAttr(obj,ln=mpName.CACHEATTR,at='bool',k=False)
    cmds.setAttr(attrName,value)

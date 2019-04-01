'''Functions associated with creating and modifying controls, or the nodes that animators
will be putting keyframes on.'''
import math
import os
import json
import maya.cmds as cmds
import maya.mel as mel
import attr
import name
import fileIO
import rigmath
import rig

#List of available curve ctrl types
CTRLTYPES=['sphere','cube','box','circle','cross','square','pyramid','line','spoon']

def addCtrl(ctrlname,shape='sphere',size=1.0,segments=13,parent=None,color=None,shapeXform=None,xform=None):
    '''make a ctrl with a given shape out of a curve, parented under a zero null
    shape: sphere,cube,circle,cross,pyramid,line,spoon
    size: defaults to 1.0
    segments: used on round shapes, defaults to 13
    parent: object to parent under (if any)
    color: maya color name or color index
    shapeXform: a matrix or object (uses worldMatrix) to transform ctrl shape with. This is only cosmetic.
    xform: an object, vector, or matrix to xform the transform and rotationOrder of the ctrl
    '''
    #get shape with name
    crv = getCurve(shape,size=size,segments=segments)

    #rename and make zero null
    crv = cmds.rename(crv,ctrlname)
    zero = cmds.createNode('transform',n=crv + "_Zero")
    attr.hideAnimChannels(zero)
    
    #lock scale
    #In the rare cases that a ctrl must be scaled this can simply be unlocked.
    #Otherwise this saves a lot of headache later IMO.
    attr.lockAndHide(crv,'s')

    #parent under zero null so it's local xforms are zero
    cmds.parent(crv,zero)
    
    #set color based on argument, or position (based on name) if not specified
    if not color:
        color = getPositionColor(ctrlname)
    setColor(ctrlname,color)

    #do transforming (if given)
    if shapeXform:
        cluster = cmds.cluster(crv)
        xfMatrix = rigmath.Transform(shapeXform)
        cmds.xform(cluster,ws=True,m=xfMatrix.get())
        cmds.delete(crv,ch=True)
    else:
        shapeXform = rigmath.Transform()
        
    if parent:
        cmds.parent(zero,parent)

    #store shape transform for later, if needed
    cmds.addAttr(crv,dt='matrix',ln='shapeMatrix')
    shapeXform.scale(size)
    cmds.setAttr(crv+'.shapeMatrix',*shapeXform.get(),type='matrix')
    
    #flag
    setAsCtrl(crv)

    if xform:
        #if name of node then math matrix and rotate order
        if isinstance(xform,str) and cmds.objExists(xform):
            matchMatrix = cmds.xform(xform,q=True,ws=True,m=True)
            attr.matchAttr(xform,zero,"rotateOrder")
            attr.matchAttr(xform,crv,"rotateOrder")
        #otherwise just match matrix.
        #wrapping a Transform here for convenience
        else:
            try:
                matchMatrix = rigmath.Transform(xform).get()
            except RuntimeError:
                raise RuntimeError("Couldn't find object or transform %s to match"%xform)
        cmds.xform(zero,ws=True,m=matchMatrix)
    return (zero,crv) 

def changeCtrlShape(ctrl,newShape,shapeXform=None,size=1.0,segments=13):
    '''given a ctrl and a new shape, swap the shape. If shapeXform is given it will
    override the ctrl's shapeMatrix.
    '''
    newCrv = getCurve(shape=newShape,size=size,segments=segments)
    if not shapeXform:
        if cmds.objExists(ctrl+'.shapeMatrix'):
            shapeXform = rigmath.Transform(cmds.getAttr(ctrl+'.shapeMatrix'))
    if shapeXform:
        shapeXform.scale(size)
        cluster = cmds.cluster(newCrv)
        xfMatrix = rigmath.Transform(shapeXform)
        cmds.xform(cluster,ws=True,m=xfMatrix.get())
        cmds.delete(newCrv,ch=True)
        cmds.setAttr(ctrl+'.shapeMatrix',*shapeXform.get(),type='matrix')

    newShape = cmds.listRelatives(newCrv,s=True)[0]
    oldShape = cmds.listRelatives(ctrl,s=True)[0]
    cmds.connectAttr(newShape + ".local", oldShape + ".create",force=True)
    cmds.delete(cmds.cluster(oldShape)) #force update of crv shape
    cmds.delete(newCrv)

def getCurve(shape,size=1.0,segments=13):
    '''given a shape name return the corresponding curve.
    Wrapper for the various getCube,getSphere etc functions in this module
    '''    
    shapeFactory = {
        'sphere':makeSphere,
        'cube':makeCube,
        'box':makeCube,
        'circle':makeCircle,
        'cross':makeCross,
        'square':makeSquare,
        'pyramid':makePyramid,
        'line':makeLine,
        'spoon':makeSpoon
        }
    try:
        crv = shapeFactory[shape](size=size,segments=segments)
    except KeyError:
        raise RuntimeError("unknown ctrl shape argument: %s"%shape)
    return crv

def getPositionColor(ctrlname):
    ''' Given a control, return a color based on 'left' 'right'
    or 'center' position of the control. This is done based on
    the naming convetion.
    '''
    lfColor = "light blue"
    rtColor = "red"
    cnColor = "yellow"
    if '%s%s%s' % (name.SEP,name.LEFT,name.SEP) in ctrlname:
        return lfColor
    elif'%s%s%s' % (name.SEP,name.RIGHT,name.SEP) in ctrlname:
        return rtColor
    else:
        return cnColor
 
def setColor(ctrl,color):
    '''set color on given object, take int or color name'''
    try:
        color = int(color)
    except ValueError:
        color = getMayaColor(color)
    cmds.setAttr( ctrl + ".overrideEnabled", 1 )
    cmds.setAttr( ctrl + ".overrideColor", color)
    
def setAsCtrl(obj):
    '''add an attribute that identifies this as a ctrl'''
    if not isCtrl(obj):
        attr.addAttrSwitch(obj + ".isCtrl",keyable=False,type='bool',value=1)
    cmds.setAttr(obj + ".isCtrl",1)
    
def isCtrl(obj):
    '''Return True or False if given object is a ctrl.
    Checks for a boolean attribute that is created by addCtrl
    '''
    if not obj:
        return False
    return cmds.objExists(obj+".isCtrl")

def getMayaColor(color):
    '''Convert the a color into the maya display color value. 
    If a int is given a string is returned and vice versa'''
    colors = ["grey","black","dark grey","light grey","burgundy","navy blue","blue",
              "dark green","dark purple","magenta","dark orange","dark brown",
              "dark red","red","green","dark blue","white","yellow","light blue",
              "aquamarine", "pink", "peach", "light yellow", "sea green", "light brown",
              "barf","lime green","light green","turquoise","royal blue","dark violet",
              "dark magenta"]
    try:
        return colors[color]
    except TypeError: #not given an int
        try:
            return(colors.index(color))
        except ValueError:
            raise TypeError("argument must be color index or maya color name")

def saveCtrlAppearance(ctrlList,filePath,force=True,search='',replace=''):
    '''given a list of ctrls, save file containing curve ctrl appearence info.
    Force will overwrite existing file. Default True
    Search/replace will search/replace ctrl name before saving'''
    #check path
    fileIO.ensurePath(filePath,force=force)

    curveData=dict()
    for ctrl in ctrlList:
        ctrlName=ctrl
        if search and replace:
            ctrlName = ctrl.replace(search,replace)
        #get shape node
        ctrlShape=cmds.listRelatives(ctrl,type='nurbsCurve')
        if not ctrlShape:
            raise RuntimeError('curve shape not found under node: %s'%ctrl)
        ctrlShape=ctrlShape[0]
        points=cmds.ls(ctrlShape+'.cv[*]',fl=True)
        roundedPoints=[] #space saving
        for point in points:
            roundedPoints.append([round(x,4)for x in cmds.xform(point,objectSpace=True,q=True,t=True)])
        overrideColor=cmds.getAttr(ctrl+'.overrideColor')
        overrideRGBColors=cmds.getAttr(ctrl+'.overrideRGBColors')
        overrideColorRGB=cmds.getAttr(ctrl+'.overrideColorRGB')[0]
        curveData[ctrlName]={
            'p':roundedPoints,
            'oc':overrideColor,
            'oRGB':overrideRGBColors,
            'ocRGB':overrideColorRGB
            }
    jsonString=json.dumps(curveData,sort_keys=True)
    jsonString=jsonString.replace('},','},\n')

    with open(filePath,'w') as outfile:  
        outfile.write(jsonString)

def loadCtrlAppearance(filePath,search='',replace=''):
    '''load a ctrl appearance file into the current scene. Ctrls found by name.
    search and replace are optional arguments to search/replace ctrl names before loading'''
    if not os.path.exists(filePath):
        raise IOError('ctrl appearance file not found:%s'%filePath)
    with open(filePath) as ctrlAppFile:
        data=json.load(ctrlAppFile)
        for ctrlName,ctrlData in data.iteritems():
            if search:
                ctrlName=ctrlName.replace(search,replace)
            if not cmds.objExists(ctrlName):
                continue
            #made tmp ctrl, then swap shape over
            pointData=ctrlData['p']
            tmpCtrl=cmds.curve(d=1, p=pointData,k=range(len(pointData)))
            copyCtrlShape(tmpCtrl,ctrlName)
            cmds.delete(tmpCtrl)

            cmds.setAttr(ctrlName+'.overrideColor',ctrlData['oc'])
            cmds.setAttr(ctrlName+'.overrideRGBColors',ctrlData['oRGB'])
            cmds.setAttr(ctrlName+'.overrideColorRGB',*ctrlData['ocRGB'])

def copyCtrlShape(src,dst):
    '''given a source curve, copy it's shape to destination curve'''
    if cmds.nodeType(src)=='transform':
        src = cmds.listRelatives(src,s=True)[0]
    if cmds.nodeType(dst)=='transform':
        dst = cmds.listRelatives(dst,s=True)[0]
    cmds.connectAttr(src+".worldSpace",dst+".create",force=True)
    cmds.xform(dst+".cv[0]",q=True,ws=True,t=True)#update attribute
    cmds.disconnectAttr(src+".worldSpace",dst+".create")

def mirrorCtrlShape(src,dst=None):
    '''given a source curve, copy it's mirror shape to dst.
    If not dst is given then use rig library to find mirrored ctrl.'''
    #find mirrored ctrl
    if not dst:
        dst=rig.findMirrorCtrl(src)
    if not dst:
        raise RuntimeError("could not find mirror ctrl. Specify with 'dst' arg")

    #find mirror info
    mirrorInfo=rig.getMirrorInfo(dst)
    if not mirrorInfo:
        mel.warning('Mirror info not found on destination ctrl, using -1 -1 -1')
        mirrorInfo=(-1,-1,-1)

    #duplicate the mirrored ctrl
    tmpCtrl=cmds.curve(d=1,p=((0,0,0),(0,1,0)),k=(0,1),n='tmpCtrl')
    cmds.xform(tmpCtrl,ws=True,m=cmds.xform(dst,ws=True,m=True,q=True))
    copyCtrlShape(src,tmpCtrl)

    #create cluster and flip
    tmpCluster=cmds.cluster(tmpCtrl,n='tmpCluster')
    cmds.xform(tmpCluster,p=True,ws=True,sp=cmds.xform(dst,ws=True,q=True,t=True))
    cmds.scale(mirrorInfo[0],mirrorInfo[1],mirrorInfo[2],tmpCluster)
    cmds.delete(tmpCtrl,ch=True)
    
    # copy and delete tmp object
    copyCtrlShape(tmpCtrl,dst)
    cmds.delete(tmpCtrl)

    
def makeCube(size=1.0,**kwargs):
    '''Make a nurbs curve cube with given size.'''
    wd=0.5*size
    crn=[
        (-wd,wd,-wd),
        (wd,wd,-wd),
        (wd,-wd,-wd),
        (-wd,-wd,-wd),
        (-wd,wd,wd),
        (wd,wd,wd),
        (wd,-wd,wd),
        (-wd,-wd,wd),
        ]
    verts = (crn[0],crn[1],crn[2],crn[3],crn[0],crn[4],crn[5],crn[6],
        crn[7],crn[4],crn[5],crn[1],crn[0],crn[4],crn[7],crn[3],crn[0],
        crn[1],crn[2],crn[6])
    return cmds.curve(d=1,p=verts,k=range(len(verts)))
        
def makeCross(size=1.0,**kwargs):
    '''make a cross shape curve with given size'''
    m=size*0.5
    verts = ( [(.25*m),0,.75*m], [(.25*m),0,(.25*m)], [.75*m,0,.25*m], [.75*m,0,-.25*m], 
        [.25*m,0,-.25*m], [(.25*m),0,(-.75*m)], [(.25*m),0,-.75*m], [(-.25*m),0,-.75*m], 
        [(-.25*m),0,(-.25*m)], [-.75*m,0,(-.25*m)], [-.75*m,0,(.25*m)], [(-.25*m),0,(.25*m)], 
        [-.25*m,0,(.75*m)], [(.25*m),0,.75*m] 
        )
    return cmds.curve(degree=1, p=verts,k=range(len(verts)))
        
def makePyramid(size=1.0,**kwargs):
    '''make a pyramid shape curve with given size'''
    m=size*0.5
    nm=m*-1.0
    verts = ([m,0,m],[nm,0,m],[nm,0,nm],[m,0,nm],[m,0,m],[0,1*m,0],[nm,0,m],[nm,0,nm],[0,1*m,0],[m,0,nm])
    return cmds.curve(d=1, p=verts, k=range(len(verts)))
    
def makeSphere(size=1.0,segments=13,**kwargs):
    ''' make a sphere shaped nurbs curve with a given size.'''
    wd=0.5*size
    vertsX = []
    vertsY = []
    vertsZ = []
    for x in range(segments):
        percent = float(x)/(segments-1)
        toRad = percent * math.pi * 2
        firstCoord = math.sin(toRad) * wd
        secCoord = math.cos(toRad) * wd
        vertsX.append((0,firstCoord,secCoord))
        vertsY.append((firstCoord,0,secCoord))
        vertsZ.append((firstCoord,secCoord,0))
        
    #add the axes together.
    #The little segment added in is needed to bridge where the second circle ends
    #to where the third circle begins.
    totalVerts = vertsX+vertsY+vertsX[:segments/3] + vertsZ
    
    return cmds.curve(d=1,p=totalVerts,k=range(len(totalVerts)))
        
def makeCircle(size=1.0,segments=13,**kwargs):
    ''' make a circle shaped nurbs curve with a given size and segments.'''
    wd=0.5*size
    verts = []
    for x in range(segments):
        percent = float(x)/(segments-1)
        toRad = percent * math.pi * 2
        firstCoord = math.sin(toRad) * wd
        secCoord = math.cos(toRad) * wd
        verts.append((0,firstCoord,secCoord))
    
    return cmds.curve(d=1,p=verts,k=range(len(verts)))
        
def makeSquare(size=1.0,**kwargs):
    '''make a square shaped nurbs curve with given size'''
    m=size*0.5
    nm=m*-1.0
    verts = ( [m,0,m],[nm,0,m],[nm,0,nm],[m,0,nm] )
    return cmds.curve(d=1, p=verts,k=range(len(verts)))

def makeLine(size=1.0,**kwargs):
    '''make a line shaped nurbs curve with given size as length. Defaults sticking out +Y'''
    verts=([0,0,0],[0,size,0])
    return cmds.curve(d=1, p=verts,k=range(len(verts)))

def makeSpoon(size=1.0,**kwargs):
    '''make a line with a circle on the end, length = size. Defaults to sticking out +Y'''
    spoonSizePct=0.1
    sw=size*spoonSizePct*0.5 #spoon width
    hl=size*(1-spoonSizePct) #handle length
    verts=([0,0,0],[0,hl,0],[sw,hl,0],[sw,hl+sw*2,0],[-sw,hl+sw*2,0],[-sw,hl,0],[0,hl,0])
    return cmds.curve(d=1, p=verts,k=range(len(verts)))

    
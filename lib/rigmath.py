'''Vector and Transform classes and math functions to make rigging easier.
Vector is a 3D vector with many methods for arithmetic, cross/dot products, length, etc.
It is set and get with lists, other vectors, or maya object names (the world translation
is used in that case.)

Transform is similar but represents a 16 element, 4x4 matrix. Methods that return or set
columns/rows of the matrix return Vectors where they can. Initializing with a maya object
uses the world matrix, or by default just an identity matrix.

Vectors and Transforms can be multiplied/added/subtracted with each other, where it 
makes sense.
'''
import maya.cmds as cmds
import math

def degToRad(deg):
    '''convert degree to radians'''
    return math.pi*deg/180.0

def radToDeg(rad):
    '''convert radians to degrees'''
    return 180.0*rad/math.pi
    
class Vector(object):
    '''3d vector helper class. 
    Initializes to origin unless given three float args. Can also be given
    a maya object and will initialize to the world transform
    '''
    def __init__(self,*args):
        object.__init__(self)
        if args:
            self.set(*args)
        else:
            self.zero()
            
    def __repr__(self):
        return 'Vector(%.3f,%.3f,%.3f)'%(self.x,self.y,self.z)
        
    def zero(self):
        '''set vector to zero'''
        self.x=0
        self.y=0
        self.z=0
    
    def set(self,*args):
        '''set vector. If one float arg, set all three axes to that value.
        If three float args, set to xyz. If a maya object use the world translate
        of that object.
        '''
        if len(args)==1:
            if hasattr(args[0], 'x') and hasattr(args[0],'y') and hasattr(args[0],'z'):
                self.setFromVector(args[0])
            elif hasattr(args[0], '_matrix'):
                self.setFromVector(args[0].getTranslation())
            elif hasattr(args[0],'__iter__'):
                self.setFromList(args[0])
            elif cmds.objExists(args[0]):
                self.setFromObj(args[0])
            elif isinstance(args[0], (int, long, float)):
                self.setFromScalar(args[0])
            else:
                raise RuntimeError("Could not create vector from args: %s" % args)
        elif len(args)==3:
            self.setFromList(args)
            
    def copy(self):
        '''return a copy of the current vector'''
        return Vector(self.x,self.y,self.z)
        
    def setFromScalar(self,scalar):
        self.x=float(scalar)
        self.y=float(scalar)
        self.z=float(scalar)
        
    def setFromList(self,other):
        '''set from a list'''
        self.x=float(other[0])
        self.y=float(other[1])
        self.z=float(other[2])
        
    def setFromVector(self,other):
        '''set this vector from another vector'''
        self.x=other.x
        self.y=other.y
        self.z=other.z
        
    def setFromObj(self,obj):
        '''set vector to a maya object's world space transform'''
        self.x,self.y,self.z = cmds.xform(obj,ws=True,q=True,t=True)
    
    def get(self):
        '''return list of this vector's xyz coords'''
        return [self.x,self.y,self.z]
    
    def __add__(self,other):
        newV = Vector()
        newV.setFromList([self.x + other.x,self.y + other.y,self.z + other.z])
        return newV
    
    def __sub__(self,other):
        newV = Vector()
        newV.setFromList([self.x - other.x, self.y - other.y, self.z - other.z])
        return newV
    
    def __mul__(self,other):
        newV=Vector()
        if isinstance(other,Vector):
            newV.setFromVector(self.x * other.x, self.y * other.y, self.z * other.z)
        elif isinstance(other,Transform):
            a1,a2,a3 = self.get()
            b11,b12,b13,b14,b21,b22,b23,b24,b31,b32,b33,b34,b41,b42,b43,b44 = other.get()
            newV.setFromList(
                [
                b11*a1 + b21*a2 + b31*a3 + b41,
                b21*a1 + b22*a2 + b22*a3 + b42,
                b31*a2 + b32*a2 + b33*a3 + b43
                ]
            )
        else:
            newV.setFromList([self.x*other,self.y*other,self.z*other])
        return newV
        
    def __div__(self, other):
        newV = Vector()
        newV.setFromList([self.x / other.x, self.y / other.y, self.z / other.z])
        return newV
        
    def __len__(self):
        return 3
        
    def __gt__(self,other):
        return self.sqLength() > other
        
    def __lt__(self,other):
        return self.sqLength() < other
        
    def normalize(self):
        thisLength=self.length()
        self.x/=thisLength
        self.y/=thisLength
        self.z/=thisLength
        
    def length(self):
        '''return vector length'''
        return math.sqrt(self.sqLength())
        
    def sqLength(self):
        '''return vector length squared'''
        return self.dot(self)
        
    def dot(self,other):
        '''return dot product of this vector and another'''
        return self.x*other.x+self.y*other.y+self.z*other.z
        
    def cross(self,other):
        '''return cross product of this vector and another as a Vector'''
        return Vector(self.y*other.z-self.z*other.y , 
            self.z*other.x-self.x*other.z , 
            self.x*other.y-self.y*other.x)
    
    def invert(self):
        '''invert the current vector in place'''
        self.x *= -1
        self.y *= -1
        self.z *= -1
        
    def reflect(self,plane=None):
        '''reflect the current vector along the plane formed by another. If none given the
        yz plane is used (-1,0,0)'''
        thisV = self.copy()
        if not plane:
            plane=Vector(-1,0,0)
        else:
            plane=Vector(plane)
        dot=thisV.dot(plane)
        self.setFromVector(thisV-plane*2*dot)
        
class Transform(object):
    '''4x4 object transform class'''
    def __init__(self,*args):
        object.__init__(self)
        self.identity()
        if args:
            self.set(*args)
            
    def __repr__(self):
        return '''Transform(%.3f,%.3f,%.3f,%.3f,
        %.3f,%.3f,%.3f,%.3f,
        %.3f,%.3f,%.3f,%.3f,
        %.3f,%.3f,%.3f,%.3f)''' % (
        self._matrix[0],self._matrix[1],self._matrix[2],self._matrix[3],
        self._matrix[4],self._matrix[5],self._matrix[6],self._matrix[7],
        self._matrix[8],self._matrix[9],self._matrix[10],self._matrix[11],
        self._matrix[12],self._matrix[13],self._matrix[14],self._matrix[15],
        )
        
    def copy(self):
        '''return a copy of this transform as a new Transform'''
        return Transform(self.get())
        
    def zero(self):
        '''set to all zero'''
        self._matrix = [0]*16
        
    def identity(self):
        '''set to identity'''
        self._matrix = [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
        
    def get(self):
        return self._matrix[:]
        
    def set(self,*args):
        '''set the matrix to the given list, transform, vector (translation). If no
        args matrix is set to identity
        '''
        if args:
            if len(args) == 1:
                if hasattr(args[0], 'x') and hasattr(args[0],'y') and hasattr(args[0],'z'):
                    self.setTranslation(args[0])
                elif hasattr(args[0], 'get') and len(args[0].get()) == 16:
                    self.setFromList(args[0].get())
                elif hasattr(args[0],'__iter__'):
                    self.setFromList(args[0])
                elif cmds.objExists(args[0]):
                    self.setFromObj(args[0])
                else:
                    raise RuntimeError("can't find '%s' in scene to make matrix"%args[0])
            elif len(args) == 16:
                self.setFromList(args)
            else:
                raise RuntimeError("can't init matrix from args: %s" % str(args))
        else:
            self.identity()
            
    def __len__(self):
        return 16
            
    def setFromObj(self,obj):
        self._matrix=cmds.xform(obj,ws=True,m=True,q=True)
        
    def setFromList(self,other):
        '''set matrix from a 16 element list'''
        if not len(other)==16:
            raise TypeError("matrix must be set from 16 element list")
        self._matrix=list(other[:])
        
    def xAxis(self):
        '''return the xAxis of the Transform as a Vector'''
        return Vector(self._matrix[0],self._matrix[1],self._matrix[2])
    
    def yAxis(self):
        '''return the yAxis of the Transform as a Vector'''
        return Vector(self._matrix[4],self._matrix[5],self._matrix[6])

    def zAxis(self):
        '''return the zAxis of the Transform as a Vector'''
        return Vector(self._matrix[8],self._matrix[9],self._matrix[10])
        
    def getTranslation(self):
        '''get translation as a Vector'''
        return Vector(self._matrix[12],self._matrix[13],self._matrix[14])
        
    def setTranslation(self,other):
        '''set translation from another object'''
        other = Vector(other)
        self._matrix[12]=other.x
        self._matrix[13]=other.y
        self._matrix[14]=other.z
        
    def translate(self,*args):
        '''move the translation based on the translation of another object, Vector or 
        Transform'''
        other = Vector(*args)
        self._matrix[12]+=other.x
        self._matrix[13]+=other.y
        self._matrix[14]+=other.z
        
    def scale(self, *args):
        '''scale the transform by the given amount, or by the given xyz if three args given'''
        other = Vector(*args)
        self._matrix[0]*=other.x
        self._matrix[5]*=other.y
        self._matrix[10]*=other.z
        
    def __add__(self,other):
        '''add this matrix to another, or to a vector (to translate)'''
        try:
            if len(other)==3: #matrix and vector
                self.translate(other)
            elif len(other)==16: #matrix and matrix
                return Transform(map((lambda x,y: x+y),self.get(),other.get()))
        #matrix and float
        except TypeError:
            return Transform(map((lambda x,y: x+y),self.get(),[float(other)]*16))
        
    def __sub__(self,other):
        '''subtract this matrix from another, or subtract a vector (from translate)'''
        try:
            if len(other)==3: #matrix and vector
                self.translate(other*-1)
            elif len(other)==16: #matrix and matrix
                return Transform(map((lambda x,y: x-y),self.get(),other.get()))
        except TypeError: # matrix and float
            return Transform(map((lambda x,y: x-y),self.get(),[float(other)]*16))     
            
    def __mul__(self,other):
        '''multiply this matrix by another matrix or vector'''
        if isinstance(other,Transform):
            a11,a12,a13,a14,a21,a22,a23,a24,a31,a32,a33,a34,a41,a42,a43,a44 = self.get()
            b11,b12,b13,b14,b21,b22,b23,b24,b31,b32,b33,b34,b41,b42,b43,b44 = other.get()
            m11=a11*b11 + a12*b21 + a13*b31 + a14*b41
            m12=a11*b12 + a12*b22 + a13*b32 + a14*b42
            m13=a11*b13 + a12*b23 + a13*b33 + a14*b43
            m14=a11*b14 + a12*b24 + a13*b34 + a14*b44
            m21=a21*b11 + a22*b21 + a23*b31 + a24*b41
            m22=a21*b12 + a22*b22 + a23*b32 + a24*b42
            m23=a21*b13 + a22*b23 + a23*b33 + a24*b43
            m24=a21*b14 + a22*b24 + a23*b34 + a24*b44
            m31=a31*b11 + a32*b21 + a33*b31 + a34*b41
            m32=a31*b12 + a32*b22 + a33*b32 + a34*b42
            m33=a31*b13 + a32*b23 + a33*b33 + a34*b43
            m34=a31*b14 + a32*b24 + a33*b34 + a34*b44
            m41=a41*b11 + a42*b21 + a43*b31 + a44*b41
            m42=a41*b12 + a42*b22 + a43*b32 + a44*b42
            m43=a41*b13 + a42*b23 + a43*b33 + a44*b43
            m44=a41*b14 + a42*b24 + a43*b34 + a44*b44
            return Transform(m11,m12,m13,m14,m21,m22,m23,m24,m31,m32,m33,m34,m41,m42,m43,m44)
        elif isinstance(other,Vector):
            a11,a12,a13,a14,a21,a22,a23,a24,a31,a32,a33,a34,a41,a42,a43,a44 = self.get()
            b1,b2,b3 = other.get()
            return Transform(a11*b1,a12*b2,a13*b3,a14,a21*b1,a22*b2,a23*b3,a24,
                a31*b1,a32*b2,a33*b3,a34,a41,a42,a43,a44)
        else:
            raise TypeError("unsupported operand type(s) for *: '%s' and '%s'" %(self.__class__.__name__ ,other.__class__.__name__))
            
    def reflect(self,plane=None):
        '''reflect the transform about a plane specified as a Vector. If none given the yz
        plane is used.'''
        xa=self.xAxis()
        xa.reflect(plane=plane)
        ya=self.yAxis()
        ya.reflect(plane=plane)
        za=self.zAxis()
        za.reflect(plane=plane)
        ta=self.getTranslation()
        ta.reflect(plane=plane)
        self.set(xa.x,xa.y,xa.z,0,ya.x,ya.y,ya.z,0,za.x,za.y,za.z,0,ta.x,ta.y,ta.z,1)
        
    def det(self):
        '''return the determinate of the matrix'''
        a11,a12,a13,a14,a21,a22,a23,a24,a31,a32,a33,a34,a41,a42,a43,a44 = self.get()
        return (
            a11*a22*a33*a44 + a11*a23*a34*a42 + a11*a24*a32*a43 +
            a12*a21*a34*a43 + a12*a23*a31*a44 + a12*a24*a33*a41 +
            a13*a21*a32*a44 + a13*a22*a34*a41 + a13*a24*a31*a42 +
            a14*a21*a33*a42 + a14*a22*a31*a43 + a14*a23*a32*a41 -
            a11*a22*a34*a43 - a11*a23*a32*a44 - a11*a24*a33*a42 -
            a12*a21*a33*a44 - a12*a23*a34*a41 - a12*a24*a31*a43 -
            a13*a21*a34*a42 - a13*a22*a31*a44 - a13*a24*a32*a41 -
            a14*a21*a32*a43 - a14*a22*a33*a41 - a14*a23*a31*a42
            )
            
    def transpose(self):
        '''transpose the current matrix in place'''
        a11,a12,a13,a14,a21,a22,a23,a24,a31,a32,a33,a34,a41,a42,a43,a44 = self.get()
        self.set(a11,a21,a31,a41,a12,a22,a32,a42,a13,a23,a33,a43,a14,a24,a34,a44)
        
    def invert(self):
        '''invert the current matrix in place.'''
        inv = [0]*16
        a = self._matrix[:]
        inv[0] = a[5]*a[10]*a[15] - a[5]*a[11]*a[14] - a[9]*a[6]*a[15] + \
                 a[9]*a[7]*a[14] + a[13]*a[6]*a[11] - a[13]*a[7]*a[10]
        inv[4] = -a[4]*a[10]*a[15] + a[4]*a[11]*a[14] + a[8]*a[6]*a[15] - \
                  a[8]*a[7]*a[14] - a[12]*a[6]*a[11] + a[12]*a[7]*a[10]
        inv[8] = a[4]*a[9]*a[15] - a[4]*a[11]*a[13] - a[8]*a[5]*a[15] + \
                 a[8]*a[7]*a[13] + a[12]*a[5]*a[11] - a[12]*a[7]*a[9]
        inv[12] = -a[4]*a[9]*a[14] + a[4]*a[10]*a[13] + a[8]*a[5]*a[14] - \
                   a[8]*a[6]*a[13] - a[12]*a[5]*a[10] + a[12]*a[6]*a[9]
        inv[1] = -a[1]*a[10]*a[15] + a[1]*a[11]*a[14] + a[9]*a[2]*a[15] - \
                  a[9]*a[3]*a[14] - a[13]*a[2]*a[11] + a[13]*a[3]*a[10]
        inv[5] = a[0]*a[10]*a[15] - a[0]*a[11]*a[14] - a[8]*a[2]*a[15] + \
                 a[8]*a[3]*a[14] + a[12]*a[2]*a[11] - a[12]*a[3]*a[10]
        inv[9] = -a[0]*a[9]*a[15] + a[0]*a[11]*a[13] + a[8]*a[1]*a[15] - \
                  a[8]*a[3]*a[13] - a[12]*a[1]*a[11] + a[12]*a[3]*a[9]
        inv[13] = a[0]*a[9]*a[14] - a[0]*a[10]*a[13] - a[8]*a[1]*a[14] + \
                  a[8]*a[2]*a[13] + a[12]*a[1]*a[10] - a[12]*a[2]*a[9]
        inv[2] = a[1]*a[6]*a[15] - a[1]*a[7]*a[14] - a[5]*a[2]*a[15] + \
                 a[5]*a[3]*a[14] + a[13]*a[2]*a[7] - a[13]*a[3]*a[6]
        inv[6] = -a[0]*a[6]*a[15] + a[0]*a[7]*a[14] + a[4]*a[2]*a[15] - \
                  a[4]*a[3]*a[14] - a[12]*a[2]*a[7] + a[12]*a[3]*a[6]
        inv[10] = a[0]*a[5]*a[15] - a[0]*a[7]*a[13] - a[4]*a[1]*a[15] + \
                  a[4]*a[3]*a[13] + a[12]*a[1]*a[7] - a[12]*a[3]*a[5]
        inv[14] = -a[0]*a[5]*a[14] + a[0]*a[6]*a[13] + a[4]*a[1]*a[14] - \
                   a[4]*a[2]*a[13] - a[12]*a[1]*a[6] + a[12]*a[2]*a[5]
        inv[3] = -a[1]*a[6]*a[11] + a[1]*a[7]*a[10] + a[5]*a[2]*a[11] - \
                  a[5]*a[3]*a[10] - a[9]*a[2]*a[7] + a[9]*a[3]*a[6]
        inv[7] = a[0]*a[6]*a[11] - a[0]*a[7]*a[10] - a[4]*a[2]*a[11] + \
                 a[4]*a[3]*a[10] + a[8]*a[2]*a[7] - a[8]*a[3]*a[6]
        inv[11] = -a[0]*a[5]*a[11] + a[0]*a[7]*a[9] + a[4]*a[1]*a[11] - \
                   a[4]*a[3]*a[9] - a[8]*a[1]*a[7] + a[8]*a[3]*a[5]
        inv[15] = a[0]*a[5]*a[10] - a[0]*a[6]*a[9] - a[4]*a[1]*a[10] + \
                  a[4]*a[2]*a[9] + a[8]*a[1]*a[6] - a[8]*a[2]*a[5]

        det = a[0]*inv[0] + a[1]*inv[4] + a[2]*inv[8] + a[3]*inv[12];
        if (det == 0):
            raise ZeroDivisionError("matrix is not invertable")
        det = 1.0 / det
        self._matrix=[x * det for x in inv]
        
    def setFromAxisAngle(self,axis,angle):
        '''given an axis Vector and angle in radians, set matrix to rotation'''
        axisVector = Vector(axis)
        axisVector.normalize()
        x,y,z=axisVector.x,axisVector.y,axisVector.z
        sa=math.sin(-angle)
        ca=math.cos(-angle)
        xx=x*x
        yy=y*y
        zz=z*z
        xy=x*y
        xz=x*z
        yz=y*z
        a11,a12,a13,a14,a21,a22,a23,a24,a31,a32,a33,a34,a41,a42,a43,a44 = self.get()
        
        a11=xx+ca*(1.0-xx)
        a12=xy-ca*xy+sa*z
        a13=xz-ca*xz-sa*y
        a14=0.0
        a21=xy-ca*xy-sa*z
        a22=yy+ca*(1.0-yy)
        a23=yz-ca*yz+sa*x
        a24=0.0
        a31=xz-ca*xz+sa*y
        a32=yz-ca*yz-sa*x
        a33=zz+ca*(1.0-zz)
        a34=0.0
        a41=0.0
        a42=0.0
        a43=0.0
        a44=1.0      
        self.set(a11,a21,a31,a41,a12,a22,a32,a42,a13,a23,a33,a43,a14,a24,a34,a44)         

    def setFromXYZ(self,x,y,z):
        '''set the rotation by the given XYZ angles in degrees,
        in xyz order
        '''
        x=degToRad(-x)
        y=degToRad(-y)
        z=degToRad(-z)
        cx=math.cos(x)
        cy=math.cos(y)
        cz=math.cos(z)
        sx=math.sin(x)
        sy=math.sin(y)
        sz=math.sin(z)
        a11,a12,a13,a14,a21,a22,a23,a24,a31,a32,a33,a34,a41,a42,a43,a44 = self.get()

        a11=cz*cy
        a12=sz*cx + cz*sy*sx
        a13=sz*sx - cz*sy*cx	
        a21=-sz*cy
        a22=cz*cx - sz*sy*sx	
        a23=cz*sx + sz*sy*cx 
        a31=sy	
        a32=-cy*sx
        a33=cy*cx  
        self.set(a11,a21,a31,a41,a12,a22,a32,a42,a13,a23,a33,a43,a14,a24,a34,a44)  

    def alignToWorld(self):
        '''UNTESTED. Applies the smallest rotation that will make transform axes parallel to world axes'''
        xa=self.xAxis()
        ya=self.yAxis()
        za=self.zAxis()

        xa.normalize()
        ya.normalize()
        za.normalize()

        wx=Vector(1,0,0)
        wy=Vector(0,1,0)
        wz=Vector(0,0,1)
        xAngle,yAngle,zAngle=(0,0,0)

        for axis in (wx,wy,wz):
            dot = xa.dot(axis)
            if abs(dot) > abs(xAngle):
                xAngle = dot
            dot = ya.dot(axis)
            if abs(dot) > abs(yAngle):
                yAngle = dot
            dot = za.dot(axis)
            if abs(dot) > abs(zAngle):
                zAngle = dot

        xAngle = math.acos(xAngle)
        yAngle = math.acos(yAngle)
        zAngle = math.acos(zAngle)
        self.setFromXYZ(radToDeg(xAngle),radToDeg(yAngle),radToDeg(zAngle))
            

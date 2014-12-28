#! /usr/bin/env python2.6

# Where we are at : building a function for multiplying and adding vectors

""" v_2 is a complete rewrite. Everything operates within the tree() loop. 
All the points are stored in Points.points{}, and the attributes of each point instance is stored as an object attribute.
With each step, the tree loop cycles through all the points, and tests each point. 
If test is positive, then the point class is called with the calling point as an argument, 
and a new point is created, set, and added to the database."""

""" v_3 is a rewrite, to change from multiple Classes to one class, 
and to change data storage from a dictionary of objects to an array of arrays.

1. Instantiating Point will call the init function that will create a root point and store it as a list within a list. 
The index will be the id
"""

#! /usr/bin/env python2.6
import  math 
import random
import numpy as np
import treeMath as tm
import cPickle as pickle
import shelve
import thread

def vmult(a,b):
    d = locals()

def fit(value=.33,inMin=0.0,inMax=1.0,outMin=0.0,outMax=100.0):
    rat = 1.0  
    rat /= (inMax-inMin)
    valueRatio = (value - inMin)*rat
    output = (valueRatio *(outMax -outMin))+outMin
    return output

#============================CONTROL CLASS ===========================
#=====================================================================

class Control(object):
    """ reads parameters from a file and stores parameters used to drive the tree creation program"""
   
    def __init__(self,filename = "control.txt"):
        """d = locals()
        e = len(d)
        if e != 2:
            raise ValueError("requires string object of path to control file")
        print e
        print d.values()"""
        self.parms = []
        with open(filename) as file:
            data = file.readlines()
            count = 0
            for line in data:
                if count == 7:
                    break
                val = line.split()
                tmp = val[2]
                self.parms.append(tmp)
                count += 1
        self.__class__.seed = float(self.parms[0])
        self.__class__.stepNum = int(self.parms[1])
        self.__class__.stepSize = float(self.parms[2])
        self.__class__.stepRange = float(self.parms[3])
        self.__class__.jitAngleRange = float(self.parms[4])
        self.__class__.branchAngle = float(self.parms[5])
        self.__class__.branchAngleRange = float(self.parms[6])
        self.__class__.maxPoints = int(self.parms[7])

    def status(self):
        list =  "seed = "+str(self.__class__.seed)+"\n"\
                "stepNum = "+str(self.__class__.stepNum)+"\n"\
                "stepSize = "+str(self.__class__.stepSize)+"\n"\
                "stepRange = "+str(self.__class__.stepRange)+"\n"\
                "jitAngleRange = "+str(self.__class__.jitAngleRange)+"\n"\
                "branchAngle = "+str(self.__class__.branchAngle)+"\n"\
                "branchAngleRange = "+str(self.__class__.branchAngleRange)+"\n"\
                "maxPoints = "+str(self.__class__.maxPoints)+"\n"
        print list
            
#----------------------------END CONTROL CLASS ---------------------------
#-------------------------------------------------------------------------
        
#+++++++++++++++++++++++++++++++Main Class++++++++++++++++++++++++++++++++++++
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++        
class Tree(object):
    """ creates and maintains point objects and attributes.
        the init method creates the variables, the setPoint changes their value"""

    def __init__(self):   
        """ 
        1. calls the attribute function to return a list of values
        2. adds that list as an element of an array to allPoints.
            The id is the index of the item
        3. Sets the global TOTAL attribute to 0

        """
        self.TOTAL = 0
        self.currentStep = 0
        self.allPoints = []
        bundle = self.attributes()
        self.allPoints.append(bundle) # this attaches the root point, as represented by the bundle list of attributes
        self.attList = {"id" : 0,"pos" : 1,"line" : 2, "parentId" : 3, "parentPos" : 4,"parentLine" : 5,\
               "angle" : 6 ,"dir" : 7, "walk" : 8, "birthStep" : 9, "alive" : 10 , "split" : 11,\
               "parentDir" : 12}          
#-----------------------Global Attributes to conform to bgeo formatting code--------------------------------
        self.PointAttributes = {}
        self.PrimitiveAttributes = {}
        self.VertexAttributes = {}
        self.GlobalAttributes = {}
        self.VertexMap = []
        self.Primitives = []
        self.Info = None
#------------------------------------------ATTRIBUTE HANDLING--------------------------------------------
    def floatAtt(self, name):
        first = []
        self.define = {}
        self.define["scope"] = "public"
        self.define["storage"] = "fpreal32"
        self.define["name"] = name
        local_options = {}
        self.define["options"] ={}
  
    def addPoint(self,parent = 0):
        """ this function:
        1. increments the index, 
        2. gets a bundle of attributes,
        3. and assigns it to an array. 
        4. It records the calling point as attribute parentId.
        5. It also returns the index of the new element as 'thisId' """        
        self.TOTAL += 1
        bundle = self.attributes()
        thisId = self.TOTAL
        self.allPoints.append(bundle) 
        # set inherited attributes
        self.setAttr(thisId,"parentId",parent)
        return thisId
        
        #print bundle
        
    def setAttr(self, point, attName, value):
        index = int(self.attList[attName])
        self.allPoints[point][index] = value 
        
    def getAttr(self, point, attName):
        index = int(self.attList.get(attName,100))
        tmp = self.allPoints[point][index] 
        return tmp
        
    def attributes(self):
        pid = self.TOTAL
        pos = (0.0,0.0,0.0)
        line = 0
        parentId = 0
        parentPos = (0.0,0.0,0.0)
        parentLine = 0
        angle = 30.0
        dirv = (0,1.0,0)
        walk = 0.0
        birthStep = 0
        alive = 1
        split = 2
        parentDir = (0.0,1.0,0.0)
        bundle = [pid,pos,line,parentId,parentPos,parentLine,angle,dirv,walk,birthStep,alive,split,parentDir]
        return bundle
        
    def makeTree(self):
        """
        1. Calls the Control function to read global control values from a file
        2. Starts a loop limited by number of steps allowed. (steps equal length of longest line)
            3. this loop first gets the current number of existing points
            4. It loops over this entire range
                5. It grabs a point and pulls out the split attribute value [0-x]
                    6. It starts a range loop over value of split
                        7. Each iteration, it adds a point
                        8. Then gets the id
                        9. Then resets the attributes to new values
        10. For testing only, it then loops through all points a prints some values       
        """
        Control("control.txt")
        parentId = 0 
        while (self.currentStep < Control.stepNum):
            allP = len(self.allPoints) 
            print "number of points = " + str(allP)
            
            for p in range(allP):   
                    thisPoint = self.allPoints[p]
                    localSplit = self.getAttr(p, "split")
                    for d in range(localSplit):
                        self.addPoint(p)  #adds a point with parent point in argument
                        thisId = self.TOTAL
                        self.setPoint(thisId)
                    self.setAttr(p, "split", 0)
                    
            self.currentStep += 1
        #return self.allPoints
            
    def printTree(self):    
        plist = self.allPoints
        v = []
        for p in plist:
            x = p[0]
            v.append(x)
        print v
        print len(plist)
                                  
    def makeStep(self,dir=(0.0,1.0,0),seed = 1.2):  #this works but needs to return a position vector
        """called with the parentDir as the first argument and id as the second, returns a position dir """
        dist = Control.stepSize
        var = Control.stepRange * .5
        random.seed(Control.seed+seed)
        wander = random.random()
        steplength = fit(wander,0,1,dist-var,dist+var)
        dvec = self.dirVec(dir,seed)
        #newStep = tm.vecMult(dvec, steplength)
        newStep = dvec  #remove when math library added*********************************************************
        ##addWalk goes here        
        return newStep
        
    def setPoint(self,thisId=1):
        """retrieve Point objects. Requires control attributes"""
        localPoint = self.allPoints[thisId]
        parentId = localPoint[3]
        localParent = self.allPoints[parentId]
        #inheritable attributes
        parentPos = self.getAttr(parentId,"pos")
        parentDir = self.getAttr(parentId,"dir")
        angle = self.getAttr(parentId,"angle")
        self.setAttr(thisId,"parentPos",parentPos)
        self.setAttr(thisId, "parentDir",parentDir)
        self.setAttr(thisId, "angle",angle)
        step = self.makeStep(parentDir, parentId)
        position = tm.vecAdd(step,parentPos)
        tmpVec = tm.vecSub(parentPos,position)
        self.setAttr(thisId,"dir",tmpVec)
           
    
    def __str__(self):
        rep = "id "+str(self.pid)+"\n"\
              "pos = " + str(self.pos)+"\n"\
              "line = " +str(self.line)+"\n"\
              "parentId = " +str(self.parentId)+"\n"\
              "parentPos = " +str(self.parentPos)+"\n"\
              "parentLine = " +str(self.parentLine)+"\n"\
              "angle = " +str(self.angle)+"\n"\
              "dir = " + str(self.dir)+"\n"\
              "walk = " +str(self.walk)+"\n"\
              "birthStep = " + str(self.birthStep)
        return rep
    
    def randVec(self,seed = 1.3):
        """TESTED  requires loading random module, returns normalized vector. TESTED """
        thisSeed = seed * self.TOTAL
        random.seed(thisSeed)
        a = random.random()-.5
        b = random.random()-.5
        c = random.random()-.5
        outVec = (a,b,c)
        newVec = tm.vecNorm(outVec)
        return newVec

    def dirVec(self,parentDir=(0.0,1.0,0.0),parentId=0,upVec = (0.0,1.0)):
        """calls parentVec, randomVec, and blends them using angleJitter. The makeStep functions multiplies this by steplength to return product"""
        randir = self.randVec(parentId)
        #pdir = tm.vecNorm(parentDir)
        pdir = parentDir#remove when math library added*********************************************************
        mix = Control.jitAngleRange
        #newVec = tm.vecBlend(pdir, randir, mix)
        newVec = randir  #remove when math library added*********************************************************
        return newVec

#------------------------------------WRITE OUT ---------------------------------------

    def saveFile(self, filename):
        """writes out pickled data. Data is the self.allPoints attribute of the Tree instance."""
        myData = self.allPoints
        header = self.attList
        dataOut = [header, myData]
        output = open(filename,"wb")
        pickle.dump(dataOut, output)
        output.close()
    
    
#------------------------Utility Functions ------------------------

#main

tree = Tree()
#myData = tree.makeTree()
tree.makeTree()
tree.saveFile("saveData.p")

#output = open("saveData.p","wb")

#output.close()

loadFile = pickle.load(open("saveData.p","rb"))
print loadFile[0]
print loadFile[1]
pp = Control("control.txt")
print pp.parms



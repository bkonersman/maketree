import math, random

def clamp01(num):
    newNum = num - math.floor(num)
    return newNum

def getRand(seed):
    """returns number from 0 to 1"""
    random.seed(seed)
    x = random.random()
    return x

def vecSub(subThisVec,fromThisVec):
    """the first vector gets subtracted from the second vector"""
    ax = subThisVec[0]
    ay = subThisVec[1]
    az = subThisVec[2]
    bx = fromThisVec[0]
    by = fromThisVec[1]
    bz = fromThisVec[2]
    newVec = (bx - ax, by - ay, bz - az)
    return newVec

def vecNorm(inVec):
    """ TESTED returns a normalized vector """
    a = inVec[0]
    b = inVec[1]
    c = inVec[2]
    v = math.sqrt((a*a)+(b*b)+(c*c))
    a = a/v
    b = b/v
    c = c/v
    vec = (a,b,c)
    return vec

def vecAdd(aVec,bVec):
    ax = aVec[0]
    ay = aVec[1]
    az = aVec[2]
    bx = bVec[0]
    by = bVec[1]
    bz = bVec[2]
    newVec = ((ax+bx),(ay+by),(az+bz))
    return newVec

def vecBlend(aVec,bVec,bias):
    bias = clamp01(bias)
    ax = aVec[0]
    ay = aVec[1]
    az = aVec[2]
    bx = bVec[0]
    by = bVec[1]
    bz = bVec[2]
    biasB = 1-bias
    newVec = ((ax*bias + bx *biasB),(ay*bias + by *biasB),(az*bias + bz *biasB))
    return newVec

def vecMult(aVec,mult):
    ax = aVec[0]
    ay = aVec[1]
    az = aVec[2]
    newVec = (ax * mult, ay * mult, az * mult)
    return newVec

def vecLength(vec):
    a = vec[0]
    b = vec[1]
    c = vec[2]
    length = math.sqrt((a*a)+(b*b)+(c*c))
    return length
    

if __name__=="__main__":
    print "You ran this module directly instead of importing it"

'''
    Module to interpret the schema of Houdini's JSON geometry format.
'''

import os, sys, time
import numpy

VERBOSE = False
_START = time.time()
_LAP = _START

_VERSION = '12.0.0'

def _Assert(condition, message):
    ''' Print out verbose information about processing '''
    if not condition:
        print message
        sys.exit(1)

def _Verbose(msg):
    ''' Print out verbose information about processing '''
    if VERBOSE:
        global _LAP
        now = time.time()
        sys.stdout.write('+++ %6.3f (%6.3f): %s\n' % (now-_START, now-_LAP, msg))
        _LAP = now
        sys.stdout.flush()

try:
    import json  #was hjson
except:
    # If there's an issue loading hjson, fall back to simplejson.  This doesn't
    # support binary JSON but works for ASCII files.
    _Verbose('Falling back to simplejson')
    import json  #was simplejson
    json = json  #hjson = simplejson

def listToDict(L):
    # Since JSON doesn't enforce order for dictionary objects, the geometry
    # schema often stores dictionaries as lists of name/value pairs.  This
    # function will throw the list into a dictionary for easier access.
    if L and type(L) == list:
        d = {}
        for i in xrange(0, len(L), 2):
            d[L[i]] = L[i+1]
        return d
    return L

def _rawPageDataToTupleArray(raw, packing, pagesize, constflags, total_tuples):
    ''' Marshall raw page data into an array of tuples '''
    # Raw page data is stored interleaved as:
    # [ <subvector0_page0> <subvector1_page0> <subvector2_page0>
    #   <subvector0_page1> <subvector1_page1> <subvector2_page1>
    #   <subvector0_page2> <subvector1_page2> <subvector2_page2>
    #  ...
    #   <subvector0_pageN> <subvector1_pageN> <subvector2_pageN>]
    #
    # <subvectorI_PageJ> will be a single subvector value if constflags[i][j]
    # is True.
    import operator
    tuple_size = sum(packing)
    n_pages = 0
    # We can extract the number of pages from the length of a constant flag
    # table if any subvectors have one.
    if constflags is not None:
        n_pages = reduce(lambda x,y: x if x > 0 else len(y), constflags, 0)
    # Failing that, we know that raw contains no constant pages, and so we
    # can compute the number of pages directly from the length of raw.
    if n_pages == 0:
        full_pagesize = tuple_size * pagesize
        n_pages = (len(raw) + full_pagesize - 1) // full_pagesize

    # Build list of the subvector index and offset into that subvector for
    # each tuple component.
    tuple_pack_info = []
    for i in xrange(0, len(packing)):
        tuple_pack_info.extend([(i, j) for j in xrange(0, packing[i])])

    # Precompute the increments for pages where all subvectors are varying
    # as these don't change.
    varying_steps = [1] * len(packing)
    varying_steps = map(operator.mul, packing, varying_steps)

    result = []
    raw_index = 0
    raw_left = len(raw)
    # Iterate over the input pages
    for i in xrange(0, n_pages):
        # Compute the packed vector steps, i.e., the step to take in raw to
        # move to the start of the next packed subvector.  This will be 0
        # for constant pages.
        if constflags is not None:
            pv_steps = [0 if (len(x) > 0 and x[i]) else 1 for x in constflags]
            pv_steps = map(operator.mul, packing, pv_steps)
        else:
            pv_steps = varying_steps
        # Compute the number of varying components on this page using the
        # already computed vec_increments.
        n_varying = sum(pv_steps)
        # Use the number of varying components and the amount of data left
        # to compute the number of tuples this page represents.  When the
        # last page is constant for all the subvectors, i.e., there are no
        # varying components, we load a single tuple in this iteration and
        # later duplicate it to create the remaining tuples.
        if n_varying > 0:
            n_tuples = min(pagesize, (raw_left - (tuple_size - n_varying)) // n_varying)
        else:
            _Assert( raw_left >= tuple_size, "Expected more data" )
            n_tuples = pagesize if raw_left > tuple_size else 1

        # Compute the list of offsets into raw for the start of each packed
        # subvector.
        curr_offset = raw_index
        pv_offsets = []
        for i, step in enumerate(pv_steps):
            pv_offsets.append(curr_offset)
            curr_offset += max(step * n_tuples, packing[i])
            
        # Finally, extract each tuple on the page from the raw list.
        if tuple_size > 1:
            for j in xrange(0, n_tuples):
                result.append([raw[pv_offsets[x]+y] for x,y in tuple_pack_info])
                pv_offsets = map(operator.add, pv_offsets, pv_steps)
        else:
            for j in xrange(0, n_tuples):
                result.append(raw[pv_offsets[0]])
                pv_offsets = map(operator.add, pv_offsets, pv_steps)

        consumed = n_varying * n_tuples + (tuple_size - n_varying)
        raw_index += consumed
        raw_left -= consumed
        _Assert( raw_index == curr_offset, "Indexing bug" )

    # The loop above marshalls all the available data in raw into our result,
    # but without explicitly using the total_tuples argument, we had no way
    # of computing the size of the last page if it was constant for all the
    # subvectors.  In such a case, we treated it as if it contained a single
    # tuple, and so we now add any missing tuples.
    if constflags is not None and result:
        copy_source = result[-1]
        if tuple_size > 1:
            for i in xrange(len(result), total_tuples):
                result.append(list(copy_source))
        else:
            for i in xrange(len(result), total_tuples):
                result.append(copy_source)
            
    _Assert( len(result) == total_tuples, "Expected more data" )
    return result

class Basis:
    ''' Simple basis definition '''
    def __init__(self, btype='NURBS', order=2,
                    endinterpolation=True, knots=[0,0,1,1]):
        self.Type = btype
        self.Order = order
        self.EndInterpolation = endinterpolation
        self.Knots = knots

    def load(self, bdata):
        bdata = listToDict(bdata)
        self.Type = bdata.get('type', self.Type)
        self.Order = bdata.get('order', self.Order)
        self.EndInterpolation = bdata.get('endinterpolation', self.EndInterpolation)
        self.Knots = bdata.get('knots', self.Knots)

    def save(self):
        return [
            "type", self.Type,
            "order", self.Order,
            "endinterpolation", self.EndInterpolation,
            "knots", self.Knots
        ]

class TrimRegion:
    ''' Class to define a trim region of a profile curve '''
    def __init__(self):
        ''' Create an empty trim region '''
        self.OpenCasual = False
        self.Faces = []

    def load(self, tdata):
        ''' Interpret the JSON schema to create a list of faces (with extents)
            which define a single trim region '''
        tdata = listToDict(tdata)
        self.OpenCasual = tdata["opencasual"]
        self.Faces = []
        for face in tdata["faces"]:
            fdata = listToDict(face)
            self.Faces.append({
                "face":fdata['face'],
                "u0"  :fdata['u0'],
                "u1"  :fdata['u1'],})

    def save(self):
        ''' Create an object reflecting the JSON schema for the trim region '''
        data = [ "opencasual", self.OpenCasual ]
        fdata = []
        for f in self.Faces:
            fdata.append([ "face", f["face"],
                            "u0", f["u0"],
                            "u1", f["u1"] ])
        data += [ "faces", fdata ]
        return data

#class Attribute:  saved separately
    

def _unpackRLE(rle):
    ''' Unpack a run-length encoded array of bit data (used to save groups) '''
    a = []
    for run in xrange(0, len(rle), 2):
        count = rle[run]
        state = [False,True][rle[run+1]]
        a += [state] * count
    return a

class ElementGroup:
    ''' There are different group types in GA.  ElementGroup's are used for
        groups of primitive, vertex and point objects.  They may be ordered or
        unordered
    '''
    def __init__(self, name):
        ''' Create a new element group of the given name '''
        self.Name = name
        self.Selection = []
        self.Order = None
        self.Defaults = None
        self.Count = 0

    def updateMembership(self):
        ''' Count the number of elements in the group '''
        self.Count = self.Selection.sum()

    def loadUnordered(self, obj):
        ''' Load an unordered group.  There are currently two encodings to
        store the bit-array.  The runlengh encoding is an array of pairs
        [count, value, count, value], while the "i8" encoding stores as 8-bit
        integers (binary mode) '''
        self.Selection = numpy.array([], dtype=bool)
        obj = listToDict(obj)
        rle = obj.get('boolRLE', None)
        if rle:
            self.Selection = numpy.array(_unpackRLE(rle), dtype=bool)
            return
        i8 = obj.get('i8', None)
        if i8:
            self.Selection = numpy.array(i8, dtype=bool)
            return
        _Assert(False, 'Unknown element group encoding')

    def loadOrdered(self, obj, element_count):
        ''' Ordered groups are stored as a list of the elements in the group
        (in order) '''
        self.Order = obj
        self.Selection = numpy.resize(numpy.array([False], dtype=bool),
                                    element_count)
        for i in obj:
            self.Selection[i] = True

    def loadSelection(self, obj, element_count):
        ''' Interpret the schema, loading the group selection '''
        obj = listToDict(obj)
        sel = listToDict(obj['selection'])
        self.Defaults = sel['defaults']
        style = sel.get('unordered', None)
        if style:
            self.loadUnordered(style)
        else:
            self.loadOrdered(sel['ordered'], element_count)
        self.updateMembership()
    def save(self, gtype):
        ''' Create the JSON schema for the group (definition & values) '''
        gdef = [ "name", self.Name, "type", gtype ]
        if self.Order:
            selection = [
                "defaults", self.Defaults,
                "ordered", self.Order
            ]
        else:
            # JSON can't handle numpy arrays
            bools = [ [0,1][i] for i in self.Selection ]
            selection = [
                "defaults", self.Defaults,
                "unordered", [ "i8", bools ]
            ]
        return [ gdef, [ "selection", selection ] ]

def savePoly(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices,
        "closed", prim.Closed
    ]

def saveMesh(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices,
        "surface", prim.Surface,
        "uwrap", prim.Uwrap,
        "vwrap", prim.Vwrap,
    ]

def saveMetaBall(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices[0],
        "transform", prim.Transform,
        "metakernel", prim.Kernel,
        "metaweight", prim.Weight
    ]
def saveMetaSQuad(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices[0],
        "transform", prim.Transform,
        "metakernel", prim.Kernel,
        "metaweight", prim.Weight,
        "xy-exponent", prim.XYExponent,
        "z-exponent", prim.ZExponent
    ]
def saveParticle(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices,
        "renderproperties", prim.RenderProperties,
    ]

def saveQuadric(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices[0],
        "transform", prim.Transform,
    ]

def saveTube(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices[0],
        "transform", prim.Transform,
        "caps", prim.Caps,
        "taper", prim.Taper,
    ]

def saveSplineCurve(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices,
        "closed", prim.Closed,
        "basis", prim.Basis.save()
    ]

def saveSplineMesh(prim):
    ''' Create the schema for the primitive '''
    data = [
        "vertex", prim.Vertices,
        "surface", prim.Surface,
        "uwrap", prim.Uwrap,
        "vwrap", prim.Vwrap,
        "ubasis", prim.UBasis.save(),
        "vbasis", prim.VBasis.save()
    ]
    if hasattr(prim, 'Profiles'):
        # Profiles are stored as a contained detail
        data.append("profiles")
        data.append(prim.Profiles.saveJSON())
    return data

def saveVolume(prim):
    ''' Create the schema for the primitive '''
    return [
        "vertex", prim.Vertices[0],
        "transform", prim.Transform,
        "res", prim.Resolution,
        "border", prim.Border,
        "compression", prim.Compression,
        "voxels", prim.Voxels
    ]
def saveUnknown(prim):
    ''' Create the schema for an unknown primitive primitive.  This is simply
        the primitive data loaded for an unknown primitive. '''
    return prim.Data

primSavers = {
    'BezierCurve' : saveSplineCurve,
    'BezierMesh'  : saveSplineMesh,
    'Circle'      : saveQuadric,
    'Mesh'        : saveMesh,
    'MetaBall'    : saveMetaBall,
    'MetaSQuad'   : saveMetaSQuad,
    'NURBCurve'   : saveSplineCurve,
    'NURBMesh'    : saveSplineMesh,
    'Part'        : saveParticle,
    'Poly'        : savePoly,
    'Sphere'      : saveQuadric,
    'Tube'        : saveTube,
    'Volume'      : saveVolume,
}

class Primitive:
    '''
        A primitive represents a geometric primitive in a detail.  Every
        primitive has a vertex list and may have other intrinsic attributes
        (i.e. a closed flag for faces, a transform for quadrics, etc.).
    '''
    def __init__(self, prim_type, vertices=[]):
        ''' Initialize the primitive of the given type.  All primitives have a
        list of vertices '''
        self.Type = prim_type
        self.Vertices = vertices

    def save(self):
        ''' Call the appropriate save method to generate the schema for the
        primitive. '''
        return [
            [ "type", self.Type ],
            primSavers.get(self.Type, saveUnknown)(self)
        ]

    def getVertexCount(self):
        ''' Return the number of vertices used by the primitive '''
        return len(self.Vertices)
    def getVertexOffset(self, vertex_index):
        ''' Return vertex offset for the N'th vertex of the primitive '''
        return self.Vertices[vertex_index]

def loadBasis(bdata):
    ''' Create a Basis object from the schema '''
    b = Basis()
    b.load(bdata)
    return b

def loadPoly(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive('Poly', pdata['vertex'])
    prim.Closed = pdata.get('closed', True)
    return prim

def loadMesh(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive('Mesh', pdata['vertex'])
    prim.Surface = pdata['surface']
    prim.Uwrap = pdata['uwrap']
    prim.Vwrap = pdata['vwrap']
    return prim

def loadMetaBall(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, [pdata['vertex']])
    prim.Transform = pdata['transform']
    prim.Kernel = pdata['metakernel']
    prim.Weight = pdata['metaweight']
    return prim
def loadMetaSQuad(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, [pdata['vertex']])
    prim.Transform = pdata['transform']
    prim.Kernel = pdata['metakernel']
    prim.Weight = pdata['metaweight']
    prim.XYExponent = pdata['xy-exponent']
    prim.ZExponent = pdata['z-exponent']
    return prim

def loadQuadric(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, [pdata['vertex']])
    prim.Transform = pdata['transform']
    return prim

def loadTube(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive('Tube', [pdata['vertex']])
    prim.Transform = pdata['transform']
    prim.Caps = pdata.get('caps', False)
    prim.Taper = pdata.get('taper', 1)
    return prim

def loadSplineCurve(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, pdata['vertex'])
    prim.Closed = pdata['closed']
    prim.Basis = loadBasis(pdata['basis'])
    return prim

def loadSplineMesh(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, pdata['vertex'])
    prim.Surface = pdata['surface']
    prim.Uwrap = pdata['uwrap']
    prim.Vwrap = pdata['vwrap']
    prim.UBasis = loadBasis(pdata['ubasis'])
    prim.VBasis = loadBasis(pdata['vbasis'])
    profiles = pdata.get('profiles', None)
    if profiles:
        prim.Profiles = Detail()
        prim.Profiles.loadJSON(profiles)
    return prim

def loadParticle(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, pdata['vertex'])
    prim.RenderProperties = pdata.get('renderproperties', {})
    return prim
def loadVolume(ptype, pdata):
    ''' Load the primitive from the schema '''
    pdata = listToDict(pdata)
    prim = Primitive(ptype, [pdata['vertex']])
    prim.Transform = pdata['transform']
    # Voxel resolution
    prim.Resolution = pdata['res']
    # Dictionary of border parameters
    prim.Border = pdata['border']
    # Dictionary of compression parameters
    prim.Compression = pdata['compression']
    # JSON encoding of UT_VoxelArray
    prim.Voxels = pdata['voxels']
    return prim
def loadUnknown(ptype, pdata):
    ''' Load the primitive from the schema '''
    prim = Primitive(ptype, [])
    prim.Data = pdata
    return prim

primLoaders = {
    'BezierCurve'  : loadSplineCurve,
    'BezierMesh'   : loadSplineMesh,
    'Circle'       : loadQuadric,
    'Mesh'        : loadMesh,
    'MetaBall'    : loadMetaBall,
    'MetaSQuad'    : loadMetaSQuad,
    'NURBCurve'    : loadSplineCurve,
    'NURBMesh'     : loadSplineMesh,
    'Part'         : loadParticle,
    'Poly'         : loadPoly,
    'Sphere'       : loadQuadric,
    'Tube'        : loadTube,
    'Volume'       : loadVolume,

    # Uncommon primitive types.  These are passed through verbatim currently
    'MetaBezier'   : loadUnknown,
    'MetaLine'     : loadUnknown,
    'MetaTriangle' : loadUnknown,
    'PasteSurf'    : loadUnknown,
    'TriBezier'    : loadUnknown,
    'TriFan'       : loadUnknown,
    'TriStrip'     : loadUnknown,
}

def primRun(pdef, pdata):
    ''' Load a run of primitives.  A run consists of a set of "uniform" fields
        which have the same value for all primitives in the run as well as a
        list of the varying fields (fields which have different values for the
        primitives in the run).  Each primitive's data in the run has a simple
        list of data which maps exactly (in size and order) to the list of
        varying fields.'''
    # Load a run of primitives
    ptype = pdef['runtype']
    vfield = pdef['varyingfields']      # Values unique to each primitive
    data = pdef['uniformfields']      # Values shared by all run primitives
    primlist = []
    for v in pdata:
        vidx = 0
        for field in vfield:
            data[field] = v[vidx]
            vidx += 1
        primlist.append(primLoaders.get(ptype, loadUnknown)(ptype, data))
    return primlist

#class Detail: saved separately

    
#############################################################
#  Test Functions
#############################################################
def _ginfoAttributes(style, attributes):
    # Print out attributes
    if attributes:
        print '%s Attributes' % style
        for name in attributes:
            a = attributes[name]
            print '    %s %s[%d]' % (a.Type, a.Name, a.TupleSize)

def _ginfoGroups(style, groups):
    # Print out group information
    if groups:
        print '%s Groups' % style
        for name in groups:
            g = groups[name]
            ordered = ''
            if g.Order:
                ordered = 'ordered, '
            print'    %s (%s%d elements)' % (g.Name, ordered, g.Count)

def _ginfoPrimitives(primlist):
    # Print out primitive information
    counts = {}
    for p in primlist:
        counts[p.Type] = counts.get(p.Type, 0) + 1
    print '%d Primitives' % (len(primlist))
    for p in counts:
        print ' %10d %s' % (counts[p], p)

def _dumpPrimitive(detail, prim_num):
    prim = detail.Primitives[prim_num]
    nvtx = prim.getVertexCount()
    print 'Primitive', prim_num, 'is a', prim.Type, 'and has', nvtx, 'vertices.'
    P = detail.PointAttributes['P']
    for i in xrange(nvtx):
        vertex = prim.getVertexOffset(i)
        point = detail.vertexPoint(vertex)
        print '  Vertex[%d]->Point[%d]  P=' % (i, point), P.getValue(point)

def _ginfo(filename):
    try:
        fp = open(filename, 'r')
    except:
        print 'Unable to open', filename
        return
    _Verbose('Loading %s' % filename)
    fdata = hjson.load(fp)
    _Verbose('Done Loading %s' % filename)
    d = Detail()
    d.loadJSON(fdata)
    print '='*10, filename, '='*10
    print '%12d Points' % d.pointCount()
    print '%12d Vertices' % d.vertexCount()
    print '%12d Primitives' % d.primitiveCount()
    print '-'*5, 'Attributes', '-'*5
    _ginfoAttributes('Point', d.PointAttributes)
    _ginfoAttributes('Vertex', d.VertexAttributes)
    _ginfoAttributes('Primitive', d.PrimitiveAttributes)
    _ginfoAttributes('Global', d.GlobalAttributes)
    _ginfoGroups('Point', d.PointGroups)
    _ginfoGroups('Vertex', d.VertexGroups)
    _ginfoGroups('Primitive', d.PrimitiveGroups)
    _ginfoPrimitives(d.Primitives)
    _dumpPrimitive(d, 0)

def test():
    if len(sys.argv) == 1:
        _ginfo(os.path.expandvars('$HH/geo/defgeo.bgeo'))
    else:
        for f in sys.argv[1:]:
            _ginfo(f)

if __name__ == "__main__":
    VERBOSE = True
    test()

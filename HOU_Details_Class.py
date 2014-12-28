class Detail:
    '''
        A detail object contains:
            - Point Attributes
            - Vertex Attributes
            - Primitive Attributes
            - Global/Detail Attributes
            - VertexMap (which points are referenced by which vertices)
            - A list of primitives
            - Group information
    '''
    def __init__(self):
        ''' Initialize an empty detail '''
        self.PointAttributes = {}
        self.PrimitiveAttributes = {}
        self.VertexAttributes = {}
        self.GlobalAttributes = {}
        self.VertexMap = []
        self.Primitives = []
        self.Info = None

    def pointCount(self):
        ''' Return the number of points '''
        P = self.PointAttributes['P']
        return len(P.Array)
    def vertexCount(self):
        ''' Return the total number of vertices '''
        return len(self.VertexMap)
    def primitiveCount(self):
        ''' Return the number of primitives '''
        return len(self.Primitives)

    def vertexPoint(self, vertex_offset):
        ''' Return the point offset for the given vertex offset.  That is, the
            point referenced by the given vertex. '''
        return self.VertexMap[vertex_offset]

    def loadTopology(self, obj):
        ''' Load the topology -- the map of the unique vertices to shared
            points '''
        obj = listToDict(obj)
        pointref = listToDict(obj.get('pointref', None))
        _Assert(pointref, "Missing 'pointref' for topology")
        self.VertexMap = pointref.get('indices', None)
        _Assert(self.VertexMap and type(self.VertexMap) == list,
                "Invalid vertex topology")

    def loadSingleAttribute(self, attrib_data, element_count):
        ''' Interpret the schema for an attribute and create the attribute.
            Attributes are stored in a list of 2 objects.  The first object is
            the attribute definition, the second is the attribute's data.'''
        _Assert(type(attrib_data) == list and len(attrib_data) == 2,
                    'Invalid attribute defintion block')
        adef = listToDict(attrib_data[0])
        attrib = Attribute(adef['name'], adef['type'], adef['scope'])
        attrib.Options = adef.get('options', {})
        attrib.loadValues(attrib_data[1], element_count)
        return attrib

    def loadAttributeDict(self, attrib_list, element_count):
        ''' Interpret the schema for a dictionary of attributes.  That is, all
            the attributes for a given element type (point, vertex, etc.) '''
        if not attrib_list:
            return {}
        attributes = {}
        for attrib in attrib_list:
            a = self.loadSingleAttribute(attrib, element_count)
            if a:
                attributes[a.Name] = a
        return attributes

    def loadAttributes(self, obj, pointcount, vertexcount, primitivecount):
        ''' Interpret the schema to load all attributes '''
        obj = listToDict(obj)
        self.VertexAttributes = self.loadAttributeDict(
                        obj.get('vertexattributes', None), vertexcount)
        self.PointAttributes = self.loadAttributeDict(
                        obj.get('pointattributes', None), pointcount)
        self.PrimitiveAttributes = self.loadAttributeDict(
                        obj.get('primitiveattributes', None), primitivecount)
        self.GlobalAttributes = self.loadAttributeDict(
                        obj.get('globalattributes', None), 1)

    def loadElementGroup(self, obj, element_count):
        ''' Interpret the schema to load all element groups for a given type '''
        glist = {}
        nload = 0
        if obj:
            for g in obj:
                gdef = listToDict(g[0])
                gname = gdef['name']
                glist[gname] = ElementGroup(gname)
                glist[gname].loadSelection(g[1], element_count)
                nload += 1
                if nload % 100 == 0:
                    _Verbose('Loaded %d groups' % nload)
        return glist

    def loadElementGroups(self, obj):
        ''' Load all vertex, point and primitive groups '''
        self.VertexGroups = self.loadElementGroup(
                        obj.get('vertexgroups', None), self.vertexCount())
        self.PointGroups = self.loadElementGroup(
                        obj.get('pointgroups', None), self.pointCount())
        self.PrimitiveGroups = self.loadElementGroup(
                        obj.get('primitivegroups', None), self.primitiveCount())

    def loadSinglePrimitive(self, pdef, pdata):
        ''' Load a single primitive by finding a function to interpret the
            schema for the type.  If there's no known schema, we just hold onto
            the data block so it can be saved (see loadUnknown)'''
        pdef = listToDict(pdef)
        ptype = pdef['type']
        if ptype == 'run':
            self.Primitives += primRun(pdef, pdata)
        else:
            self.Primitives.append(primLoaders.get(ptype, loadUnknown)(ptype, pdata))

    def loadPrimitives(self, obj):
        ''' Load all primitives from the schema '''
        for p in obj:
            self.loadSinglePrimitive(p[0], p[1])

    def loadJSON(self, file):
        ''' Interpret the JSON object schema to create a Detail object '''
        file = listToDict(file)
        self.Info = file.get('info', None)
        self.loadTopology(file['topology'])
        _Verbose('Loaded Topology')
        self.loadAttributes(file['attributes'], pointcount=file['pointcount'],
                            vertexcount=file['vertexcount'],
                            primitivecount=file['primitivecount'])
        _Verbose('Loaded Attributes')
        self.loadPrimitives(file['primitives'])
        _Verbose('Loaded Primitives')
        self.loadElementGroups(file)
        _Verbose('Loaded Groups')

        # Trim regions for profile curves
        if file.has_key("altitude"):
            self.Altitude = file["altitude"]
        if file.has_key("trimregions"):
            self.TrimRegions = []
            for t in file["trimregions"]:
                region = TrimRegion()
                region.load(t)
                self.TrimRegions.append(region)

    def saveAttributes(self, name, adict):
        ''' Create the JSON schema for an attribute dictionary '''
        if not adict:
            return []
        attribs = []
        for a in adict:
            attribs += [adict[a].save()]
        return [ name, attribs ]

    def savePrimitives(self):
        ''' Create the JSON schema for all the primitives '''
        prims = []
        for p in self.Primitives:
            prims.append(p.save())
        return [ "primitives", prims ]

    def saveGroups(self, glabel, gtype, glist):
        ''' Create the JSON schema for the element groups for a single element
            type.'''
        if glist:
            groups = []
            for gname in glist:
                g = glist[gname]
                groups.append(g.save(gtype))
            return [ glabel, groups ]
        return []

    #------------------------------------WRITE OUT ---------------------------------------

    def saveJSON(self):
        ''' Create the JSON schema for the detail:  all the attributes,
            primitives, groups.
            For 2D (trim curves), the detail also contains special properties
            for the altitude and trim regions.'''
        data = []
        data += [ 'fileversion', _VERSION ]
        data += [ 'pointcount', self.pointCount() ]
        data += [ 'vertexcount', self.vertexCount() ]
        data += [ 'primitivecount', self.primitiveCount() ]
        data += [ 'topology', [ 'pointref', [ 'indices', self.VertexMap ] ] ]
        attribs = []
        attribs += self.saveAttributes('vertexattributes', self.VertexAttributes)
        attribs += self.saveAttributes('pointattributes', self.PointAttributes)
        attribs += self.saveAttributes('primitiveattributes', self.PrimitiveAttributes)
        attribs += self.saveAttributes('globalattributes', self.GlobalAttributes)
        if attribs:
            data += ["attributes", attribs]
        data += self.savePrimitives()
        data += self.saveGroups("pointgroups", "point", self.PointGroups)
        data += self.saveGroups("vertexgroups", "vertex", self.VertexGroups)
        data += self.saveGroups("primitivegroups", "primitive", self.PrimitiveGroups)
        if hasattr(self, 'Altitude'):
            data += ["altitude", self.Altitude]
        if hasattr(self, 'TrimRegions'):
            regions = []
            for t in self.TrimRegions:
                regions.append(t.save())
            data += ["trimregions", regions]
        return data

    def save(self, fp, indent=None):
        ''' Save the JSON schema to a file '''
        hjson.dump(self.saveJSON(), fp, indent=indent)



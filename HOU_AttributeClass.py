class Attribute:
    '''
        An attribute may be bound to point, primitive, vertex or detail
        elements.  The attribute stores an array of values, one for each
        element in the detail.
    '''
    def __init__(self, name, attrib_type, attrib_scope):
        ''' Initialize an attribute of the given name, type and scope '''
        # Data defined in definition block
        self.Name = name
        self.Type = attrib_type
        self.Scope = attrib_scope
        self.Options = {}
        # Data defined in per-attribute value block
        self.TupleSize = 1
        self.Array = []
        self.Defaults = None
        self.Strings = None

    def loadDefaults(self, obj):
        ''' Load defaults from the JSON schema '''
        obj = listToDict(obj)
        self.Defaults = None
        if obj:
            self.Defaults = obj.get('values', None)

    def getValue(self, offset):
        ''' Implemented for numeric/string attributes.
            Return's the value for the element offset '''
        if self.Type == "numeric":
            return self.Array[offset]
        elif self.Type == "string":
            str_idx = self.Array[offset]
            if str_idx < 0 or str_idx >= len(self.Strings):
                return ''
            return self.Strings[str_idx]
        return None

    def loadValues(self, obj, element_count):
        ''' Interpret the JSON schema to load numeric/string attributes '''
        obj = listToDict(obj)
        self.loadDefaults(obj.get('defaults', None))
        if self.Type == 'numeric':
            values = listToDict(obj['values'])
            self.TupleSize = values.get('size', 1)
            self.Array = values.get('tuples', None)
            self.Storage = values.get('storage', 'fpreal32')
            if not self.Array:
                pagedata = values.get('rawpagedata', None)
                if pagedata is not None:
                    packing = values.get('packing', [self.TupleSize])
                    pagesize = values.get('pagesize', -1)
                    _Assert(pagesize >= 0, "Expected pagesize field")
                    constflags = values.get('constantpageflags', None)
                    self.Array = _rawPageDataToTupleArray(
                                                raw=pagedata,
                                                packing=packing,
                                                pagesize=pagesize,
                                                constflags=constflags,
                                                total_tuples=element_count)
            if not self.Array:
                self.Array = values.get('arrays', None)
                _Assert(self.Array and self.TupleSize == 1,
                        "Expected a single value")
                # Stored as a tuple of arrays rather than an array of tuples,
                # so de-reference the index, giving the expected result.
                self.Array = self.Array[0]
        elif self.Type == 'string':
            self.Strings = obj['strings']
            indices = listToDict(obj['indices'])
            self.TupleSize = indices.get('size', 1)
            self.Array = indices.get('tuples', None)
            self.Storage = indices.get('storage', 'int32')
            if not self.Array:
                pagedata = indices.get('rawpagedata', None)
                if pagedata is not None:
                    packing = indices.get('packing', [self.TupleSize])
                    pagesize = indices.get('pagesize', -1)
                    _Assert(pagesize >= 0, "Expected pagesize field")
                    constflags = indices.get('constantpageflags', None)
                    self.Array = _rawPageDataToTupleArray(
                                                raw=pagedata,
                                                packing=packing,
                                                pagesize=pagesize,
                                                constflags=constflags,
                                                total_tuples=element_count)
            if not self.Array:
                self.Array = indices.get('arrays', None)
                _Assert(self.Array and self.TupleSize == 1,
                        "Expected a single value")
                self.Array = self.Array[0]
        else:
            # Unknown attribute type, so just store the entire attribute value
            # block
            print 'Unknown attribute type', self.Type
            self.Array = obj

    def save(self):
        ''' Create the JSON schema from the attribute's data '''
        adef = [
            "scope", self.Scope,
            "type", self.Type,
            "name", self.Name,
            "options", self.Options
        ]
        avalue = [
            "size", self.TupleSize,
        ]
        if self.Defaults:
            avalue += [
                "defaults", [
                    "size", len(self.Defaults),
                    "storage", "fpreal64",
                    "values", self.Defaults
                ]
            ]
        if self.Strings:
            avalue += [ "strings", self.Strings ]

        kword = "tuples"
        a = self.Array
        if self.TupleSize == 1:
            kword = "arrays"    # Store tuple of arrays not an array of tuples
            a = [self.Array]
        if self.Type == 'numeric':
            avalue += [ 'storage', self.Storage ]
            avalue += [
                "values", [
                    "size", self.TupleSize,
                    "storage", self.Storage,
                    kword, self.Array
                ]
            ]
        elif self.Type == 'string':
            avalue += [
                "indices", [
                    "size", self.TupleSize,
                    "storage", "int32",
                    kword, self.Array ]
            ]
        else:
            avalue += self.Array
        return [ adef, avalue ]

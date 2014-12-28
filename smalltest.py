#! /usr/bin/env python2.6

import cPickle as pickle
import shelve
import os




class Attribute(object):

    def __init__(self):
        self.data = {}
    
    def add_data(self,item,val):
        if item in self.data:
            self.data[item]=(val)
        else:
            self.data[item] = ()
            self.data[item]=val
            
        
        
        
        
class ToGeo(object):

    def __init__(self):
        self.P = Attribute()
        
        self.P.data["scope"]="public"
        self.P.data["storage"]="fpreal32"
        self.P.add_data("size",3)
        x = 'self.P.add_data('+'"tuplesize"'+',' +'"fpreal32"'+ ')'
        eval(x)
        
        
tree = ToGeo()
print tree.P.data

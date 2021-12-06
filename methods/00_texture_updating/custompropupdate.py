import bpy
from datetime import datetime

cube = bpy.context.object

def testpropupdate(self,context):
    print("UPDATED! :-)")
    print(cube.testprop)

def testpropget(self):
    return self["testprop"]

def testpropset(self, value):
    self["testprop"] = value
    print(datetime.now())
    print(cube.name)
    print(cube.testprop)

bpy.types.Object.testprop = bpy.props.IntProperty(name= "testprop", update=testpropupdate, get=testpropget, set=testpropset)

bpy.context.object.testprop = 1
bpy.context.object.keyframe_insert(data_path="testprop")
bpy.context.object.testprop = 10
bpy.context.object.keyframe_insert(data_path="testprop", frame=6)

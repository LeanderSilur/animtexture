import bpy


# Simple property reading/writing from ID properties.
# This is what the RNA would do internally.
def get_float(self):
    print("Getter", self["testprop"])
    return self["testprop"]
    pass

def set_float(self, value):
    print("Setter", value)
    self["testprop"] = value
    pass


bpy.types.Scene.test_float = bpy.props.FloatProperty(name="test", default=1, get=get_float, set=set_float)

# bpy.context.scene.test_float = 123

# bpy.context.scene.keyframe_insert(data_path="test_float")

def post_handler(scene):
    print("scene (post):", bpy.context.scene.test_float)
print(bpy.context.scene.test_float)
post = bpy.app.handlers.frame_change_post
for h in post:
    post.remove(h)
post.append(post_handler)

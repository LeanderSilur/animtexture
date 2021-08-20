import bpy

# link to images on hard drive
for i in range(1, 91):
    name = str(i).zfill(4)
    filepath = "//numbers\\" + name + ".png"
    image = bpy.data.images.load(filepath)
    image.name = name
    image.use_fake_user
    

# switch the images on playback
def my_handler(scene):
    frame = scene.frame_current 
    frame = scene.frame_current - scene.frame_current%4
    # frame = ... [complex rule]

    name = str(frame).zfill(4)
    img = bpy.data.images.get(name)
    
    bpy.data.materials[0].node_tree.nodes[2].image = img
    
frame_change_pre = bpy.app.handlers.frame_change_pre
[frame_change_pre.remove(h) for h in frame_change_pre if h.__name__ == "my_handler"]
frame_change_pre.append(my_handler)
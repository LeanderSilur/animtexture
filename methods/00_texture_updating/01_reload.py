import bpy

def my_handler(scene):
    frame = scene.frame_current
    name = str(frame).zfill(4)
    img = bpy.data.images[name]
#    frame = frame - frame % 4

    img.filepath = '//numbers\\' + str(frame).zfill(4) + '.png'
frame_change_pre = bpy.app.handlers.frame_change_pre
[frame_change_pre.remove(h) for h in frame_change_pre if h.__name__ == "my_handler"]
frame_change_pre.append(my_handler)
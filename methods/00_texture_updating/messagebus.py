import bpy

# Any Python object can act as the subscription's owner.
owner = object()

#subscribe_to = bpy.context.object.location
subscribe_to = bpy.context.object.animation_data.action.fcurves[0].keyframe_points[0].path_resolve("co_ui", False)

print(subscribe_to)
print(type(subscribe_to))

def msgbus_callback(*args):
    # This will print:
    # Something changed! (1, 2, 3)
    print("Something changed!", args[0].location)

bpy.msgbus.subscribe_rna(
    key=subscribe_to,
    owner=owner,
    args=(bpy.context.object,),
    notify=msgbus_callback,
)

#bpy.msgbus.clear_by_owner(owner)
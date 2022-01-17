import bpy

# Any Python object can act as the subscription's owner.
owner = object()

#subscribe_to = bpy.data.materials[0].node_tree.nodes[2].image
#subscribe_to = bpy.data.objects[0].location
subscribe_to = bpy.data.materials[0].node_tree.nodes[2]

def msgbus_callback(*args):
    # This will print:
    # Something changed! (1, 2, 3)
    print("Something changed!", args)

    # for node in bpy.context.object.active_material.node_tree.nodes:
    #     update_node_color(node)

bpy.msgbus.subscribe_rna(
    key=subscribe_to,
    owner=owner,
    args=(1, 2, 3),
    notify=msgbus_callback,
)
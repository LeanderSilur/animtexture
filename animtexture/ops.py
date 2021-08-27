import bpy
from bpy.app.handlers import persistent
from bpy.types import (
    FCurve,
    Keyframe,
    FCurveKeyframePoints,
    NODE_UL_interface_sockets,
    NodeTree,
    PropertyGroup,
    Operator,
    ShaderNodeTexImage,
    )
from bpy.props import (
    IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )


"""Properties attached to the Window Manager."""
class AnimtextureGlobalProperties(PropertyGroup):
    nextid: IntProperty(
        name="ShaderNodeTexImage Id",
        description="Distributes Ids to new ShaderNodeTexImage nodes.",
        default=1,
    )


"""Properties attached to the ShaderNodeTexImage."""
class AnimtextureProperties(PropertyGroup):
    id: IntProperty(
        name="Id",
        description="Id of this node.",
        default=0,
    )
    dimensions: IntVectorProperty(
        name="Dimensions",
        size=2,
        description="x and y dimension of the images",
        default=(512, 512),
    )
    savepath: StringProperty(
        name="Save Location",   
        description="Path to folder, where the images should be saved.",
        default=""
    )


"""Adds a new animtexture keyframe."""
class ANIM_OT_insert_animtexture(Operator):
    bl_label = "Insert"
    bl_idname = "anim.animtexture_insert"
    bl_description = "Insert a Keyframe"
    bl_options = {'REGISTER', 'UNDO'}
    # https://devtalk.blender.org/t/addon-operators-and-undo-support/4271/13
    
    @classmethod
    def poll(self, context):
        # TODO speed?
        node_tree = get_active_node_tree(context)
        return get_active_SNTI(node_tree) != None

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        
        if not tree.animation_data:
            tree.animation_data_create()
        if not tree.animation_data.action:
            # Since this action will be empty, the nextid will increment anyways
            tree.animation_data.action = bpy.data.actions.new(
                str(context.window_manager.animtexture_properties.nextid))

        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = tree.animation_data.action.fcurves.find(datapath)

        if not crv:
            # first registering
            nextid = context.window_manager.animtexture_properties.nextid
            node.animtexture.id = nextid
            nextid += 1
            context.window_manager.animtexture_properties.nextid = nextid

            # update the save path
            node.animtexture.savepath = "//animtexture" + str(nextid)

            # create a new curve and insert new keyframes
            crv = tree.animation_data.action.fcurves.new(datapath)
        
        y = -1
        for pt in crv.keyframe_points:
            y = max(y, pt.co.y)
        y = int(y + 1)
        
        # TODO these hardcoded namings could clash with user names
        # TODO 
        name = "AT" + str(node.animtexture.id) + "_" + str(y)
        img = bpy.data.images.get(name)
        if img: bpy.data.images.remove(img)
        img = bpy.data.images.new(name, *node.animtexture.dimensions, alpha=True)
        img.use_fake_user = True
        
        # TODO save images
        node.animtexturekey = y
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        # TODO update visual representation
        node.image = img
        return {'FINISHED'}


"""Saves the animated texture images."""
class ANIM_OT_save_animtexture(Operator):
    bl_label = "Save"
    bl_idname = "anim.animtexture_save"
    bl_description = "Save the Keyframes"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        # TODO speed?
        node_tree = get_active_node_tree(context)
        return get_keyframes_of_SNTI(node_tree) != None

    def execute(self, context):
        node_tree = get_active_node_tree(context)
        node = get_active_SNTI(node_tree)
        
        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = node_tree.animation_data.action.fcurves.find(datapath)

        indices = set()
        for k in crv.keyframe_points:
            indices.add(int(k.co.y))
            
        import os, pathlib
        full_path = bpy.path.abspath(node.animtexture.savepath)
        pathlib.Path(full_path).mkdir(parents=True, exist_ok=True)

        for i in indices:
            name = "AT" + str(node.animtexture.id) + "_" + str(i)
            img = bpy.data.images.get(name)
            if not img:
                print("problem")
            else:
                path = os.path.join(node.animtexture.savepath, str(i).zfill(6) + ".png")
                img.filepath_raw = path
                img.file_format = 'PNG'
                img.save()

        return {'FINISHED'}

"""Returns the activate node tree which selected via the gui (or null)."""
def get_active_node_tree(context) -> NodeTree:
    ob = context.object
    if len(ob.material_slots) == 0: return None
    mat = ob.material_slots[ob.active_material_index].material
    if not mat or not mat.use_nodes: return None
    return mat.node_tree


"""Returns the active ShaderNodeTexImage of the node_tree. Does also accept None as an input."""
def get_active_SNTI(node_tree) -> ShaderNodeTexImage:
    if (    not node_tree
            or not node_tree.nodes.active
            or not node_tree.nodes.active.type == 'TEX_IMAGE'):
        return None
    return node_tree.nodes.active


"""Returns the keyframes of a SNTI. Does also accept None as an input."""
def get_keyframes_of_SNTI(node_tree) -> FCurveKeyframePoints:
    if (    not node_tree
            or not node_tree.animation_data
            or not node_tree.animation_data.action
            or not node_tree.animation_data.action.fcurves):
        return None
    
    node = node_tree.nodes.active
    if not node or not node.type == 'TEX_IMAGE': return False

    datapath = 'nodes["' + node.name + '"].animtexturekey'
    crv = node_tree.animation_data.action.fcurves.find(datapath)
    if crv and len(crv.keyframe_points):
        return crv.keyframe_points
    return None


# switch the images on playback
@persistent
def animtexture_framechangehandler(scene):
    update_displayed_texture(bpy.context)

"""
    Update the displayed texture, based on the current frame and 
    the selected ShaderNodeTexImage
"""
def update_displayed_texture(context):
    # TODO speed?
    tree = get_active_node_tree(context)
    node = get_active_SNTI(tree)
    
    if not tree.animation_data or not tree.animation_data.action:
        return

    # TODO request unique id for folder organization
    id = "AT" + str(node.animtexture.id)
    datapath = 'nodes["' + node.name + '"].animtexturekey'
    crv = tree.animation_data.action.fcurves.find(datapath)

    if not crv:
        return

    image_number = int(crv.evaluate(context.scene.frame_current))
    
    name = "AT" + str(node.animtexture.id) + "_" + str(int(image_number))

    img = bpy.data.images.get(name)

    # TODO check?
    node.image = img


"""
    make sure the image sequence is saved
"""
def animtexture_loadprehandler():
    pass
"""
    make sure all the images are still there
    provide options to find them and reconnect them
"""
def animtexture_loadposthandler():
    pass
import bpy
from bpy.app.handlers import persistent
from bpy.types import (
    FCurve,
    Keyframe,
    FCurveKeyframePoints,
    NodeTree,
    PropertyGroup,
    Operator,
    ShaderNodeTexImage,
    )
from bpy.props import (
    IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )
import os
import shutil
import pathlib


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

        y = 0
        if not crv or not len(crv.keyframe_points):
            # first registering
            nextid = context.window_manager.animtexture_properties.nextid
            node.animtexture.id = nextid
            nextid += 1
            context.window_manager.animtexture_properties.nextid = nextid

            # update the save path
            node.animtexture.savepath = "//animtexture" + str(nextid)

            # create a new curve if necessary
            
            crv = tree.animation_data.action.fcurves.find(datapath)
            if not crv:
                crv = tree.animation_data.action.fcurves.new(datapath)

            #make path
            full_path = bpy.path.abspath(node.animtexture.savepath)
            pathlib.Path(full_path).mkdir(parents=True, exist_ok=True)
            print("make > ", full_path)


            # TODO these hardcoded namings could clash with user names
            # TODO 
            name = "AT" + str(node.animtexture.id)
            img = bpy.data.images.get(name)
            if img: bpy.data.images.remove(img)
            img = bpy.data.images.new(name, *node.animtexture.dimensions, alpha=True)
            img.use_fake_user = True

            path = os.path.join(node.animtexture.savepath, str(y).zfill(6) + ".png")
            img.filepath_raw = path
            img.file_format = 'PNG'
            img.save()
            
            shutil.copyfile(bpy.path.abspath(path),
                bpy.path.abspath(os.path.join(node.animtexture.savepath, "template.png")))

            img.source = 'SEQUENCE'
            img.filepath = path
            node.image = img
            node.image_user.frame_duration = context.scene.frame_end
            node.image_user.use_auto_refresh = True
        else:
            for pt in crv.keyframe_points:
                y = max(y, pt.co.y)
            y = int(y + 1)
            shutil.copyfile(
                bpy.path.abspath(os.path.join(node.animtexture.savepath, "template.png")),
                bpy.path.abspath(os.path.join(node.animtexture.savepath, str(y).zfill(6) + ".png"))
                )
        
        # TODO save images
        node.animtexturekey = y
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        # TODO update visual representation
        frame_offset = y - context.scene.frame_current
        node.image_user.frame_offset = frame_offset
        update_display_texture_imageeditor(context, node.image, frame_offset)
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

    def execute(self, context: bpy.context):
        node_tree = get_active_node_tree(context)
        node = get_active_SNTI(node_tree)
        
        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = node_tree.animation_data.action.fcurves.find(datapath)

        indices = dict()
        for k in crv.keyframe_points:
            indices[int(k.co.y)] = int(k.co.x)
        
        for v in indices:
            frame = indices[v]
            context.scene.frame_set(frame)
            context.view_layer.update()
            node.image.filepath_raw = os.path.join(
                node.animtexture.savepath,
                str(v).zfill(6) + ".png")
            node.image.save()

        node.image.filepath_raw = os.path.join(
            node.animtexture.savepath,
            str(0).zfill(6) + ".png")
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

    datapath = 'nodes["' + node.name + '"].animtexturekey'
    crv = tree.animation_data.action.fcurves.find(datapath)

    if not crv:
        return

    image_number = int(crv.evaluate(context.scene.frame_current))
    frame_offset = image_number - context.scene.frame_current
    node.image_user.frame_offset = frame_offset
    update_display_texture_imageeditor(context, node.image, frame_offset)


def update_display_texture_imageeditor(context, image, offset):
    for area in context.screen.areas:
        if area.type != 'IMAGE_EDITOR':
            continue
        if area.spaces[0].image == image:
            area.spaces[0].image_user.frame_offset = offset

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
import bpy
from bpy.app.handlers import persistent
from bpy.types import (
    BlendDataImages,
    FCurve,
    Image,
    Keyframe,
    FCurveKeyframePoints,
    NodeTree,
    PropertyGroup,
    Operator,
    ShaderNodeTexImage,
    )
from bpy.props import (
    EnumProperty, IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )
import os
import shutil
import pathlib



"""Adds a new animtexture keyframe."""
class ANIM_OT_insert_animtexture(Operator):
    bl_label = "Insert"
    bl_idname = "anim.animtexture_insert"
    bl_description = "Insert a Keyframe"
    bl_options = {'REGISTER'}
    # https://devtalk.blender.org/t/addon-operators-and-undo-support/4271/13

    name = StringProperty(name="Name")
    path = StringProperty(name="Path", subtype="DIR_PATH")
    dimensions = IntVectorProperty(name= "Dimensions", size=2, default=(512, 512))
    filetype: EnumProperty(
        name="filetype",
        items = [
            ('JPG', '.jpg', ''),
            ('PNG', '.png', ''),
            ('OPEN_EXR', '.exr', '')],
        default='OPEN_EXR'
    )
    PADDING = 4

    def invoke(self, context, event):
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
            crv = tree.animation_data.action.fcurves.new(datapath)
        self.tree = tree
        self.node = node
        self.crv = crv
        self.datapath = datapath

        if not len(crv.keyframe_points):
            #assign unique id
            i = 0
            while os.path.exists(bpy.path.abspath("//animtexture" + str(i))):
                i += 1
            self.path = "//animtexture" + str(i)
            self.name = "AT" + str(i)
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)
        

    @classmethod
    def poll(self, context):
        # TODO speed?
        node_tree = get_active_node_tree(context)
        return get_active_SNTI(node_tree) != None

    def execute(self, context):
        tree = self.tree
        node = self.node
        crv = self.crv
        datapath = self.datapath
        
        y = 0
        if not len(crv.keyframe_points):
            img = bpy.data.images.get(self.name)
            if img: bpy.data.images.remove(img)
            img = bpy.data.images.new(self.name, *self.dimensions, alpha=True)

            full_path = bpy.path.abspath(self.path)
            pathlib.Path(full_path).mkdir(parents=True, exist_ok=True)
            print("make > ", full_path)

            path = os.path.join(self.path, str(y).zfill(self.PADDING)
                + "." + str(self.filetype).split("_")[-1].lower())
            img.filepath_raw = path
            img.file_format = self.filetype
            img.save()
            
            shutil.copyfile(bpy.path.abspath(path),
                bpy.path.abspath(os.path.join(self.path, "template.png")))

            img.source = 'SEQUENCE'
            img.filepath = path
            node.image = img
            node.image_user.use_auto_refresh = True
        else:
            for pt in crv.keyframe_points:
                y = max(y, pt.co.y)
            y = int(y + 1)
            absfilepath = bpy.path.abspath(node.image.filepath)
            dir = os.path.dirname(absfilepath)
            _, ext = os.path.splitext(absfilepath)
            shutil.copyfile(
                bpy.path.abspath(os.path.join(dir, "template.png")),
                bpy.path.abspath(os.path.join(dir, str(y).zfill(self.PADDING) + ext))
                )
        
        # TODO save images
        node.animtexturekey = y
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        # TODO update visual representation
        frame_offset = y - context.scene.frame_current
        node.image_user.frame_offset = frame_offset

        update_display_texture_imageeditor(context, node.image, context.scene.frame_current, frame_offset)
        return {'FINISHED'}


"""Saves the animated texture images."""
class ANIM_OT_save_animtexture(Operator):
    bl_label = "Save"
    bl_idname = "anim.animtexture_save"
    bl_description = "Save the Keyframes"
    bl_options = {'REGISTER'}
    # TODO saveAll functionality
    save_all: bpy.props.BoolProperty(
        name='Save All',
        description='Save all AnimTexture-sequence which are active in nodes, even if the nodes are not selected.',
        default=False
        )

    def execute(self, context):
        images = []

        if self.save_all:
            images = [i for i in bpy.data.images if i.source == 'SEQUENCE']
        else:
            node_tree = get_active_node_tree(context)
            node = get_active_SNTI(node_tree)
            if node and node.image and node.image.source == 'SEQUENCE':
                images = [node.image]

        if not len(images):
            return {'FINISHED'}

        def save_img(images: BlendDataImages, context, area, errors):
            override = context.copy()
            override['area'] = area
            for i in images:
                if not os.path.exists(os.path.dirname(bpy.path.abspath(i.filepath))):
                    errors.append(i)
                    continue
                area.spaces.active.image = i
                bpy.ops.image.save_sequence(override)

        # Default to the current area, but look for an IMAGE_EDITOR
        area = context.area
        errors = []
        for a in context.screen.areas:
            if a.type == 'IMAGE_EDITOR':
                area = a
                break
        if area.type == 'IMAGE_EDITOR':
            # Other area is IMAGE_EDITOR.
            old_image = area.spaces.active.image
            save_img(images, context, area, errors)
            area.spaces.active.image = old_image
        else:
            # No area is IMAGE_EDITOR.
            # setup and save state
            old_type = context.area.type
            area.type = 'IMAGE_EDITOR'
            old_image = area.spaces.active.image
            
            save_img(images, context, area, errors)

            # restore state
            area.spaces.active.image = old_image
            area.type = old_type
        if len(errors):
            self.report({'WARNING'}, "Some files failed. Look in the console.")
            for e in errors:
                print(">", e.name)
        return {'FINISHED'}


"""Exports the animtexture sequence as an image sequence."""
class ANIM_OT_export_animtexture(Operator):
    bl_label = "Export"
    bl_idname = "anim.animtexture_export"
    bl_description = "Export the animated texture"
    bl_options = {'REGISTER'}

    dirpath: bpy.props.StringProperty(subtype="DIR_PATH")

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        node_tree = get_active_node_tree(context)
        node = get_active_SNTI(node_tree)
        if node and node.image and node.image.source == 'SEQUENCE':
            images = [node.image]

        print ("Directorypath:", self.dirpath)
        print ("Folder name:", os.path.dirname(self.dirpath))
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
def get_keyframes_of_SNTI(node_tree, node) -> FCurveKeyframePoints:
    if (    not node_tree
            or not node_tree.animation_data
            or not node_tree.animation_data.action
            or not node_tree.animation_data.action.fcurves):
        return []
    
    if not node or not node.type == 'TEX_IMAGE':
        return []

    datapath = 'nodes["' + node.name + '"].animtexturekey'
    crv = node_tree.animation_data.action.fcurves.find(datapath)
    if crv and len(crv.keyframe_points):
        return crv.keyframe_points
    return []


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

    frame = context.scene.frame_current
    image_number = int(crv.evaluate(frame))
    frame_offset = image_number - frame
    node.image_user.frame_duration = frame
    node.image_user.frame_offset = frame_offset
    
    update_display_texture_imageeditor(context, node.image, frame, frame_offset)


def update_display_texture_imageeditor(context, image, duration, offset):
    for area in context.screen.areas:
        if area.type != 'IMAGE_EDITOR':
            continue
        if area.spaces.active.image == image:
            area.spaces.active.image_user.frame_duration = duration
            area.spaces.active.image_user.frame_offset = offset

"""
    make sure the image sequence is saved
"""
@persistent
def animtexture_savewithfile(empty):
    # TODO find more elegant solution
    context = bpy.context
    SAVE_ALL = context.preferences.addons[__package__].preferences.savewithfile == 'SAVE_ALL'
    bpy.ops.anim.animtexture_save(save_all=SAVE_ALL)

"""
    make sure all the images are still there when we reopen a file
    provide options to find them and reconnect them
"""
@persistent
def animtexture_checklinks(empty):
    # TODO find more elegant solution
    print("checking on open")
    return
    # TODO
    context = bpy.context

    sequence_nodes = []
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                continue
            if node.image and node.image.source == 'SEQUENCE':
                sequence_nodes.append([mat.node_tree, node])
    for tree, node in sequence_nodes:
        keys = get_keyframes_of_SNTI(tree, node)
        values = [k.co.y for k in keys]
    
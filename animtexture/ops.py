import string
import bpy
from typing import List, Tuple
from bpy.app.handlers import persistent
from bpy.ops import image
from bpy.types import (
    BlendDataImages,
    Context,
    FCurve,
    Image,
    Keyframe,
    FCurveKeyframePoints,
    Node,
    NodeTree,
    OverDropSequence,
    PropertyGroup,
    Operator,
    ShaderNodeTexImage,
    )
from bpy.props import (
    BoolProperty, EnumProperty, IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )
import os
import shutil
import pathlib



class ANIM_OT_insert_animtexture(Operator):
    """Adds a new animtexture keyframe."""
    bl_label = "Insert"
    bl_idname = "anim.animtexture_insert"
    bl_description = "Insert an Animtexture Keyframe for the active Texture Node"
    bl_options = {'REGISTER'}
    # https://devtalk.blender.org/t/addon-operators-and-undo-support/4271/13

    directory: bpy.props.StringProperty(
        name="Directory",
        description="Save path for the image sequence.",
        subtype="DIR_PATH"
    )
    name: StringProperty(
        name="Name",
        description="Name of the Image Texture in Blender."
    )
    filetype: EnumProperty(
        name="Extension",
        description="Filetype of the images.",
        items = [
            ('JPEG', '.jpeg', ''),
            ('PNG', '.png', ''),
            ('OPEN_EXR', '.exr', '')],
        default='OPEN_EXR'
    )
    padding: IntProperty(
        name="Padding",
        min=1,max=20,
        default=4
    )
    dimensions: IntVectorProperty(
        name= "Dimensions",
        size=2,
        default=(512, 512)
    )
    rgba: EnumProperty(
        name="Color Space",
        description="Color Space of the Images.",
        items = [
            ('RGB', 'RGB', ''),
            ('RGBA', 'RGBA', '')],
        default='RGBA'
    )
    transparent: BoolProperty(
        name= "Transparent by Default",
        description="Newly created images are transparent in alpha by default.",
        default=True
    )

    @classmethod
    def poll(self, context):
        # TODO speed?
        node_tree = get_active_node_tree(context)
        return get_active_SNTI(node_tree) != None

    def invoke(self, context, event):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        attach_action_if_needed(tree)

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
            self.directory = "//animtexture" + str(i)
            self.name = "AT" + str(i)
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)
        
    def execute(self, context):
        tree = self.tree
        node = self.node
        crv = self.crv
        datapath = self.datapath
        
        if not len(crv.keyframe_points):
            
            

            img = bpy.data.images.get(self.name)
            if img: bpy.data.images.remove(img)
            img = bpy.data.images.new(self.name,
                                    *self.dimensions,
                                    alpha=self.rgba=='RGBA')
            if self.rgba=='RGBA' and self.transparent:
                buffer = [img.pixels[0] * 0] * len(img.pixels)
                img.pixels.foreach_set(buffer)

            full_path = bpy.path.abspath(self.directory)
            pathlib.Path(full_path).mkdir(parents=True, exist_ok=True)
            print("make > ", full_path)

            ext = "." + str(self.filetype).split("_")[-1].lower()
            path = os.path.join(self.directory, str(0).zfill(self.padding)
                +  ext)
            img.filepath_raw = path
            img.file_format = self.filetype
            img.save()
            
            shutil.copyfile(bpy.path.abspath(path),
                bpy.path.abspath(os.path.join(self.directory, "template" + ext)))

            img.source = 'SEQUENCE'
            img.filepath = path
            node.image = img
            node.image_user.use_auto_refresh = True
            node.animtexturekeynext = 0
        else:
            if not node.image or node.image.source != "SEQUENCE":
                self.report({'ERROR'}, "There seem to be keyframes left, but no image in the texture node. Did you accidentally detach the image from the texture node?")
                return {'CANCELLED'}
                
            dir, name, padding, ext = get_sequence_path_info(node.image.filepath)
            
            try:
                shutil.copyfile(
                    bpy.path.abspath(os.path.join(dir, "template" + ext)),
                    bpy.path.abspath(os.path.join(dir, name + str(node.animtexturekeynext).zfill(padding) + ext))
                    )
            except OSError:
                # TODO check what raised the error and give useful feedback
                # (1) source file doesnt exist OR/AND (2) path not writable
                # self.report()
                return {'CANCELLED'}
        
        node.animtexturekey = node.animtexturekeynext
        node.animtexturekeynext += 1
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        return {'FINISHED'}


class ANIM_OT_duplicate_animtexture(Operator):
    """Duplicates the current animtexture file and insert it as a new keyframe."""
    bl_label = "Duplicate"
    bl_idname = "anim.animtexture_duplicate"
    bl_description = "Duplicate an Animtexture Keyframe for the active Texture Node"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        # TODO speed?
        node_tree = get_active_node_tree(context)
        node = get_active_SNTI(node_tree)
        if not node: return False
        keys = get_keyframes_of_SNTI(node_tree, node)
        return len(keys) > 0

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        
        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = tree.animation_data.action.fcurves.find(datapath)
        
        frame = int(context.scene.frame_current)
        key = int(crv.evaluate(frame))
        key_values = [int(k.co.y) for k in crv.keyframe_points]
        if key not in key_values:
            self.report({'ERROR'}, "The keyframes seem to be faulty. Check that their interpolation is set to CONSTANT. Also file this as a bug.")
            return {'CANCELLED'}

        dir, name, padding, ext = get_sequence_path_info(node.image.filepath)

        
        # save active image
        image_editor, restore_image_editor = get_image_editor(context)
        override = context.copy()
        override['area'] = image_editor

        image_editor.spaces.active.image = node.image
        image_editor.spaces.active.image_user.frame_duration = frame
        image_editor.spaces.active.image_user.frame_offset = key - frame
        context.scene.frame_set(frame)
        res = bpy.ops.image.save(override)
        restore_image_editor()

        # then duplicate it
        shutil.copyfile(
            bpy.path.abspath(os.path.join(dir, name + str(key).zfill(padding) + ext)),
            bpy.path.abspath(os.path.join(dir, name + str(node.animtexturekeynext).zfill(padding) + ext))
            )

        # insert a new keyframe for the duplicated image
        node.animtexturekey = node.animtexturekeynext
        node.animtexturekeynext += 1
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        return {'FINISHED'}


"""Saves the animated texture images."""
class ANIM_OT_save_animtexture(Operator):
    bl_label = "Save"
    bl_idname = "anim.animtexture_save"
    bl_description = "Save the Animtexture Keyframes"
    bl_options = {'REGISTER'}
    # TODO saveAll functionality
    save_all: bpy.props.BoolProperty(
        name='Save All',
        description='Save all AnimTexture-sequence which are active in nodes, even if the nodes are not selected.',
        default=False
        )

    def execute(self, context):
        class Img():
            def __init__(self, image: Image, keyframes: FCurveKeyframePoints) -> None:
                self.image = image
                self.keyframes = keyframes
        images = []

        if self.save_all:
            # Check all nodes in materials with keyframes.
            for mat in bpy.data.materials:
                if (    not mat.use_nodes or
                        not mat.node_tree.animation_data or
                        not mat.node_tree.animation_data.action):
                    continue
                for node in mat.node_tree.nodes:
                    keys = get_keyframes_of_SNTI(mat.node_tree, node)
                    if len(keys) > 0:
                        images.append(Img(node.image, keys))
        else:
            node_tree = get_active_node_tree(context)
            node = get_active_SNTI(node_tree)
            keys = get_keyframes_of_SNTI(node_tree, node)
            if len(keys) > 0:
                images.append(Img(node.image, keys))

        if not len(images):
            return {'FINISHED'}

        # Save img objects in a list of List[Img].
        def save_images(images: List[Img], context, image_editor, errors):
            override = context.copy()
            override['area'] = image_editor

            for img in images:
                i = img.image
                
                absfilepath = bpy.path.abspath(i.filepath)
                dir, name, padding, ext = get_sequence_path_info(absfilepath)
                if not os.path.exists(dir):
                    errors.append(i)
                    continue
                image_editor.spaces.active.image = i
                bpy.ops.image.save_sequence(override)

                # Delete unused - left over - images.
                if context.preferences.addons[__package__].preferences.reorganizeOnSave:
                    clean_directory(img.keyframes, absfilepath)

        errors = []
        image_editor, restore_image_editor = get_image_editor(context)
        save_images(images, context, image_editor, errors)
        restore_image_editor()
        
        if len(errors):
            self.report({'WARNING'}, "Some files failed. Look in the console.")
            for e in errors:
                print(">", e.name)
        return {'FINISHED'}


"""Imports an image sequence as an animtexture sequence."""
class ANIM_OT_import_animtexture(Operator):
    bl_label = "Import"
    bl_idname = "anim.animtexture_import"
    bl_description = "Import an image sequence"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    stop_at_gaps: bpy.props.BoolProperty(name="Stop at Gaps", default=False)
    use_rel_path: bpy.props.BoolProperty(name="Make Relative", default=True)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = get_active_node_tree(context)
        node =  get_active_SNTI(tree)
        if not node:
            self.report({'ERROR'}, "Select a ImageTexture node first.")
            return {'CANCELLED'}
        
        # get file info and files in directory
        dir, name, padding, ext = get_sequence_path_info(self.filepath)
        all_files = os.listdir(dir)
        
        # create template if necessary
        if "template" + ext not in all_files:
            tmp_img = bpy.data.images.load(self.filepath)
            buffer = [tmp_img.pixels[0] * 0] * len(tmp_img.pixels)
            tmp_img.pixels.foreach_set(buffer)
            tmp_img.filepath_raw = os.path.join(dir, "template" + ext)
            tmp_img.save()
            bpy.data.images.remove(tmp_img)
        
        length = len(name) + padding + len(ext)
        files = [f for f in all_files
            if f.startswith(name)
                and len(f) == length
                and f[len(name):len(name) + padding].isdigit()
                and f.endswith(ext)]
        files.sort()

        # get first image and remove doubles
        from filecmp import cmp

        a, b = len(name), len(name) + padding
        get_index = lambda filename: int(filename[a:b])

        img_a = os.path.basename(self.filepath)
        start = files.index(img_a)
        keys = [get_index(img_a)]
        for i in range(start + 1, len(files)):
            img_b = files[i]
            if not cmp(os.path.join(dir, img_a), os.path.join(dir, img_b)):
                keys.append(get_index(img_b))
                img_a = img_b

        # create/overwrite keyframes
        attach_action_if_needed(tree)

        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = tree.animation_data.action.fcurves.find(datapath)
        if not crv:
            crv = tree.animation_data.action.fcurves.new(datapath)
        
        while len(crv.keyframe_points) > len(keys):
            crv.keyframe_points.remove(crv.keyframe_points[0], fast=True)
        if len(crv.keyframe_points) < len(keys):
            crv.keyframe_points.add(len(keys) - len(crv.keyframe_points))
        for pt, key in zip(crv.keyframe_points, keys):
            pt.co.x = key
            pt.co.y = key
            pt.interpolation = 'CONSTANT'

        node.animtexturekeynext = keys[-1] + 1

        # imageblock, assign image block, add offset, 
        if self.use_rel_path and bpy.data.is_saved:
            self.filepath = bpy.path.relpath(self.filepath)
        
        node.image = bpy.data.images.load(self.filepath)
        node.image.source = 'SEQUENCE'
        node.image_user.use_auto_refresh = True

        node.animtexturekey = int(crv.evaluate(context.scene.frame_current))
        update_texture(context)
        
        return {'FINISHED'}


"""Imports a single image into an animtexture sequence."""
class ANIM_OT_import_single_animtexture(Operator):
    bl_label = "Import Single"
    bl_idname = "anim.animtexture_import_single"
    bl_description = "Import a single image into an animtexture sequence"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(self, context):
        # TODO speed?
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        if not node: return False
        keys = get_keyframes_of_SNTI(tree, node)
        return len(keys) > 0

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)

        # get file info and files in directory
        dir, name, padding, ext1 = get_sequence_path_info(self.filepath)

        dir, name, padding, ext2 = get_sequence_path_info(node.image.filepath)

        if ext1 != ext2:
            self.report({'ERROR'}, "Wrong file extension.")
            return {'CANCELLED'}
        
        # then duplicate it
        shutil.copyfile(
            bpy.path.abspath(self.filepath),
            bpy.path.abspath(os.path.join(dir, name + str(node.animtexturekeynext).zfill(padding) + ext2))
            )

        # insert a new keyframe for the duplicated image
        datapath = 'nodes["' + node.name + '"].animtexturekey'
        keyframe_points = get_keyframes_of_SNTI(tree, node)
        node.animtexturekey = node.animtexturekeynext
        node.animtexturekeynext += 1
        tree.keyframe_insert(data_path=datapath)
        keyframe_points[-1].interpolation = 'CONSTANT'

        return {'FINISHED'}


class ANIM_OT_export_animtexture(Operator):
    """Exports the animtexture sequence as an image sequence."""
    bl_label = "Export"
    bl_idname = "anim.animtexture_export"
    bl_description = "Export the animated texture"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    fill_gaps: bpy.props.BoolProperty(name="Fill Gaps", default=True)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        if not node.image or node.image.source != 'SEQUENCE':
            self.report({'ERROR'}, "Select a ImageTexture node with animtexture sequence first.")
            return {'CANCELLED'}

        # TODO check if this function can be referenced
        fullpath = bpy.path.abspath(node.image.filepath)
        dir = os.path.dirname(fullpath)
        filename = os.path.basename(fullpath)
        base, ext = os.path.splitext(filename)

        keyframes = get_keyframes_of_SNTI(tree, node)
        keys = {int(k.co.x):int(k.co.y) for k in keyframes}

        key = keys[min(keys.keys())]
        if self.fill_gaps:
            for frame in range(context.scene.frame_start, context.scene.frame_end + 1):
                if frame in keys:
                    key = keys[frame]
                path_in = os.path.join(dir, str(key).zfill(len(base)) + ext)
                path_out = os.path.join(self.directory, str(frame).zfill(len(base)) + ext)
                shutil.copyfile(path_in, path_out)
        else:
            for frame in keys:
                key = keys[frame]
                path_in = os.path.join(dir, str(key).zfill(len(base)) + ext)
                path_out = os.path.join(self.directory, str(frame).zfill(len(base)) + ext)
                shutil.copyfile(path_in, path_out)

        return {'FINISHED'}


class ANIM_OT_openimage_animtexture(Operator):
    """Looks for an active ShaderNodeTextureImage with an image sequence and opens it in a UV Editor."""
    bl_label = "Open in Editor"
    bl_idname = "anim.animtexture_openimage"
    bl_description = "Show the active texture in the image editor."
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # TODO speed?
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        return node and node.image and node.image.source == 'SEQUENCE'

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
            
        for area in context.screen.areas:
            if area.type in ['IMAGE_EDITOR', 'UV_EDITOR']:
                area.spaces.active.image = node.image
                area.spaces.active.image_user.frame_duration = node.image_user.frame_duration
                area.spaces.active.image_user.frame_offset = node.image_user.frame_offset
                return {'FINISHED'}

        self.report({'WARNING'}, "Open an ImageEditor or UV Editor first.")
        return {'CANCELLED'}


def clean_directory(keyframe_points, absfilepath):
    """Removes all images except for the required images from the animtexture directory."""
    dir, name, padding, ext = get_sequence_path_info(absfilepath)
    key_values = [int(k.co.y) for k in keyframe_points]
    def create_path(i):
        return os.path.join(dir, name + str(i).zfill(padding) + ext)
    required_files = [name + str(y).zfill(padding) + ext for y in key_values]
    required_files.append("template" + ext)

    for file in os.listdir(dir):
        if file not in required_files:
            os.remove(os.path.join(dir, file))
            print(file)
            
    transfer = dict()
    covered = []
    i = 0
    for k in keyframe_points:
        v = int(k.co.y)
        if v not in transfer:
            transfer[v] = i
            i += 1
        k.co.y = transfer[v]
        if transfer[v] == v:
            del transfer[v]
    
    duplicate = []
    for t in transfer:
        v = transfer[t]
        a = create_path(t)
        b = create_path(v)
        
        if v in transfer:
            b += "d"
            duplicate.append(b)
        os.rename(a, b)
    for d in duplicate:
        os.rename(d, d[:-1])
        pass
    return i



def get_image_editor(context: Context):
    """Get an image_editor area and a callback to restore it."""

    # Current area is IMAGE_EDITOR.
    if context.area.type =='IMAGE_EDITOR':
        former_image = context.area.spaces.active.image
        def restore():
            context.area.spaces.active.image = former_image
        return context.area, restore
    
    area = context.area
    for a in context.screen.areas:
        if a.type == 'IMAGE_EDITOR':
            area = a
            break

    if area.type == 'IMAGE_EDITOR':
        # Other area is IMAGE_EDITOR.
        former_image = area.spaces.active.image
        area.spaces.active.image = former_image
        def restore():
            area.spaces.active.image = former_image
        return area, restore
    else:
        # No area is IMAGE_EDITOR.
        # setup and save state
        former_type = context.area.type
        area.type = 'IMAGE_EDITOR'
        former_image = area.spaces.active.image
        
        def restore():
            area.spaces.active.image = former_image
            area.type = former_type
        return area, restore


def get_sequence_path_info(path: str) -> Tuple[str, int, str]:
    """Returns: directory, name, padding, extension(with a leading dot)."""
    absfilepath = bpy.path.abspath(path)
    dir = os.path.dirname(absfilepath)
    name, ext = os.path.splitext(os.path.basename(absfilepath))
    stripped_name = name.rstrip(string.digits)
    return dir, stripped_name, len(name) - len(stripped_name), ext

def attach_action_if_needed(tree:NodeTree):
    """Create AnimationData and a new Action if required."""
    if not tree.animation_data:
        tree.animation_data_create()
    if not tree.animation_data.action:
        suffix = 0
        while bpy.data.actions.find("AT" + str(suffix)) > 0:
            suffix += 1
        tree.animation_data.action = bpy.data.actions.new("AT" + str(suffix))

"""Returns the activate node tree which selected via the gui (or null)."""
def get_active_node_tree(context) -> NodeTree:
    ob = context.object
    if len(ob.material_slots) == 0: return None
    mat = ob.material_slots[ob.active_material_index].material
    if not mat or not mat.use_nodes: return None
    return mat.node_tree

# TODO naming of duplicate function
"""Returns the node tree of an object."""
def get_node_tree(ob) -> NodeTree:
    if len(ob.material_slots) == 0: return None
    mat = ob.material_slots[ob.active_material_index].material
    if not mat or not mat.use_nodes: return None
    return mat.node_tree

def get_active_SNTI(node_tree) -> ShaderNodeTexImage:
    """Returns the active ShaderNodeTexImage of the node_tree. Does also accept None as an input."""
    if (    not node_tree
            or not node_tree.nodes.active
            or not node_tree.nodes.active.type == 'TEX_IMAGE'):
        return None
    return node_tree.nodes.active


def get_keyframes_of_SNTI(node_tree: NodeTree, node: Node) -> FCurveKeyframePoints:
    """Returns the keyframes of a SNTI (ShaderNodeTexImage). Does also accept None as an input."""
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


def animtexturekey_get(self):
    """Getter for SNTI attribute `animtexturekey`."""
    return self["ATK"]

def animtexturekey_set(self, value):
    """Setter for SNTI attribute `animtexturekey`."""
    if "ATK" not in self or self["ATK"] != value:
        self["ATK"] = value
        udpate_texture_setter(self, value)


def animtexture_startupcheckhandler():
    errors = {}
    for mat in bpy.data.materials:
        if (    not mat.use_nodes or
                not mat.node_tree.animation_data or
                not mat.node_tree.animation_data.action):
            continue
        for node in mat.node_tree.nodes:
            keys = get_keyframes_of_SNTI(mat.node_tree, node)
            if len(keys) == 0:
                continue
            if not node.image or node.image.source != 'SEQUENCE':
                continue

            dir, name, padding, ext = get_sequence_path_info(node.image.filepath)
            if os.path.exists(dir):
                indices = [int(key.co.y) for key in keys]
                existingfiles= os.listdir(dir)
                for index in indices:
                    filename = name + str(index).zfill(padding) + ext
                    if not filename in existingfiles:
                        if node.name not in errors:
                            errors[node.name] = []
                        errors[node.name].append(filename)
    if len(errors):
        def draw(self, context):
            col = self.layout.column()
            for nodename, imagenumbers in errors.items():
                col.label(text=nodename + str(imagenumbers))

        bpy.context.window_manager.popup_menu(draw, title = "Animtexture: There are files missing:", icon='ERROR')   


@persistent
def animtexture_framechange(scene):
    update_texture(bpy.context)

@persistent
def animtexture_loadpost(scene):
    animtexture_startupcheckhandler()
    update_texture(bpy.context)
    # Not working yet.
    bpy.context.view_layer.update()

def update_texture(context):
    """
    Update the displayed texture, based on the current frame and 
    the selected ShaderNodeTexImage
    """
    # TODO speed?
    if not context.object:
        return
    tree = get_active_node_tree(context)
    node = get_active_SNTI(tree)
    
    if not tree.animation_data or not tree.animation_data.action:
        return

    datapath = 'nodes["' + node.name + '"].animtexturekey'
    crv = tree.animation_data.action.fcurves.find(datapath)

    if not crv:
        return

    frame = context.scene.frame_current
    # image_number_0 = int(crv.evaluate(frame))
    image_number = node.animtexturekey

    frame_offset = image_number - frame
    duration = max(frame + 1, 1)
    node.image_user.frame_duration = duration
    node.image_user.frame_offset = frame_offset

    update_display_texture_imageeditor(node.image, duration, frame_offset)

def udpate_texture_setter(node, image_number):
    frame = bpy.context.scene.frame_current
    frame_offset = image_number - frame
    duration = max(frame, 1)
    node.image_user.frame_duration = duration
    node.image_user.frame_offset = frame_offset
    
    update_display_texture_imageeditor(node.image, duration, frame_offset)

def update_display_texture_imageeditor(image, duration, offset):
    for screen in bpy.data.screens:
        for area in screen.areas:
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

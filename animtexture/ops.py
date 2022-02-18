from re import T
import string
import bpy
from typing import List, Tuple
from bpy.app.handlers import persistent
from bpy.ops import image
from bpy.types import (
    ShaderNodeTree, Context, FCurve, Image, Keyframe, FCurveKeyframePoints, Node, NodeTree, PropertyGroup, Operator, ShaderNodeTexImage,
    )
from bpy.props import (
    BoolProperty, EnumProperty, IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )
import os
import shutil
import pathlib
from filecmp import cmp as filecompare

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
    bg_color: bpy.props.FloatVectorProperty(
        name="Background Color",
        description="Background Color for newly created images",
        subtype="COLOR",
        size = 4,
        default=(0.0, 0.0, 0.0, 0.0),
        min=0.0, max=1.0,
    )
    delete_keyframes: BoolProperty(
        name= "Delete leftover keyframes",
        description="Leftover keyframes from old image texture are deleted when new tecture is created.",
        default=False,
        options ={'HIDDEN'},
    )

    @classmethod
    def poll(cls, context):
        node_tree = get_active_node_tree(context)
        return get_active_SNTI(node_tree) != None

    def invoke(self, context, event):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        attach_action_if_needed(tree)

        datapath = get_animkeydatapath(node.name)
        crv = (tree.animation_data.action.fcurves.find(datapath)
            or tree.animation_data.action.fcurves.new(datapath))

        if len(crv.keyframe_points) and (not node.image or node.image.source != "SEQUENCE"):
            if self.delete_keyframes:
                pts = crv.keyframe_points
                while len(pts):
                    pts.remove(pts[0], fast=True)
            else:
                bpy.ops.anim.animtexture_insertdelete('INVOKE_DEFAULT')
                return {'CANCELLED'}

        if not len(crv.keyframe_points):
            self.name = "AT"
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)
        
    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        datapath = get_animkeydatapath(node.name)
        crv = tree.animation_data.action.fcurves.find(datapath)

        if not len(crv.keyframe_points):

            # create a new image
            if len(self.name) and self.name[-1:].isdigit():
                self.name += "_"

            img = bpy.data.images.get(self.name)
            if img: bpy.data.images.remove(img)
            img = bpy.data.images.new(self.name,
                                    *self.dimensions,
                                    alpha=True)
            
            buffer = list(self.bg_color) * int(len(img.pixels) / 4)
            img.pixels.foreach_set(buffer)

            # create directory
            full_path = bpy.path.abspath(self.directory)
            pathlib.Path(full_path).mkdir(parents=True, exist_ok=True)
            
            # create image file in directory
            ext = "." + str(self.filetype).split("_")[-1].lower()
            path = os.path.join(self.directory, self.name + "0" * self.padding
                +  ext)
            img.filepath_raw = path
            img.file_format = self.filetype
            img.save()
            
            #create template
            shutil.copyfile(bpy.path.abspath(path),
                bpy.path.abspath(bpy.path.abspath(get_template(path))))
            
            if img.file_format == 'OPEN_EXR':
                img.alpha_mode = 'PREMUL'
            img.source = 'SEQUENCE'
            img.filepath = path
            node.image = img
            node.image_user.use_auto_refresh = True
            node.animtexturekeynext = 0

            msgbus_subscribe_to(node, tree)

        else:
            dir, name, padding, ext = get_sequence_path_info(node.image.filepath)
            
            try:
                # create new image from template
                shutil.copyfile(
                    bpy.path.abspath(get_template(node.image.filepath)),
                    bpy.path.abspath(os.path.join(
                        dir,
                        name + str(node.animtexturekeynext).zfill(padding) + ext))
                    )
            except OSError as e:
                # if the template file is missing, call dialog box operator (missing template error) 
                path = bpy.path.abspath(get_template(node.image.filepath))
                if not pathlib.Path(path).exists():
                    bpy.ops.anim.animtexture_insertmissingtemplate('INVOKE_DEFAULT')
                else:
                    self.report({'ERROR'}, "Unknown problem.")
                return {'CANCELLED'}
            
        # create keyframe
        node.animtexturekey = node.animtexturekeynext
        node.animtexturekeynext += 1
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        update_node_color(node)

        return {'FINISHED'}


class ANIM_OT_duplicate_animtexture(Operator):
    """Duplicates the current animtexture file and insert it as a new keyframe."""
    bl_label = "Duplicate"
    bl_idname = "anim.animtexture_duplicate"
    bl_description = "Duplicate an Animtexture Keyframe for the active Texture Node."
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        node_tree = get_active_node_tree(context)
        node = get_active_SNTI(node_tree)
        
        return (node and
            len(get_keyframes_of_SNTI(node_tree, node)) and
            node.image and node.image.source == "SEQUENCE")
    
    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        datapath = get_animkeydatapath(node.name)
        crv = tree.animation_data.action.fcurves.find(datapath)
        
        frame = int(context.scene.frame_current)
        key = int(crv.evaluate(frame))
        all_keys = [int(k.co.y) for k in crv.keyframe_points]
        if key not in all_keys:
            self.report({'ERROR'}, "The keyframes seem to be faulty. Check that their interpolation is set to CONSTANT. Also file this as a bug.")
            return {'CANCELLED'}

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
        dir, name, padding, ext = get_sequence_path_info(node.image.filepath)
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


class ANIM_OT_save_animtexture(Operator):
    """Saves the animated texture images."""
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
            def __init__(self,
                    image: Image,
                    node: Node,
                    keyframes: FCurveKeyframePoints) -> None:
                self.image = image
                self.node = node
                self.keyframes = keyframes
        images = []

        # store references to animtexture nodes and their keyframes
        if self.save_all:
            for mat in bpy.data.materials:
                if (    not mat.use_nodes or
                        not mat.node_tree.animation_data or
                        not mat.node_tree.animation_data.action):
                    continue
                for node in mat.node_tree.nodes:
                    keys = get_keyframes_of_SNTI(mat.node_tree, node)
                    if len(keys) > 0:
                        images.append(Img(node.image, node, keys))
        else:
            node_tree = get_active_node_tree(context)
            node = get_active_SNTI(node_tree)
            keys = get_keyframes_of_SNTI(node_tree, node)
            if len(keys) > 0:
                images.append(Img(node.image, node, keys))

        if not len(images):
            return {'FINISHED'}

        # create error list, setup image editor override
        errors = []
        image_editor, restore_image_editor = get_image_editor(context)
        override = context.copy()
        override['area'] = image_editor

        # iterate trough animtexture image node list and check for errors
        for img in images:
            if not img.image:
                errors.append(img.node.name + " - node has no texture selected.")
                continue 
            if img.image.source != "SEQUENCE":
                errors.append(img.image.name + " - is no image sequence.")
                continue
            
            # save image sequence
            i = img.image
            absfilepath = bpy.path.abspath(i.filepath)
            dir, name, padding, ext = get_sequence_path_info(absfilepath)
            if not os.path.exists(dir):
                errors.append(i.name)
                continue
            image_editor.spaces.active.image = i
            bpy.ops.image.save_sequence(override)

            # delete unused (left over) images
            if context.preferences.addons[__package__].preferences.reorganizeOnSave:
                clean_directory(img.keyframes, absfilepath)

        restore_image_editor()
        
        if len(errors):
            self.report({'WARNING'}, "Some files failed. Look in the console.")
            print("Failed to save animtexture image sequences:")
            for e in errors:
                print(e)
        return {'FINISHED'}


class ANIM_OT_import_animtexture(Operator):
    """Imports an image sequence as an animtexture sequence."""
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

        # open second file browser to set working directory
        bpy.ops.anim.animtexture_set_working_dir('INVOKE_DEFAULT', import_filepath = self.filepath, stop_at_gaps = self.stop_at_gaps, use_rel_path = self.use_rel_path)

        return {'FINISHED'}


class ANIM_OT_import_set_working_directory_animtexture(Operator):
    """Set Directory as working directory for imported texture."""
    bl_label = "Set Working Directory"
    bl_idname = "anim.animtexture_set_working_dir"
    bl_description = "Select a folder where working files of imported sequence stay"
    bl_options = {'REGISTER'}

    import_filepath: bpy.props.StringProperty(
        name="Sequence File Path",
        description="The File Path of the sequence that will be imported",
        options ={'HIDDEN'}
    )
    stop_at_gaps: bpy.props.BoolProperty(
        name="Stop at Gaps",
        options ={'HIDDEN'}
    )
    use_rel_path: bpy.props.BoolProperty(
        name="Make Relative",
        options ={'HIDDEN'}
    )
    directory: bpy.props.StringProperty(
        name="Import - Working directory Path",
        description="Working directory Path for importing sequence"
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):

        # get info of the import files in directory
        dir, name, padding, ext = get_sequence_path_info(self.import_filepath)
        all_files = os.listdir(dir)

        first_image_name = name + "0" * padding + ext
        
        # duplicate template if it exists, otherwise create new empty template
        template_name = get_template(first_image_name)
        if template_name in all_files:
            shutil.copyfile(
                bpy.path.abspath(os.path.join(dir, template_name)),
                bpy.path.abspath(os.path.join(self.directory, template_name))
                )
        else:
            tmp_img = bpy.data.images.load(self.import_filepath)
            buffer = [tmp_img.pixels[0] * 0] * len(tmp_img.pixels)
            tmp_img.pixels.foreach_set(buffer)
            tmp_img.filepath_raw = os.path.join(self.directory, template_name)
            tmp_img.save()
            bpy.data.images.remove(tmp_img)

        # create list of files that are part of the sequence and sort them    
        length = len(name) + padding + len(ext)
        files = [f for f in all_files
            if f.startswith(name)
                and len(f) == length
                and f[len(name):len(name) + padding].isdigit()
                and f.endswith(ext)]
        files.sort()

        # image a is compared to image b, if they are different
        # a new keyframe is added until the last image is reached
        index_start, index_end = len(name), len(name) + padding
        img_a = os.path.basename(self.import_filepath)
        start = files.index(img_a)
        keys = [int(img_a[index_start:index_end])]
        for i in range(start + 1, len(files)):
            img_b = files[i]
            files_are_same = filecompare(os.path.join(dir, img_a),
                                        os.path.join(dir, img_b))
            if not files_are_same:
                keys.append(int(img_b[index_start:index_end]))
                img_a = img_b

        # movecopy key images into new working directory        
        for i, key in enumerate(keys):
            shutil.copyfile(
                bpy.path.abspath(os.path.join(dir, name + str(key).zfill(padding) + ext)),
                bpy.path.abspath(os.path.join(self.directory, name + str(i).zfill(padding) + ext))
                )

        # create/overwrite keyframes
        tree = get_active_node_tree(context)
        node =  get_active_SNTI(tree)
        attach_action_if_needed(tree)
        datapath = get_animkeydatapath(node.name)
        crv = tree.animation_data.action.fcurves.find(datapath)
        if not crv:
            crv = tree.animation_data.action.fcurves.new(datapath)

        while len(crv.keyframe_points) > len(keys):
            crv.keyframe_points.remove(crv.keyframe_points[0], fast=True)
        if len(crv.keyframe_points) < len(keys):
            crv.keyframe_points.add(len(keys) - len(crv.keyframe_points))
        for i in range(len(keys)):
            pt = crv.keyframe_points[i]
            pt.co.x = keys[i]
            pt.co.y = i
            pt.interpolation = 'CONSTANT'
            
        # set new image path in node
        node.animtexturekeynext = keys[-1] + 1
        new_path = os.path.join(self.directory, name + "0" * padding + ext)
        if self.use_rel_path and bpy.data.is_saved:
            new_path = bpy.path.relpath(new_path)

        node.image = bpy.data.images.load(new_path)
        # if file format is open_exr it needs to be premultiplied
        if node.image.file_format == 'OPEN_EXR':
            node.image.alpha_mode = 'PREMUL'
        node.image.source = 'SEQUENCE'
        node.image_user.use_auto_refresh = True
        node.animtexturekey = int(crv.evaluate(context.scene.frame_current))

        update_node_color(node)

        msgbus_subscribe_to(node, tree)

        update_texture(context)
        return {'FINISHED'}


class ANIM_OT_import_single_animtexture(Operator):
    """Imports a single image into an animtexture sequence."""
    bl_label = "Import Single"
    bl_idname = "anim.animtexture_import_single"
    bl_description = "Import a single image into an animtexture sequence"
    bl_options = {'REGISTER'}

    import_filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
        description="Filepath for single image file"
    )

    @classmethod
    def poll(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        if not node: return False
        keys = get_keyframes_of_SNTI(tree, node)
        return len(keys) > 0 and node.image and node.image.source == "SEQUENCE"

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        dir, name, padding, ext1 = get_sequence_path_info(self.import_filepath)
        dir, name, padding, ext2 = get_sequence_path_info(node.image.filepath)

        # abort, if the import file has a different extension
        if ext1 != ext2:
            self.report({'ERROR'}, "Wrong file extension.")
            return {'CANCELLED'}
        
        # movecopy the import file
        shutil.copyfile(
            bpy.path.abspath(self.import_filepath),
            bpy.path.abspath(os.path.join(dir,
                name + str(node.animtexturekeynext).zfill(padding) + ext2))
            )

        # insert a new keyframe for the imported image file
        datapath = get_animkeydatapath(node.name)
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

    export_directory: bpy.props.StringProperty(
        subtype="DIR_PATH"
        )
    fill_gaps: bpy.props.BoolProperty(
        name="Fill Gaps",
        default=True
        )
    include_template: bpy.props.BoolProperty(
        name="Include Template",
        default=True,
        description="Include template in exported files"
        )

    def invoke(self, context, event):
        
        # assert, that an animtexture node with keys exists
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        if not node:
            return {'CANCELLED'}
        keys = get_keyframes_of_SNTI(tree, node)
        if len(keys) == 0 or not node.image or node.image.source != 'SEQUENCE':
            self.report({'ERROR'}, "Select a ImageTexture node with a texture sequence and animtexture keyframes.")
            return {'CANCELLED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)

        abspath = bpy.path.abspath(node.image.filepath)
        dir, name, padding, ext = get_sequence_path_info(abspath)

        keyframes = get_keyframes_of_SNTI(tree, node)
        keys = {int(k.co.x):int(k.co.y) for k in keyframes}

        missing_files = []
        failed_files = []

        # copy image files to export directory
        if self.fill_gaps:
            key = keys[min(keys.keys())]
            for frame in range(context.scene.frame_start, context.scene.frame_end + 1):
                if frame in keys:
                    key = keys[frame]
                path_in = os.path.join(dir,
                    name + str(key).zfill(padding) + ext)
                path_export = os.path.join(self.export_directory,
                    name + str(frame).zfill(padding) + ext)
                try:
                    shutil.copyfile(path_in, path_export)

                except OSError as e:
                    # if the image file is missing or failed to copy, add the image path to error list 
                    if not pathlib.Path(path_in).exists():
                        missing_files.append(path_in)
                    else:
                        failed_files.append(path_export)

        else:
            for frame in keys:
                key = keys[frame]
                path_in = os.path.join(dir,
                    name + str(key).zfill(padding) + ext)
                path_export = os.path.join(self.export_directory,
                    name +  str(frame).zfill(padding) + ext)
                try:
                    shutil.copyfile(path_in, path_export)

                except OSError as e:
                    # if the image file is missing or failed to copy, add the image path to error list 
                    if not pathlib.Path(path_in).exists():
                        missing_files.append(path_in)
                    else:
                        failed_files.append(path_export)

        # copy template file to export directory
        if self.include_template:
            template_name = get_template(os.path.basename(abspath))
            path_in = os.path.join(dir, template_name)
            path_export = os.path.join(self.export_directory, template_name)
            try:
                shutil.copyfile(path_in, path_export)

            except OSError as e:
                # if the template file is missing or failed to copy, add the template file path to error list 
                if not pathlib.Path(path_in).exists():
                    missing_files.append(path_in)
                else:
                    failed_files.append(path_export)

        if len(missing_files):
            print("Missing Files:")
            for i in missing_files:
                print(missing_files)
        if len(failed_files):
            print("Missing Files:")
            for i in missing_files:
                print(missing_files)

        return {'FINISHED'}


class ANIM_OT_openimage_animtexture(Operator):
    """Looks for an active ShaderNodeTextureImage with an image sequence and opens it in a UV Editor."""
    bl_label = "Open in Editor"
    bl_idname = "anim.animtexture_openimage"
    bl_description = "Show the active texture in the image editor."
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        return node and node.image and node.image.source == 'SEQUENCE'

    def execute(self, context):
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        
        # set image, duration and offset for all opened image editors    
        for area in context.screen.areas:
            if area.type in ['IMAGE_EDITOR', 'UV_EDITOR']:
                area.spaces.active.image = node.image
                area.spaces.active.image_user.frame_duration = node.image_user.frame_duration
                area.spaces.active.image_user.frame_offset = node.image_user.frame_offset
                return {'FINISHED'}

        self.report({'WARNING'}, "Open an ImageEditor or UV Editor first.")
        return {'CANCELLED'}


class ANIM_OT_insertdelete_animtexture(Operator):
    """
    This operator is called, when inserting a new animtexture sequence, but there are keyframes left on the node.
    Happens, when the image sequence data was detached.
    Opens a dialog, asking about deleting the keyframes.
    """
    bl_label = "No Image Sequence"
    bl_idname = "anim.animtexture_insertdelete"
    bl_description = "Open dialogue Box to ask whether or not to delete the keyframes"

    def execute(self, context):
        bpy.ops.anim.animtexture_insert('INVOKE_DEFAULT', delete_keyframes = True)
        return {'FINISHED'}

    def draw(self, context):
        self.layout.label(text="There are keyframes but no image sequence on this node. Delete the keyframes and create a new sequence?")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class ANIM_OT_insertmissingtemplate_animtexture(Operator):
    """"
    This Operator is called, when inserting a new keyframe, but the template file is missing.
    Opens a Dialog, asking about creating a new empty template file.
    New template has the dimensions and extension of the sequence.
    """

    bl_label = "Template File is missing"
    bl_idname = "anim.animtexture_insertmissingtemplate"
    bl_description = "Open dialogue Box to ask whether or not to create new template file."

    color: bpy.props.FloatVectorProperty(
        name="Background Color",
        description="Background Color for newly created images",
        subtype="COLOR",
        size = 4,
        default=(0.0, 0.0, 0.0, 0.0),
        min=0.0, max=1.0,
    )
    
    def execute(self, context):
        # create new empty template file
        tree = get_active_node_tree(context)
        node = get_active_SNTI(tree)
        template_path = get_template(node.image.filepath)

        # open the first image of the sequence, set color
        #  and save it as the template file
        tmp_img = bpy.data.images.load(node.image.filepath)

        buffer = list(self.color) * int(len(tmp_img.pixels) / 4)
        tmp_img.pixels.foreach_set(buffer)
        tmp_img.filepath_raw = template_path
        tmp_img.save()
        bpy.data.images.remove(tmp_img)

        bpy.ops.anim.animtexture_insert('INVOKE_DEFAULT')
        return {'FINISHED'}

    def draw(self, context):
        self.layout.prop(self, "bg_color", text="Background Color")
        self.layout.label(text="The template file is missing. Create a new template file?")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

def get_template(path: str) -> string:
    """Returns template name with extension."""
    if "." not in path:
        raise Exception("Path does not contain a file extension.")
    ext = "." + path.split(".")[-1]
    return path[:-len(ext)] + "template" + ext

def clean_directory(keyframe_points, absfilepath):
    """
        Removes all images except for the required images from the animtexture
        directory. Renames the remaining images consecutively (0, 1, 2, ...)
        and changes the keyframes_point values to match.
    """
    dir, name, padding, ext = get_sequence_path_info(absfilepath)
    key_values = [int(k.co.y) for k in keyframe_points]
    def create_path(i):
        return os.path.join(dir, name + str(i).zfill(padding) + ext)
    required_files = [name + str(y).zfill(padding) + ext for y in key_values]
    required_files.append(get_template(name + "0" * padding + ext))

    for file in os.listdir(dir):
        if file not in required_files:
            os.remove(os.path.join(dir, file))
            
    # reassigns keyframes to start from 0 consecutively 
    # [10, 12, 10, 20] => [0, 1, 0, 2]
    # with a lookup { 10=>0, 12=>1, 20=>2}
    transfer = dict()
    i = 0
    for k in keyframe_points:
        v = int(k.co.y)
        if v not in transfer:
            transfer[v] = i
            i += 1
        # change keyframe values to match new image numbers    
        k.co.y = transfer[v]
        if transfer[v] == v:
            del transfer[v]
    
    # Rename the image files to the new consecutive naming (stored in
    # the "transfer" lookup). Solve renaming conflicts by adding the
    # suffix "d" and the paths are stored in "duplicate". Remove all
    # "d"-suffices from file names.
    duplicate = []
    for orig_index in transfer:
        new_index = transfer[orig_index]
        a = create_path(orig_index)
        b = create_path(new_index)
        
        if new_index in transfer:
            b += "d"
            duplicate.append(b)
        os.rename(a, b)
    for d in duplicate:
        os.rename(d, d[:-1])
    return i


def get_image_editor(context: Context):
    """Returns an image_editor area and a callback to restore the layout."""

    if context.area.type =='IMAGE_EDITOR':
        # current area is IMAGE_EDITOR
        former_image = context.area.spaces.active.image
        def restore():
            context.area.spaces.active.image = former_image
        return context.area, restore
    
    # take the first available image editor
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
        # setup image editor and save previous gui state
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
    """Create AnimationData and a new Action for node tree if required."""
    if not tree.animation_data:
        tree.animation_data_create()
    if not tree.animation_data.action:
        suffix = 0
        while bpy.data.actions.find("AT" + str(suffix)) > 0:
            suffix += 1
        tree.animation_data.action = bpy.data.actions.new("AT" + str(suffix))


def get_active_node_tree(context) -> NodeTree:
    """Returns the active node tree which is selected via the gui. Returns null if no node tree is active."""
    ob = context.object
    if len(ob.material_slots) == 0: return None
    mat = ob.material_slots[ob.active_material_index].material
    if not mat or not mat.use_nodes: return None
    return mat.node_tree


def get_active_SNTI(tree:ShaderNodeTree) -> ShaderNodeTexImage:
    """Returns the active ShaderNodeTexImage of the node_tree. Does also accept None as an input."""
    if (    not tree
            or not tree.nodes.active
            or not tree.nodes.active.type == 'TEX_IMAGE'):
        return None
    return tree.nodes.active


def get_keyframes_of_SNTI(node_tree: NodeTree, node: Node) -> FCurveKeyframePoints:
    """Returns the keyframes of a SNTI (ShaderNodeTexImage). Does also accept None as an input."""
    if (    not node_tree
            or not node_tree.animation_data
            or not node_tree.animation_data.action
            or not node_tree.animation_data.action.fcurves):
        return []
    
    if not node or not node.type == 'TEX_IMAGE':
        return []

    datapath = get_animkeydatapath(node.name)
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
        update_texture_from_image_number(self, value, bpy.context.scene.frame_current)
        

def get_animkeydatapath(node_name:string)->string:
    return ('nodes["' + node_name + '"].animtexturekey')


def update_node_color(node:ShaderNodeTexImage):
    # change node color (greyish red(image incorrect or missing) or blue(active))
    if (    not node.image
            or node.image.source != "SEQUENCE" ):
        node.use_custom_color = True
        node.color = COLOR_ANIMTEXTURE_ERROR
    else:
        node.use_custom_color = True
        node.color = COLOR_ANIMTEXTURE_ACTIVE


def update_texture(context):
    """
    Update the displayed texture, based on the current frame and 
    the selected ShaderNodeTexImage
    """
    if not context.object:
        return
    tree = get_active_node_tree(context)
    node = get_active_SNTI(tree)

    #if node: update_node_color(node)

    if not tree.animation_data or not tree.animation_data.action:
        return

    datapath = get_animkeydatapath(node.name)
    crv = tree.animation_data.action.fcurves.find(datapath)

    if not crv:
        return

    # image_number_0 = int(crv.evaluate(frame))
    image_number = node.animtexturekey
    update_texture_from_image_number(node, image_number, context.scene.frame_current)


def update_texture_from_image_number(node: ShaderNodeTexImage, image_number, frame):
    """Update the displayed texture, based on the current frame."""
    frame_offset = image_number - frame
    duration = max(frame, 1)
    node.image_user.frame_duration = duration
    node.image_user.frame_offset = frame_offset
    
    update_display_texture_imageeditor(node.image, duration, frame_offset)


def update_display_texture_imageeditor(image, duration, offset):
    """Update image sequence in image editor."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'IMAGE_EDITOR':
                continue
            if area.spaces.active.image == image:
                area.spaces.active.image_user.frame_duration = duration
                area.spaces.active.image_user.frame_offset = offset
    

def path_exists(path):
    """Returns a Boolean, wether or not the path(argument) exists"""
    obj = pathlib.Path(path)
    return obj.exists()


def onion_create_nodes(node_tree: ShaderNodeTree):
    for name in ["ONION_PREV", "ONION_NEXT"]:
        if node_tree.nodes.find(name) == -1:
            node = node_tree.nodes.new('ShaderNodeTextureImage')
            node.name = name

def onion_get_nodes(node_tree: ShaderNodeTree):
    return node_tree.nodes.get("ONION_PREV"), node_tree.nodes.get("ONION_NEXT")

owners = []


def msgbus_callback(node, node_tree, owner):
    if get_keyframes_of_SNTI(node_tree,node):
       update_node_color(node)
    else:
        node.use_custom_color = False
        bpy.msgbus.clear_by_owner(owner)
        pass


def msgbus_subscribe_to(node, node_tree):
    owners.append(object())
    bpy.msgbus.subscribe_rna(
        key=node,
        owner=owners[-1],
        args=(node,node_tree,owners[-1]),
        notify=msgbus_callback,
    )

@persistent
def animtexture_framechange(scene):
    update_texture(bpy.context)
    

@persistent
def animtexture_loadpre(scene):
    """Checks if image files, that are connected to animtexture keyframes, are missing at startup.
    Shows a popup panel to display errors.
    Update textures."""
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

    update_texture(bpy.context)
    bpy.context.view_layer.update()


@persistent
def animtexture_loadpost(scene):
    """Set color of node,
    Attach message bus handler to
    check if a valid image sequence is present."""
    for mat in bpy.data.materials:
        if (    not mat.use_nodes or
                not mat.node_tree.animation_data or
                not mat.node_tree.animation_data.action):
            continue
        for node in mat.node_tree.nodes:
            keys = get_keyframes_of_SNTI(mat.node_tree, node)
            if len(keys) == 0:
                continue

            update_node_color(node)
            print(mat.node_tree, node)
            msgbus_subscribe_to(node, mat.node_tree)


@persistent
def animtexture_savewithfile(empty):
    """
    make sure the image sequence is saved
    """
    # TODO find more elegant solution
    context = bpy.context
    SAVE_ALL = context.preferences.addons[__package__].preferences.savewithfile == 'SAVE_ALL'
    bpy.ops.anim.animtexture_save(save_all=SAVE_ALL)

COLOR_ANIMTEXTURE_ACTIVE = (0.25, 0.35, 0.5) #greyish blue
COLOR_ANIMTEXTURE_ERROR = (0.35, 0.25, 0.25) #greyish red
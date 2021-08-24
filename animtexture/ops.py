import bpy
from bpy.types import (
    FCurve,
    Keyframe,
    PropertyGroup,
    Operator,
    ShaderNodeTexImage,
    )
from bpy.props import (
    IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )

"""Return an active ShaderNodeTexImage."""
def get_active_ShaderNodeTexImage(ob) -> ShaderNodeTexImage:
    if len(ob.material_slots) == 0: return
    mat = ob.material_slots[ob.active_material_index].material
    if not mat: return
    if not mat.use_nodes: return
    node = mat.node_tree.nodes.active
    if not node or not node.type == 'TEX_IMAGE': return
    return node



class ImgPropsTODO(PropertyGroup):
    particle_material: IntProperty(name = "id")

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
    location: StringProperty(
        name="Save Location",   
        description="Path to folder, where the images should be saved.",
        default="animtexture"
    )

"""Adds a new animtexture keyframe."""
class ANIM_OT_insert_animtexture(Operator):
    bl_label = "Insert"
    bl_idname = "anim.animtexture_insert"
    bl_description = "Insert a Keyframe"
    bl_options = {'REGISTER', 'UNDO'}
    # https://devtalk.blender.org/t/addon-operators-and-undo-support/4271/13

    def execute(self, context):
        ob = context.active_object
        node = get_active_ShaderNodeTexImage(ob)
        if not node:
            self.report({'ERROR'}, "Select an Image Texture node.")
            return
        
        # first registering
        def register(context, node, registered):
            if not registered:
                nextid = context.window_manager.animtexture_properties.nextid
                node.animtexture.id = nextid
                nextid += 1
                context.window_manager.animtexture_properties.nextid = nextid
            return True
        registered = False

        # TODO checks?
        mat = ob.material_slots[ob.active_material_index].material
        tree = mat.node_tree

        if node.animtexture.id == 0:
            registered = register(context, node, registered)
            
        # TODO request unique id for folder organization

        if not tree.animation_data:
            tree.animation_data_create()
        if not tree.animation_data.action:
            # mat.name + node.name should be a file-unique identifier
            # I'm scared, that we overwrite data-blocks otherwise. TODO
            tree.animation_data.action = bpy.data.actions.new(mat.name + node.name)

        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = tree.animation_data.action.fcurves.find(datapath)

        if not crv:
            registered = register(context, node, registered)
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
        ob = context.object
        if len(ob.material_slots) == 0: return False
        mat = ob.material_slots[ob.active_material_index].material
        if not mat or not mat.use_nodes: return False
        node = mat.node_tree.nodes.active
        if not node or not node.type == 'TEX_IMAGE': return False

        # TODO duplicate code
        datapath = 'nodes["' + node.name + '"].animtexturekey'
        if (    not mat.node_tree.animation_data
                or not mat.node_tree.animation_data.action
                or not mat.node_tree.animation_data.action.fcurves):
            return False
        
        crv = mat.node_tree.animation_data.action.fcurves.find(datapath)
        if not crv or not len(crv.keyframe_points):
            return False
        return True

    def execute(self, context):
        ob = context.active_object
        node = get_active_ShaderNodeTexImage(ob)
        if not node:
            self.report({'ERROR'}, "Select an Image Texture node.")
            return
        
        mat = ob.material_slots[ob.active_material_index].material
        tree = mat.node_tree
        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = tree.animation_data.action.fcurves.find(datapath)

        indices = set()
        for k in crv.keyframe_points:
            indices.add(int(k.co.y))

        for i in indices:
            name = "AT" + str(node.animtexture.id) + "_" + str(i)
            img = bpy.data.images.get(name)
            if not img:
                print("problem")
            else:
                path = "//animtexture/" + str(node.animtexture.id) + "/" + str(i).zfill(6) + ".png"
                img.filepath_raw = path
                img.file_format = 'PNG'
                img.save()

        return {'FINISHED'}


# switch the images on playback
def animtexture_framechangehandler(scene):
    update_displayed_texture(bpy.context)

def update_displayed_texture(context):
    ob = context.active_object
    # TODO speed?
    node = get_active_ShaderNodeTexImage(ob)
    mat = ob.material_slots[ob.active_material_index].material
    tree = mat.node_tree
    
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
    
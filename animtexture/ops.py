import bpy
from bpy.types import Keyframe

"""Return an active ShaderNodeTexImage."""
def get_active_ShaderNodeTexImage(ob):
    if len(ob.material_slots) == 0: return
    mat = ob.material_slots[ob.active_material_index].material
    if not mat: return
    if not mat.use_nodes: return
    node = mat.node_tree.nodes.active
    if not node or not node.type == 'TEX_IMAGE': return
    return node


"""Properties attached to the ShaderNodeTexImage."""
class AnimtextureProperties(bpy.types.PropertyGroup):
    dimensions: bpy.props.IntVectorProperty(
        name="Dimensions",
        size=2,
        description="x and y dimension of the images",
        default=(512, 512),
    )
    location: bpy.props.StringProperty(
        name="Save Location",
        description="Path to folder, where the images should be saved.",
        default="animtexture"
    )

"""Adds a new animtexture keyframe."""
class ANIM_OT_insert_keyframe_animtexture(bpy.types.Operator):
    bl_label = "Insert"
    bl_idname = "anim.insert_keyframe_animtexture"
    bl_description = "Insert a Keyframe"
    bl_options = {'REGISTER', 'UNDO'}
    # https://devtalk.blender.org/t/addon-operators-and-undo-support/4271/13

    def execute(self, context):
        ob = context.active_object
        node = get_active_ShaderNodeTexImage(ob)
        if not node:
            self.report({'ERROR'}, "Select an Image Texture node.")
            return
        

        # TODO checks?
        mat = ob.material_slots[ob.active_material_index].material
        tree = mat.node_tree

        # TODO request unique id for folder organization
        id = mat.name + "_" + node.name

        if not tree.animation_data:
            tree.animation_data_create()
        if not tree.animation_data.action:
            tree.animation_data.action = bpy.data.actions.new(id)

        datapath = 'nodes["' + node.name + '"].animtexturekey'
        crv = tree.animation_data.action.fcurves.find(datapath)

        if not crv:
            # create a new curve and insert new keyframes
            crv = tree.animation_data.action.fcurves.new(datapath)
        
        y = -1
        for pt in crv.keyframe_points:
            y = max(y, pt.co.y)
        y += 1
        
        img = bpy.data.images.new(id + str(int(y)), *node.animtexture.dimensions, alpha=True)
        
        # TODO save images


        node.animtexturekey = y
        tree.keyframe_insert(data_path=datapath)
        crv.keyframe_points[-1].interpolation = 'CONSTANT'

        # TODO update visual representation
        return {'FINISHED'}

   

# switch the images on playback
def animtexture_framechangehandler(scene):
    ob = bpy.context.active_object
    # TODO speed?
    node = get_active_ShaderNodeTexImage(ob)
    mat = ob.material_slots[ob.active_material_index].material
    tree = mat.node_tree
    
    if not tree.animation_data:
        return

    # TODO request unique id for folder organization
    id = mat.name + "_" + node.name
    datapath = 'nodes["' + node.name + '"].animtexturekey'
    crv = tree.animation_data.action.fcurves.find(datapath)

    if not crv:
        return

    image_number = int(crv.evaluate(scene.frame_current))
    
    name = id + str(image_number)
    print(name)
    img = bpy.data.images.get(name)

    # TODO check?
    node.image = img
    
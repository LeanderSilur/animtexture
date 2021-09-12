from . import ops
import bpy
from bpy.app import handlers

from bpy.types import (
        Operator,
        Panel,
        AddonPreferences,
        )
from bpy.props import (
        BoolProperty,
        EnumProperty,
        StringProperty,
        )

        
class VIEW3D_PT_animtexture(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animate"
    bl_label = 'AnimTexture'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        node_tree = ops.get_active_node_tree(context)
        tex = ops.get_active_SNTI(node_tree)

        layout = self.layout
        col = layout.column(align=True)
        row = col.row()
        row.operator("anim.animtexture_import", icon="IMPORT")
        row.operator("anim.animtexture_export", icon="EXPORT")
        row = col.row()
        op = row.operator("anim.animtexture_save", icon="FILE")
        op.save_all = False
        op = row.operator("anim.animtexture_save", text="Save All", icon="FILE")
        op.save_all = True
        
        
        if not tex:
            col.row().label(text="Select an Image Texture node.")
        else:
            col.row().label(text="")

        if tex:
            # DEBUGGING
            if False:
                row = col.row()
                row.prop(tex, "animtexturekey")
                row.prop(tex, "animtexturekeynext")

        row = col.row()
        row.operator("anim.animtexture_openimage", icon="IMAGE")
            
        row = col.row()
        row.operator("anim.animtexture_import_single", icon="KEY_HLT")

        row = col.row()
        row.operator("anim.animtexture_insert", icon="KEY_HLT")
        row.operator("anim.animtexture_duplicate", icon="KEY_HLT")


# Add-ons Preferences Update Panel
#
#    "name": "AnimAll",
#    "author": "Daniel Salazar <zanqdo@gmail.com>"

# Define Panel classes for updating
panels = [
        VIEW3D_PT_animtexture
        ]

from bpy.app.handlers import persistent
@persistent
def update_panel(self, context):
    message = "AnimTexture: Updating Panel locations has failed"
    try:
        for panel in panels:
            if "bl_rna" in panel.__dict__:
                bpy.utils.unregister_class(panel)

        for panel in panels:
            panel.bl_category = context.preferences.addons[__package__].preferences.category
            bpy.utils.register_class(panel)

    except Exception as e:
        print("\n[{}]\n{}\n\nError:\n{}".format(__package__, message, e))
        pass

@persistent
def update_checklinks(self, context):
    for h in handlers.load_post:
        if h.__name__ == "animtexture_checklinks":
            handlers.load_post.remove(h)
    if context.preferences.addons[__package__].preferences.checklinks:
        handlers.load_post.append(ops.animtexture_checklinks)

@persistent
def update_savewithfile(self, context):
    if context.preferences.addons[__package__].preferences.savewithfile != 'DONT_SAVE':
        handlers.save_pre.append(ops.animtexture_savewithfile)
    else:
        for h in handlers.save_pre:
            if h.__name__ == "animtexture_savewithfile":
                handlers.save_pre.remove(h)

class AnimtextureAddonPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    category: StringProperty(
        name="Tab Category",
        description="Choose a name for the category of the panel",
        default="Animate",
        update=update_panel
    )
    checklinks: BoolProperty(
        name="Check for Missing Files",
        description="Check for missing texture images when opening a file.",
        default=False,
        update=update_checklinks
    )
    savewithfile: EnumProperty(
        name="Save unsaved AnimTexture sequences when saving the file.",
        description="Give a warning, if we save a file with unsaved image sequences.",
        items = [
            ('DONT_SAVE', 'Don\'t Save', ''),
            ('SAVE_ACTIVE', 'Save Active', 'Save the active and selected texture node only.'),
            ('SAVE_ALL', 'Save All', 'Save all texture nodes of the whole file.')],
        default='SAVE_ALL',
        update=update_savewithfile
    )
    reorganizeOnSave: BoolProperty(
        name="Reorganize",
        description="Deleted unused image files and rename their indices when we save the animtexture sequence.",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column()

        col.label(text="Tab Category:")
        col.prop(self, "category", text="")
        col = row.column()
        row1 = col.row()
        row1.prop(self, "reorganizeOnSave")

        col.prop(self, "savewithfile")
        col.prop(self, "checklinks")


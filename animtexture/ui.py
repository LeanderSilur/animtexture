from . import ops
import bpy
AnimtextureProperties = ops.AnimtextureProperties
get_active_ShaderNodeTexImage = ops.get_active_ShaderNodeTexImage

from bpy.types import (
        Operator,
        Panel,
        AddonPreferences,
        )
from bpy.props import (
        BoolProperty,
        StringProperty,
        )

        
class VIEW3D_PT_animall(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animate"
    bl_label = 'AnimTexture'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        tex = get_active_ShaderNodeTexImage(context.active_object)

        if not tex:
            msg = "Select an Image Texture node."
        else:
            msg = ""

        layout = self.layout
        col = layout.column(align=True)
        row = col.row()
        row.label(text=msg)
        #col.separator()

        row.prop(tex.animtexture, "dimensions")
        row = col.row()
        row.prop(tex, "animtexturekey")
        row = col.row()
        row.operator("anim.insert_keyframe_animtexture", icon="KEY_HLT")



# Add-ons Preferences Update Panel
#
#    "name": "AnimAll",
#    "author": "Daniel Salazar <zanqdo@gmail.com>"

# Define Panel classes for updating
panels = [
        VIEW3D_PT_animall
        ]

def update_panel(self, context):
    message = "AnimAll: Updating Panel locations has failed"
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

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column()

        col.label(text="Tab Category:")
        col.prop(self, "category", text="")


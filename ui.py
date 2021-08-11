import bpy
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
        return context.active_object and context.active_object.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'}

    def draw(self, context):
        obj = context.active_object

        layout = self.layout
        col = layout.column(align=True)
        row = col.row()
        col.separator()

        #row.prop(animall_properties, "key_tilt")
        #row.operator("anim.insert_keyframe_animall", icon="KEY_HLT")


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

        



register_classes = [AnimtextureAddonPreferences]
def register():
    for cls in register_classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in register_classes:
        bpy.utils.unregister_class(cls)
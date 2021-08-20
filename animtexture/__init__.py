# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "animtexture",
    "author" : "Leander, Richard",
    "description" : "",
    "blender" : (2, 90, 0),
    "version" : (0, 0, 1),
    "location" : "",
    "warning" : "",
    "category" : "Generic",
    "support": "TESTING",
}

import bpy
from . import ops
from . import ui

#from . import auto_load
#auto_load.init()

register_classes = [
    ops.AnimtextureProperties,
    ops.ANIM_OT_insert_keyframe_animtexture,
    ui.AnimtextureAddonPreferences,
    ui.VIEW3D_PT_animall

    ]
def register():

    for cls in register_classes:
        bpy.utils.register_class(cls)
        
    bpy.types.ShaderNodeTexImage.animtexture = bpy.props.PointerProperty(type=ops.AnimtextureProperties)
    bpy.types.ShaderNodeTexImage.animtexturekey = bpy.props.IntProperty("key")

    
    # TODO is this really how you attach frame change handlers in addons?
    bpy.app.handlers.frame_change_pre.append(ops.animtexture_framechangehandler)


def unregister():
    # TODO same as with attaching, is this correct?
    frame_change_pre = bpy.app.handlers.frame_change_pre
    for h in frame_change_pre:
        if h.__name__ == "animtexture_framechangehandler":
            frame_change_pre.remove(h)

    bpy.props.RemoveProperty(bpy.types.ShaderNodeTexImage, attr="animtexture")
    bpy.props.RemoveProperty(bpy.types.ShaderNodeTexImage, attr="animtexturekey")
    del bpy.types.ShaderNodeTexImage.animtexture
    del bpy.types.ShaderNodeTexImage.animtexturekey

    for cls in register_classes:
        bpy.utils.unregister_class(cls)
        
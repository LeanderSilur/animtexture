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
    "description" : "",
    "author" : "Arun Leander, Richard",
    "blender" : (2, 92, 0),
    "version" : (0, 0, 1),
    "location" : "View3D > Properties",
    "warning" : "",
    "support": "TESTING",
    "doc_url": "https://github.com/LeanderSilur/animtexture/blob/main/README.md",
    "tracker_url": "https://github.com/LeanderSilur/animtexture/issues",
    "category" : "Animation",
}


import bpy
from bpy.types import (
    ShaderNodeTexImage,
    WindowManager,
    )
from bpy.utils import (
    register_class,
    unregister_class,
    )
from bpy.props import (
    RemoveProperty,
    PointerProperty,
    IntProperty,
    CollectionProperty
    )
from bpy.app import handlers
from . import ops
from . import ui

#from . import auto_load
#auto_load.init()

register_classes = [
    ops.ANIM_OT_insert_animtexture,
    ops.ANIM_OT_duplicate_animtexture,
    ops.ANIM_OT_save_animtexture,
    ops.ANIM_OT_export_animtexture,
    ui.AnimtextureAddonPreferences,
    ui.VIEW3D_PT_animtexture,
    ]


def register():
    for cls in register_classes:
        register_class(cls)
        
    # TODO Property in pointer property classes can be keyframed? Therefore
    # we have to keep animtexturekey separately?
    """Key to keep track of the image to be displayed."""
    ShaderNodeTexImage.animtexturekey = IntProperty("key")
    
    # TODO is this really how you attach frame change handlers in addons?
    handlers.frame_change_pre.append(ops.animtexture_updatetexturehandler)
    handlers.load_post.append(ops.animtexture_updatetexturehandler)

    if bpy.context.preferences.addons[__package__].preferences.savewithfile != 'DONT_SAVE':
        handlers.save_pre.append(ops.animtexture_savewithfile)
    if bpy.context.preferences.addons[__package__].preferences.checklinks:
        handlers.load_post.append(ops.animtexture_checklinks)

def unregister():
    # TODO same as with attaching, is this correct?
    for h in handlers.frame_change_pre:
        if h.__name__ in ["animtexture_updatetexturehandler",
                        "animtexture_loadposthandler",]:
            handlers.frame_change_pre.remove(h)
    for h in handlers.save_pre:
        if h.__name__ == "animtexture_savewithfile":
            handlers.save_pre.remove(h)
    for h in handlers.load_post:
        if h.__name__ in ["animtexture_checklinks",
                            "animtexture_updatetexturehandler"]:
            handlers.load_post.remove(h)

    RemoveProperty(ShaderNodeTexImage, attr="animtexturekey")
    del ShaderNodeTexImage.animtexturekey

    for cls in register_classes:
        unregister_class(cls)


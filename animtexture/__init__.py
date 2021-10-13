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
from .keymaps import setup_keymaps

#from . import auto_load
#auto_load.init()

register_classes = [
    ops.ANIM_OT_insert_animtexture,
    ops.ANIM_OT_duplicate_animtexture,
    ops.ANIM_OT_save_animtexture,
    ops.ANIM_OT_import_animtexture,
    ops.ANIM_OT_import_single_animtexture,
    ops.ANIM_OT_export_animtexture,
    ops.ANIM_OT_openimage_animtexture,
    ui.AnimtextureAddonPreferences,
    ui.VIEW3D_PT_animtexture,
    ]
addon_keymaps = []

def register():
    for cls in register_classes:
        register_class(cls)
        
    # TODO Property in pointer property classes can be keyframed? Therefore
    # we have to keep animtexturekey separately?
    """Key to keep track of the image to be displayed."""
    ShaderNodeTexImage.animtexturekey = IntProperty("key", default=0)
    ShaderNodeTexImage.animtexturekeynext = IntProperty("key", default=0)
    
    # TODO is this really how you attach frame change handlers in addons?
    handlers.frame_change_pre.append(ops.animtexture_updatetexturehandler)
    handlers.load_post.append(ops.animtexture_updatetexturehandler)
    handlers.load_post.append(ops.animtexture_startupcheckhandler)

    if bpy.context.preferences.addons[__package__].preferences.savewithfile != 'DONT_SAVE':
        handlers.save_pre.append(ops.animtexture_savewithfile)
    if bpy.context.preferences.addons[__package__].preferences.checklinks:
        handlers.load_post.append(ops.animtexture_checklinks)

    # keymaps
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        setup_keymaps(wm, addon_keymaps)

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    handlers = bpy.app.handlers

    def handlerdetach(handlertype):

        itemstodetach = [f for f in handlertype
            if f.__module__ == "animtexture.ops"]
        while itemstodetach:
            handlertype.remove(itemstodetach.pop())

    handlerdetach(handlers.frame_change_pre)
    handlerdetach(handlers.save_pre)
    handlerdetach(handlers.load_post)

    RemoveProperty(ShaderNodeTexImage, attr="animtexturekey")
    del ShaderNodeTexImage.animtexturekey

    for cls in register_classes:
        unregister_class(cls)


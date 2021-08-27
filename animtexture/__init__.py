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
    ops.AnimtextureProperties,
    ops.AnimtextureGlobalProperties,
    ops.ANIM_OT_insert_animtexture,
    ops.ANIM_OT_save_animtexture,
    ui.AnimtextureAddonPreferences,
    ui.VIEW3D_PT_animtexture,
    ]


def register():
    for cls in register_classes:
        register_class(cls)
        
    # TODO Property in pointer property classes can be keyframed? Therefore
    # we have to keep animtexturekey separately?
    ShaderNodeTexImage.animtexture = PointerProperty(type=ops.AnimtextureProperties)
    """Key to keep track of the image to be displayed."""
    ShaderNodeTexImage.animtexturekey = IntProperty("key")
    WindowManager.animtexture_properties = PointerProperty(type=ops.AnimtextureGlobalProperties)
    
    # TODO is this really how you attach frame change handlers in addons?
    handlers.frame_change_pre.append(ops.animtexture_framechangehandler)
    handlers.load_post.append(ops.animtexture_loadposthandler)
    
    # TODO 
    #handlers.load_pre.append(make sure the image sequence is saved)


def unregister():
    # TODO same as with attaching, is this correct?
    frame_change_pre = handlers.frame_change_pre
    for h in frame_change_pre:
        if h.__name__ in [
                "animtexture_framechangehandler",
                "animtexture_loadposthandler",]:
            frame_change_pre.remove(h)

    RemoveProperty(ShaderNodeTexImage, attr="animtexture")
    RemoveProperty(ShaderNodeTexImage, attr="animtexturekey")
    RemoveProperty(WindowManager, attr="animtexture_properties")
    del ShaderNodeTexImage.animtexture
    del ShaderNodeTexImage.animtexturekey
    del WindowManager.animtexture_properties

    for cls in register_classes:
        unregister_class(cls)


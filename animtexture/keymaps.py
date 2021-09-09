from typing import List
from bpy.types import WindowManager
from . import ops


def setup_keymaps(wm: WindowManager, addon_keymaps: List):
    # Ctrl Shift D ...      duplicate
    km = wm.keyconfigs.addon.keymaps.new(name='Image', space_type='IMAGE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_duplicate_animtexture.bl_idname,
        'D', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(ops.ANIM_OT_duplicate_animtexture.bl_idname,
        'D', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))
    
    km = wm.keyconfigs.addon.keymaps.new(name='NodeEditor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_duplicate_animtexture.bl_idname,
        'D', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))
    
    # Ctrl Shift A ...      insert (add)
    km = wm.keyconfigs.addon.keymaps.new(name='Image', space_type='IMAGE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_insert_animtexture.bl_idname,
        'A', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(ops.ANIM_OT_insert_animtexture.bl_idname,
        'A', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))
    
    km = wm.keyconfigs.addon.keymaps.new(name='NodeEditor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_insert_animtexture.bl_idname,
        'A', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    
    # Ctrl Shift E ...      export
    km = wm.keyconfigs.addon.keymaps.new(name='Image', space_type='IMAGE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_export_animtexture.bl_idname,
        'E', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(ops.ANIM_OT_export_animtexture.bl_idname,
        'E', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))
    
    km = wm.keyconfigs.addon.keymaps.new(name='NodeEditor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_export_animtexture.bl_idname,
        'E', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    
    # Ctrl Shift I ...      import
    km = wm.keyconfigs.addon.keymaps.new(name='Image', space_type='IMAGE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_import_animtexture.bl_idname,
        'I', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(ops.ANIM_OT_import_animtexture.bl_idname,
        'I', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))
    
    km = wm.keyconfigs.addon.keymaps.new(name='NodeEditor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(ops.ANIM_OT_import_animtexture.bl_idname,
        'I', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))
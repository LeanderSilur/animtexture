from importlib.resources import path
from re import T
import string
import bpy
from typing import List, Tuple
from bpy.app.handlers import persistent
from bpy.ops import image
from bpy.types import (
    ShaderNodeTree, Context, FCurve, Image, Keyframe, FCurveKeyframePoints, Node, NodeTree, PropertyGroup, Operator, ShaderNodeTexImage,
    )
from bpy.props import (
    BoolProperty, EnumProperty, IntProperty, IntVectorProperty, StringProperty, CollectionProperty
    )
import os
import shutil
import pathlib
from filecmp import cmp as filecompare

tree =  bpy.context.object.material_slots[0].material.node_tree
frame_current = int(bpy.context.scene.frame_current)

def onion_create_nodes(node_tree: ShaderNodeTree):
    for name in ["ONION_PREV", "ONION_NEXT"]:
        if node_tree.nodes.find(name) == -1:
            node = node_tree.nodes.new('ShaderNodeTexImage')
            node.name = name
            node.label = name

def onion_get_nodes(node_tree: ShaderNodeTree):
    return node_tree.nodes.get("ONION_PREV"), node_tree.nodes.get("ONION_NEXT")


def onion_update_textures(tree, frame_current):
    """
    Update the onion textures, based on the current frame and 
    the selected ShaderNodeTexImage.
    """
    
    img_num_prev, img_num_next = onion_get_img_numbers(tree, frame_current)

    for node in onion_get_nodes(tree):

        node.image = get_active_SNTI(tree).image

        if node.name == "ONION_PREV":
            update_texture_from_image_number(node, img_num_prev, frame_current)
            
        if node.name == "ONION_NEXT":
            update_texture_from_image_number(node, img_num_next, frame_current)

def onion_get_img_numbers(tree: ShaderNodeTree, frame):
    """Takes the current node tree.
    Returns the animtexture image numbers for both onion nodes"""

    # tree = get_active_node_tree(context)
    # frame = int(context.scene.frame_current)
    tree = tree
    frame = frame
    node = get_active_SNTI(tree)

    if not tree.animation_data or not tree.animation_data.action:
        return
    
    datapath = get_animkeydatapath(node.name)
    crv = tree.animation_data.action.fcurves.find(datapath)
    image_number_prev = int(crv.evaluate(frame-1))
    image_number_next = int(crv.evaluate(frame+1))

    return image_number_prev, image_number_next

#

def update_texture_from_image_number(node: ShaderNodeTexImage, image_number, frame):
    """Update the displayed texture, based on the current frame."""
    frame_offset = image_number - frame
    duration = max(frame, 1)
    node.image_user.frame_duration = duration
    node.image_user.frame_offset = frame_offset

def get_active_SNTI(tree:ShaderNodeTree) -> ShaderNodeTexImage:
    """Returns the active ShaderNodeTexImage of the node_tree. Does also accept None as an input."""
    if (    not tree
            or not tree.nodes.active
            or not tree.nodes.active.type == 'TEX_IMAGE'):
        return None
    return tree.nodes.active

def get_animkeydatapath(node_name:string)->string:
    return ('nodes["' + node_name + '"].animtexturekey')

onion_update_textures(tree, frame_current)

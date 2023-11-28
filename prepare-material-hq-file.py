"""
Sets the first material name of a .blend file to a static name
This allows us to find this material easily to append that blend file to the scene we want to render
"""

import bpy

material = bpy.data.materials[0]

material.name = "__render_importMaterial"

bpy.ops.wm.save_mainfile()
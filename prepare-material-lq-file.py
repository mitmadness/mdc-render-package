"""
Imports a GLTF file and saves the blend file at the same place
"""

import bpy
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1:] # get all args after "--"

gltfPath = argv[0]

bpy.ops.import_scene.gltf(filepath=gltfPath)
bpy.ops.wm.save_mainfile(filepath=gltfPath.replace('.gltf', '.blend'))

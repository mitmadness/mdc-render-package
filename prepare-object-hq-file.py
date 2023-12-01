"""
Join all meshes into one object and set its name to a static name
This allows us to find this object easily to append that blend file to the scene we want to render
"""

import bpy

# Join all meshes
meshes = list(filter(lambda obj: obj.type == 'MESH', bpy.data.objects))

if len(meshes) > 1:
    with bpy.context.temp_override(active_object=meshes[0], selected_editable_objects=meshes):
        bpy.ops.object.join()

# Find the joined mesh, move it to root, and apply the transform
joinedMesh = next(filter(lambda obj: obj.type == 'MESH', bpy.data.objects))

with bpy.context.temp_override(active_object=joinedMesh, selected_objects=[joinedMesh]):
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transforms_to_deltas(mode='ALL')

# Delete all non-meshes objects
nonMeshes = list(filter(lambda obj: obj.type != 'MESH', bpy.data.objects))

with bpy.context.temp_override(active_object=None, selected_objects=nonMeshes):
    bpy.ops.object.delete()

# Change the name of the joined mesh
joinedMesh.name = "__render_importObject"

# Save
bpy.ops.wm.save_mainfile()
import bpy

# Sets the first object name of a .blend file to a static name
# This allows us to find this object easily to append that blend file to the scene we want to render

object = next(filter(lambda obj: obj.parent == None, bpy.data.scenes[0].collection.objects));

object.name = "__render_importObject"

bpy.ops.wm.save_mainfile()
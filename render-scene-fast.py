# Ce script va s'occuper de faire juste le changement de caméra pour le rendu

import bpy
import idprop.types
import math
import mathutils
import re
import sys
import time
from os import path
from mathutils import Euler


startTime = time.time()

# on traite les arguments
argv = sys.argv
sceneEnvironment = argv[argv.index('--scene-environment') + 1]
isInterior = sceneEnvironment == 'interior'
isNightly = sceneEnvironment == 'nightly'

session = argv[argv.index('--session') + 1]
positionArg = argv[argv.index('--position') + 1]
orientationArg = argv[argv.index('--orientation') + 1]
cameraArg = argv[argv.index('--camera') + 1]
sunOrientationArg = argv[argv.index('--sun-orientation') + 1]

# Transforme le positionArgs en 3 flottant x y z
positionValues = positionArg.split(",")
positionX, positionY, positionZ = map(float, positionValues)
orientationValues = orientationArg.split(",")
orientationX, orientationY, orientationZ = map(float, orientationValues)
sunOrientationValues = sunOrientationArg.split(",")
sunOrientationX, sunOrientationY, sunOrientationZ = map(float, sunOrientationValues)

cameraValues = cameraArg.split(",")
cameraType = cameraValues[0]

# Supprime toutes les caméras existantes
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_by_type(type='CAMERA')
bpy.ops.object.delete()

bpy.ops.object.camera_add(location=(positionX, positionY, positionZ),
                          rotation=(orientationX, orientationY, orientationZ))

camera = bpy.context.active_object

print(f'Creating camera of {cameraType}')

# creation de la caméra en fonction du type
if cameraType == 'perspective':
    aspectRatio = cameraValues[1]
    fov = cameraValues[2]
    znear = cameraValues[3]
    zfar = cameraValues[4]

    camera.data.type = 'PERSP'
    camera.data.lens_unit = 'FOV'
    camera.data.sensor_fit = 'VERTICAL'
    camera.data.angle = float(fov)
    camera.data.clip_start = float(znear)
    camera.data.clip_end = float(zfar)
    bpy.context.scene.camera = camera
elif cameraType == 'panoramic':
    # Supprime toutes les caméras existantes
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='CAMERA')
    bpy.ops.object.delete()

    scene = bpy.context.scene
   # WIDTH, HEIGHT = 8192, 4096
    WIDTH, HEIGHT = 800, 400
    SAMPLES = 128

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = SAMPLES
    bpy.ops.object.camera_add(location=(positionX, positionY, positionZ),
                              rotation=(orientationX, orientationY, orientationZ))
    camera = bpy.context.active_object

    scene.camera = camera
    camera.data.type = 'PANO'

    try:
        camera.data.cycles.panorama_type = 'EQUIRECTANGULAR'
    except AttributeError:
        if hasattr(camera.data, "panorama_type"):
            camera.data.panorama_type = 'EQUIRECTANGULAR'

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
else:
    znear = cameraValues[1]
    zfar = cameraValues[2]
    xmag = cameraValues[3]
    ymag = cameraValues[4]

    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = float(xmag)
    camera.data.clip_start = float(znear)
    camera.data.clip_end = float(zfar)
    bpy.context.scene.camera = camera

# on change la position du soleil
sun = bpy.data.objects["__render_sun"]
sun.data.energy = 0
sun.rotation_euler = Euler((sunOrientationX, sunOrientationY, sunOrientationZ), 'XYZ')
sceneSunRotation = sunOrientationZ
hdrMapSunRotation = 0.86924

bpy.data.worlds["World"].node_tree.nodes["Mapping"].inputs[2].default_value[2] = hdrMapSunRotation - sceneSunRotation
print(f'--- render-scene-fast-import.py execution time: {time.time() - startTime} seconds ---')

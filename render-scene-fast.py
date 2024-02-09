# Ce script va s'occuper de faire juste le changement de caméra pour le rendu

import bpy
import idprop.types
import math
import mathutils
import re
import sys
import time
from os import path


startTime = time.time()

# on traite les arguments
argv = sys.argv
sceneEnvironment = argv[argv.index('--scene-environment') + 1]
isInterior = sceneEnvironment == 'interior'

session = argv[argv.index('--session') + 1]
positionArg = argv[argv.index('--position') + 1]
orientationArg = argv[argv.index('--orientation') + 1]
cameraArg = argv[argv.index('--camera') + 1]

# Transforme le positionArgs en 3 flottant x y z
positionValues = positionArg.split(",")
positionX, positionY, positionZ = map(float, positionValues)
orientationValues = orientationArg.split(",")
orientationX, orientationY, orientationZ = map(float, orientationValues)

cameraValues = cameraArg.split(",")
cameraType = cameraValues[0]

# Supprime toutes les caméras existantes
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_by_type(type='CAMERA')
bpy.ops.object.delete()

bpy.ops.object.camera_add(location=(positionX, positionY, positionZ),
                          rotation=(orientationX, orientationY, orientationZ))

camera = bpy.context.active_object

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

else:
    znear = cameraValues[1]
    zfar = cameraValues[2]
    xmag = cameraValues[3]
    ymag = cameraValues[4]

    camera.data.type = 'ORTHO'
    camera.data.magnification = xmag

bpy.context.scene.camera = camera


print(f'--- render-scene-fast-import.py execution time: {time.time() - startTime} seconds ---')

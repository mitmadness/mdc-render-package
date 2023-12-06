@echo off

if %1% == render-interior (
    blender -b render-scene-interior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device OPTIX --scene-environment interior
)
if %1% == render-exterior (
    blender -b render-scene-exterior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device OPTIX --scene-environment exterior
)
if %1% == prepare-material-hq-file (
    blender -b %2% --python prepare-material-hq-file.py
)
if %1% == prepare-material-lq-file (
    blender -b empty.blend --python prepare-material-lq-file.py -- %2%
)
if %1% == prepare-object-hq-file (
    blender -b %2% --python prepare-object-hq-file.py
)
if %1% == prepare-object-lq-file (
    blender -b empty.blend --python prepare-object-lq-file.py -- %2%
)
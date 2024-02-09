@echo off

if %1 == render-interior (
    blender -b render-scene-interior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device HIP --scene-environment interior --session %2
)
if %1 == render-exterior (
    blender -b render-scene-exterior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device HIP --scene-environment exterior --session %2
)
if %1 == render-fast-interior (
    blender -b cache\scene-interior-%2.blend --python render-scene-fast.py -o //Result#### -x 1 -f 1 -- --cycles-device HIP --scene-environment interior --session %2 --position %3 --orientation %4 --camera %5
)
if %1 == render-fast-exterior (
    blender -b cache\scene-exterior-%2.blend --python render-scene-fast.py -o //Result#### -x 1 -f 1 -- --cycles-device HIP --scene-environment exterior --session %2 --position %3 --orientation %4 --camera %5
)
if %1 == prepare-material-hq-file (
    blender -b %2 --python prepare-material-hq-file.py
)
if %1 == prepare-material-lq-file (
    blender -b empty.blend --python prepare-material-lq-file.py -- %2
)
if %1 == prepare-object-hq-file (
    blender -b %2 --python prepare-object-hq-file.py
)
if %1 == prepare-object-lq-file (
    blender -b empty.blend --python prepare-object-lq-file.py -- %2
)
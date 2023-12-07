case $1 in
    "render-interior")
        blender -b render-scene-interior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device OPTIX --scene-environment interior
        ;;
    "render-exterior")
        blender -b render-scene-exterior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device OPTIX --scene-environment exterior
        ;;
    "prepare-material-hq-file")
        blender -b $2 --python prepare-material-hq-file.py
        ;;
    "prepare-material-lq-file")
        blender -b empty.blend --python prepare-material-lq-file.py -- $2
        ;;
    "prepare-object-hq-file")
        blender -b $2 --python prepare-object-hq-file.py
        ;;
    "prepare-object-lq-file")
        blender -b empty.blend --python prepare-object-lq-file.py -- $2
        ;;
esac
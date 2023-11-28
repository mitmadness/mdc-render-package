case $1 in
    "render-interior")
        blender -b render-scene-interior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device OPTIX
        ;;
    "render-exterior")
        blender -b render-scene-exterior.blend --python render-scene-import.py -o //Result#### -x 1 -f 1 -- --cycles-device OPTIX
        ;;
    "prepare-material-hq-file")
        blender -b $args[1] --python prepare-material-hq-file.py
        ;;
    "prepare-material-lq-file")
        blender -b empty.blend --python prepare-material-lq-file.py -- $args[1]
        ;;
    "prepare-object-hq-file")
        blender -b $args[1] --python prepare-object-hq-file.py
        ;;
    "prepare-object-lq-file")
        blender -b empty.blend --python prepare-object-lq-file.py -- $args[1]
        ;;
esac
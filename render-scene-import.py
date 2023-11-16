"""Launched when rendering a scene

Imports the scene and sets everything as needed for the render
"""

import bpy
import idprop.types
import re
import sys
from os import path

## Import the GLTF scene exported from mDC Designer

sceneFilePath = path.join(path.dirname(bpy.data.filepath), 'myDecoCloud_scene', 'myDecoCloud_scene.gltf')

bpy.ops.import_scene.gltf(filepath=sceneFilePath)


## Set the active camera

bpy.context.scene.camera = bpy.data.objects["__render_camera"]


## Import and place assets, potentially their high quality versions stored in .blend files

assetsPath = path.join(path.dirname(bpy.data.filepath), 'assets')
importedMaterials = {}

def importObjectRenderAsset(obj, renderAssetRef):
    print(f'Import object {obj.name} RenderAsset')

    renderAssetFileName = renderAssetRef["assetBundleHash"]

    ## Import the .blend or .gltf scene
    blendFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}.blend')
    gltfFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}.gltf')

    if path.exists(blendFilePath):
        print(f'Import .blend {blendFilePath}')

        objectName = '__render_importObject'

        bpy.ops.wm.append(
            filepath=path.join(blendFilePath, 'Object', objectName),
            directory=path.join(blendFilePath, 'Object'),
            filename=objectName)

    elif path.exists(gltfFilePath):
        print(f'Import GLTF {gltfFilePath}')

        bpy.ops.import_scene.gltf(filepath=gltfFilePath)

    else:
        print(f'Did not find .blend or .gltf file for {renderAssetFileName}', file=sys.stderr)
        return
        
    ## Get the imported object and change its name
    importedObject = bpy.data.objects['__render_importObject']

    importedObject.name += '-' + renderAssetFileName
    
    ## Set the imported object parent (and move it there)
    importedObject.parent = obj

def importMaterialRenderAsset(objects, matName, renderAssetRef):
    print(f'Import material {matName} RenderAsset')
    
    renderAssetFileName = renderAssetRef["assetBundleHash"]

    ## Use a simple dict cache to see if we already imported this material
    if renderAssetFileName in importedMaterials:
        importedMaterial = importedMaterials[renderAssetFileName]
    
    else:
        ## Import the .blend or .gltf scene
        blendFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}.blend')
        gltfFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}.gltf')

        if path.exists(blendFilePath):
            print(f'Import .blend {blendFilePath}')

            materialName = '__render_importMaterial'

            bpy.ops.wm.append(
                filepath=path.join(blendFilePath, 'Material', materialName),
                directory=path.join(blendFilePath, 'Material'),
                filename=materialName)

        elif path.exists(gltfFilePath):
            print(f'Import GLTF {gltfFilePath}')

            bpy.ops.import_scene.gltf(filepath=gltfFilePath)

        else:
            print(f'Did not find .blend or .gltf file for {renderAssetFileName}', file=sys.stderr)
            return

        
        ## Get the imported object and change its name
        importedMaterial = bpy.data.materials['__render_importMaterial']

        importedMaterial.name += '-' + renderAssetFileName

        ## Cache it
        importedMaterials[renderAssetFileName] = importedMaterial

    ## Replace the material in all slots of meshes
    for obj in objects:
        if obj.type != 'MESH': continue
    
        for slot in obj.material_slots:
            if re.search(f'^{re.escape(matName)}(\.\d+)?$', slot.material.name) is not None:
                slot.material = importedMaterial

    ## Delete the dummy that were used in the files to keep the material, if they exist
    dummy = bpy.data.objects.get('__render_dummy')

    if dummy is not None:
        with bpy.context.temp_override(selected_objects=[dummy]):
            bpy.ops.object.delete()

for obj in bpy.context.scene.objects:
    if 'assetBundleHash' in obj:
        importObjectRenderAsset(obj, obj)

    if 'materialsMap' in obj and isinstance(obj['materialsMap'], idprop.types.IDPropertyGroup):
        for (materialName, renderAssetRef) in obj['materialsMap'].items():
            importMaterialRenderAsset([obj, *obj.children_recursive], materialName, renderAssetRef)

for mat in bpy.data.materials:
    if 'assetBundleHash' in mat:
        importMaterialRenderAsset(bpy.context.scene.objects, mat.name, mat)


## Replace windows glass materials

windowsGlassMaterial = bpy.data.materials["__render_MAT_Vitre"]

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH': continue
        
    for slot in obj.material_slots:
        if slot.material.name.startswith('MAT_Vitre_01'):
            print(f'Replace {slot.material.name} material in {obj.name} to {windowsGlassMaterial.name}')
            
            slot.material = windowsGlassMaterial

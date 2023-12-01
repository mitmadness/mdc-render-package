"""Launched when rendering a scene

Imports the scene and sets everything as needed for the render
"""

import bpy
import idprop.types
import re
import sys
import time
from os import path

startTime = time.time()

## Import the GLTF scene exported from mDC Designer

sceneFilePath = path.join(path.dirname(bpy.data.filepath), 'myDecoCloud_scene', 'myDecoCloud_scene.gltf')

bpy.ops.import_scene.gltf(filepath=sceneFilePath)


## Set the active camera

bpy.context.scene.camera = bpy.data.objects["__render_camera"]


## Import and place assets, potentially their high quality versions stored in .blend files

assetsPath = path.join(path.dirname(bpy.data.filepath), 'assets')
importedObjects = {}
importedObjectsWorldMatrixes = {}
importedMaterials = {}

def importObjectRenderAsset(obj, renderAssetRef):
    print(f'Import object {obj.name} RenderAsset')

    renderAssetFileName = renderAssetRef["assetBundleHash"]

    ## Use a simple dict cache to see if we already imported this object
    if renderAssetFileName in importedObjects:
        cachedObject = importedObjects[renderAssetFileName]

        # Duplicate it
        with bpy.context.temp_override(selected_objects=[cachedObject]):
            bpy.ops.object.duplicate(linked=True)

            importedObject = bpy.context.selected_objects[0]

    else:
        ## Import the HQ or LQ .blend scene
        hqFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}-hq.blend')
        lqFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}.blend')

        if path.exists(hqFilePath):
            print(f'Import HQ file {hqFilePath}')
            importedFilePath = hqFilePath

        elif path.exists(lqFilePath):
            print(f'Import LQ file {lqFilePath}')
            importedFilePath = lqFilePath

        else:
            print(f'Did not find file to import for {renderAssetFileName}', file=sys.stderr)
            return

        objectName = '__render_importObject'

        bpy.ops.wm.append(
            filepath=path.join(importedFilePath, 'Object', objectName),
            directory=path.join(importedFilePath, 'Object'),
            filename=objectName)

        ## Get the imported object and change its name
        importedObject = bpy.data.objects['__render_importObject']
        
        importedObject.name += '-' + renderAssetFileName

        ## Cache it
        importedObjects[renderAssetFileName] = importedObject

        ## Store its original matrix values to be able to move it and its duplicate correctly
        importedObjectsWorldMatrixes[renderAssetFileName] = importedObject.matrix_world.copy()
    
    ## Move the imported object where the null is
    ## Don't set its parent, because it takes a long time
    importedObject.matrix_world = obj.matrix_world @ importedObjectsWorldMatrixes[renderAssetFileName]

    ## Return the importedObject so that it can be used for material map
    return importedObject

def importMaterialRenderAsset(objects, matName, renderAssetRef):
    print(f'Import material {matName} RenderAsset')
    
    renderAssetFileName = renderAssetRef["assetBundleHash"]

    ## Use a simple dict cache to see if we already imported this material
    if renderAssetFileName in importedMaterials:
        importedMaterial = importedMaterials[renderAssetFileName]
    
    else:
        ## Import the HQ or LQ .blend scene
        hqFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}-hq.blend')
        lqFilePath = path.join(assetsPath, renderAssetFileName, f'{renderAssetFileName}.blend')

        if path.exists(hqFilePath):
            print(f'Import HQ file {hqFilePath}')
            importedFilePath = hqFilePath

        elif path.exists(lqFilePath):
            print(f'Import LQ file {lqFilePath}')
            importedFilePath = lqFilePath

        else:
            print(f'Did not find file to import for {renderAssetFileName}', file=sys.stderr)
            return

        materialName = '__render_importMaterial'

        bpy.ops.wm.append(
            filepath=path.join(importedFilePath, 'Material', materialName),
            directory=path.join(importedFilePath, 'Material'),
            filename=materialName)
        
        ## Get the imported object and change its name
        importedMaterial = bpy.data.materials['__render_importMaterial']

        importedMaterial.name += '-' + renderAssetFileName

        ## Cache it
        importedMaterials[renderAssetFileName] = importedMaterial

    # Replace the material in all slots of meshes
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

importedObjectsCount = 0
importedMaterialsCount = 0

for obj in bpy.context.scene.objects:
    importedObject = None

    if 'assetBundleHash' in obj:
        importedObject = importObjectRenderAsset(obj, obj)
        importedObjectsCount += 1

    if 'materialsMap' in obj and isinstance(obj['materialsMap'], idprop.types.IDPropertyGroup):
        appliedObject = importedObject or obj
        appliedObjects = [appliedObject, *appliedObject.children_recursive]

        for (materialName, renderAssetRef) in obj['materialsMap'].items():
            importMaterialRenderAsset(appliedObjects, materialName, renderAssetRef)
            importedMaterialsCount += 1

for mat in bpy.data.materials:
    if 'assetBundleHash' in mat:
        importMaterialRenderAsset(bpy.context.scene.objects, mat.name, mat)
        importedMaterialsCount += 1


## Replace windows glass materials

windowsGlassMaterial = bpy.data.materials["__render_MAT_Vitre"]

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH': continue
        
    for slot in obj.material_slots:
        if slot.material.name.startswith('MAT_Vitre_01'):
            print(f'Replace {slot.material.name} material in {obj.name} to {windowsGlassMaterial.name}')
            
            slot.material = windowsGlassMaterial

print(f'--- render-scene-import.py execution time: {time.time() - startTime} seconds ---')
print(f'importedObjectsCount: {importedObjectsCount}')
print(f'importedMaterialsCount: {importedMaterialsCount}')
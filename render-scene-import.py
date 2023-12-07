"""Launched when rendering a scene

Imports the scene and sets everything as needed for the render
"""

import bpy
import idprop.types
import math
import mathutils
import re
import sys
import time
from os import path

startTime = time.time()

argv = sys.argv
sceneEnvironment = argv[argv.index('--scene-environment') + 1]
isInterior = sceneEnvironment == 'interior'

## Import the GLTF scene exported from mDC Designer

sceneFilePath = path.join(path.dirname(bpy.data.filepath), 'myDecoCloud_scene', 'myDecoCloud_scene.gltf')

bpy.ops.import_scene.gltf(filepath=sceneFilePath)


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
        importedObject = cachedObject.copy()
        importedObject.data = cachedObject.data.copy()
        bpy.context.collection.objects.link(importedObject)

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

        ## Cache a copy of it. We can't cache it directly because if we swap materials on it,
        ## duplicates of it will not be able to swap material
        importedObjectCopy = importedObject.copy()
        importedObjectCopy.data = importedObject.data.copy()
        importedObjects[renderAssetFileName] = importedObjectCopy

        ## Store its original matrix values to be able to move it and its duplicate correctly
        importedObjectsWorldMatrixes[renderAssetFileName] = importedObject.matrix_world.copy()
    
    ## Move the imported object where the null is
    ## Don't set its parent, because it takes a long time
    importedObject.matrix_world = obj.matrix_world @ importedObjectsWorldMatrixes[renderAssetFileName]

    ## Apply the weights of the blendshape
    if 'weights' in obj and isinstance(obj['weights'], idprop.types.IDPropertyArray):
        for weightIndex, weight in enumerate(obj['weights']):
            importedObject.data.shape_keys.key_blocks[weightIndex + 1].value = weight

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
        bpy.data.objects.remove(dummy, do_unlink=True)

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


## Add light areas / portals to all openings

for obj in bpy.context.scene.objects:
    if 'opening' in obj and isinstance(obj['opening'], idprop.types.IDPropertyArray):
        print(f'Add area light to opening {obj.name}')
        
        (openingSizeX, openingSizeY, openingSizeZ) = obj['opening'].to_list()
        
        lightData = bpy.data.lights.new(name='Area Light Data', type='AREA')

        energyBase = 15 if isInterior else 2.5 # W / m^2
        lightData.energy = energyBase * openingSizeX * openingSizeY
        
        lightData.shape = 'RECTANGLE'
        lightData.size = openingSizeX * 0.95
        lightData.size_y = openingSizeY * 0.95
        lightData.color = (1.00017, 0.947265, 0.846812) # FFF9ED, color of the sun in our current HDRI

        light = bpy.data.objects.new(name='Area Light', object_data=lightData)
        light.visible_camera = False
        light.visible_glossy = False
        light.visible_transmission = False
        light.visible_volume_scatter = False

        # We need to apply a rotation to the light so that it is oriented the same way the openings nulls (obj) are
        fixRotationMatrix = mathutils.Euler((math.radians(-90), math.radians(180), math.radians(90))).to_matrix().to_4x4()

        # And we need to translate the light so that it is in the center of the opening (the null is at the bottom left of it)
        moveToCenterMatrix = mathutils.Matrix.Translation((openingSizeX / 2, openingSizeY / 2, -openingSizeZ / 2))
        
        light.matrix_world = obj.matrix_world @ fixRotationMatrix @ moveToCenterMatrix

        bpy.context.collection.objects.link(light)
        
        ## Add the light portal, only in interior
        if isInterior:
            portal = light.copy()
            portal.data = lightData.copy()
            portal.data.cycles.is_portal = True
            portal.name = 'Area Light Portal'

            bpy.context.collection.objects.link(portal)


## Set the active camera

bpy.context.scene.camera = bpy.data.objects["__render_camera"]


print(f'--- render-scene-import.py execution time: {time.time() - startTime} seconds ---')
print(f'importedObjectsCount: {importedObjectsCount}')
print(f'importedMaterialsCount: {importedMaterialsCount}')
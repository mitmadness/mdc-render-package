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
import numpy as np
from os import path
from mathutils import Matrix, Vector

startTime = time.time()

argv = sys.argv

#argv = ['--scene-environment', 'interior', '--position', '-1.570920,-0.760569,1', '--orientation', '1.570797,7.4503,-1.0471', '--camera', 'perspective,1.7777,1.09955,0.1,11.395', '--session', 'DEBUGGING']
sceneEnvironment = argv[argv.index('--scene-environment') + 1]
isInterior = sceneEnvironment == 'interior'
positionArg = argv[argv.index('--position') + 1]
orientationArg = argv[argv.index('--orientation') + 1]
cameraArg = argv[argv.index('--camera') + 1]

session = argv[argv.index('--session') + 1]
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

def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    else:
        return math.pow((c + 0.055) / 1.055, 2.4)
    
# Fonction de processing des matériaux.

# Cette méthode va s'occuper d'application la rotation custom d'un revêtement de sol
def applyRotation(objects, rotation):
    print(f'Apply rotation to', object.__name__)

    pivot = Vector((0.5,0.5))
    angle = math.radians(-rotation)

    for obj in objects:
        uvlayer  = obj.data.uv_layers.active

        p = 1 #obj.dimensions.y / obj.dimensions.x

        R = Matrix((
            (np.cos(angle), np.sin(angle) / p),
            (-p * np.sin(angle), np.cos(angle))
        ))

        uvs = np.empty(2*len(obj.data.loops))
        uvlayer.data.foreach_get("uv", uvs)

        uvs = np.dot(uvs.reshape((-1,2)) - pivot, R) + pivot
        uvlayer.data.foreach_set("uv", uvs.ravel())

        obj.data.update()

def applyOldRotation(objects, rotation):
    print(f'Apply rotation to', object.__name__)

    for obj in objects:
        if obj.type != 'MESH':
            continue

        for slot in obj.material_slots:
            new_material = slot.material.copy()
            tree = new_material.node_tree
            principled = tree.nodes['Principled BSDF']
            slot.material = new_material

            # on va créer les nouveaux noeuds
            texture_map = tree.nodes.new('ShaderNodeTexCoord')
            mapping = tree.nodes.new('ShaderNodeMapping')

            mapping.inputs['Rotation'].default_value[2] = math.radians(rotation)

            base_color = tree.nodes['Image Texture']
            metallic = tree.nodes['Image Texture.001']
            normal = tree.nodes['Image Texture.002']

            tree.links.new(texture_map.outputs['Generated'], mapping.inputs['Vector'])
            tree.links.new(mapping.outputs['Vector'], base_color.inputs['Vector'] )
            tree.links.new(mapping.outputs['Vector'], metallic.inputs['Vector'])
            tree.links.new(mapping.outputs['Vector'], normal.inputs['Vector'])


# Cette méthode sert à appliquer une palette, on est obligé de filer la materialMap car si c'était un matériaux
# customisable, il s'est fait importer la face dans un nom qui n'a plus rien à voir avec son nom original
# du coup on doit pouvoir accéder au hash du bundle pour pouvoir retrouver le matériaux et le dupliquer.
def applyColorMaterial(objects, matName, colorToApply, materialsMap):
    print(f'Apply color to {matName}')

    # on commence par regarder si le matériau cible de la palette n'est pas déjà customiser
    # par un autre matéfiau, et dans ce cas
    full_name = "NOT IMPORTED"

    print("Trying to get " + matName)
    for (localName, localRenderAsset) in materialsMap.items():
        if localName == matName:
            full_name = "__render_importMaterial-" + localRenderAsset["assetBundleHash"]
            full_name = full_name[:59] # Superbe contrainte en dur, blender tronque les identifiants

    for obj in objects:
        if obj.type != 'MESH':
            continue

        for slot in obj.material_slots:
            if re.search(f'^{re.escape(matName)}(\.\d+)?$', slot.material.name) is not None\
                    or slot.material.name[:len(full_name)] == full_name[:len(full_name)]:
                new_material = slot.material.copy()
                tree = new_material.node_tree
                principled = tree.nodes['Principled BSDF']
                slot.material = new_material
            else:
                continue

            base_color = principled.inputs['Base Color']
            new_color = (srgb_to_linear(colorToApply['r']), srgb_to_linear(colorToApply['g']), srgb_to_linear(colorToApply['b']), colorToApply['a'])

            # On a à présent plusieurs cas de figure, si il s'agit d'une base color simple, s'il s'agit d'un color
            # mix en source, ou alors d'une simple texture (cas le plus chiant)
            if len(base_color.links) == 0:
                # cas simple en gros, on a pas de lien complexe, c'est une couleur simple
                base_color.default_value = new_color
            else:
                link = base_color.links[0]
                if link.from_node.name == 'Mix':
                    # Cas où on a un mixer de couleur
                    mix = link.from_node
                    mix.inputs['B'].default_value = new_color
                else:
                    if link.from_node.name == 'Image Texture':
                        # cas où la couleur de base provient d'une texture, il faut insérer notre mix à la volée
                        image_node = link.from_node
                        new_node = tree.nodes.new('ShaderNodeMix')
                        new_node.name = 'Mix'
                        new_node.blend_type = 'MULTIPLY'
                        new_node.data_type = 'RGBA'
                        new_node.clamp_result = False
                        new_node.clamp_factor = True
                        new_node.inputs['B'].default_value = new_color
                        new_node.inputs['Factor'].default_value = 1.0

                        tree.links.new(new_node.outputs['Result'], link.to_node.inputs['Base Color'])
                        tree.links.new(image_node.outputs['Color'], new_node.inputs['A'])



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
importedColorsCount = 0

# On commence par traiter l'herbe. On fait ça avant la substitution de matériaux car
# cette dernière risque de faire disparaitre des informations

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH': continue

# On s'occupe de tous les modificateurs de matériaux
for obj in bpy.context.scene.objects:
    importedObject = None

    if 'assetBundleHash' in obj:
        importedObject = importObjectRenderAsset(obj, obj)
        importedObjectsCount += 1

    if 'materialsMap' in obj and isinstance(obj['materialsMap'], idprop.types.IDPropertyGroup)\
            or 'palettesMap' in obj and isinstance(obj['palettesMap'], idprop.types.IDPropertyGroup):

        appliedObject = importedObject or obj
        appliedObjects = [appliedObject, *appliedObject.children_recursive]

        for (materialName, renderAssetRef) in obj['materialsMap'].items():
            importMaterialRenderAsset(appliedObjects, materialName, renderAssetRef)
            importedMaterialsCount += 1

        if 'palettesMap' in obj:
            for (materialName, color) in obj['palettesMap'].items():
                applyColorMaterial(appliedObjects, materialName, color, obj['materialsMap'])
                importedColorsCount += 1


for mat in bpy.data.materials:
    if 'assetBundleHash' in mat:
        importMaterialRenderAsset(bpy.context.scene.objects, mat.name, mat)
        importedMaterialsCount += 1


## Replace windows glass materials and grass
windowsGlassMaterial = bpy.data.materials["__render_MAT_Vitre"]

## on s'occupe de générer l'herbe
grassNodeModifier = bpy.data.node_groups['ScatterGrassAndFlowers']

for obj in bpy.context.scene.objects:
    if obj.type != 'MESH': continue

    # On process toutes les surfaces qui sont indiqués comme du jardin
    # Puis on va vérifier que la texture appliquée à cette surface est bien
    # une surface "herbeuse". Dans ce cas on va rajouter un modificateur de node
    # qui génèrera la géométrie de l'herbe.
    if 'grassGeneration' in obj:
        match obj['grassGeneration']:
            case 1:
                print(f'Add grass modifier type 1 to {obj.name}')
                modifier = obj.modifiers.new("Grass", "NODES")
                modifier.node_group = grassNodeModifier

    # Les vitres
    for slot in obj.material_slots:
        if slot.material.name.startswith('MAT_Vitre_01'):
            print(f'Replace {slot.material.name} material in {obj.name} to {windowsGlassMaterial.name}')
            
            slot.material = windowsGlassMaterial

# Traitement des rotations de surface
for obj in bpy.context.scene.objects:
    if 'rotation' in obj:
        appliedObject = importedObject or obj
        appliedObjects = [appliedObject, *appliedObject.children_recursive]

        applyRotation(appliedObjects, obj['rotation'])

## On s'occupe de corriger les sources de lumières
for light_data in bpy.data.lights:
    if light_data.users:
        if light_data.type == 'POINT':
                light_data.shadow_soft_size = 0.025

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
        fixRotationMatrix = mathutils.Matrix.LocRotScale(
            None,
            mathutils.Euler((math.radians(90), math.radians(180), math.radians(-90))),
            mathutils.Vector((1, -1, 1)))

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


## Apply a little bit of sheen on all materials

for mat in bpy.data.materials:
    if (
        mat.node_tree is not None
        and "Principled BSDF" in mat.node_tree.nodes
        and mat.node_tree.nodes["Principled BSDF"].inputs[23].default_value == 0
    ):
        mat.node_tree.nodes["Principled BSDF"].inputs[23].default_value = 0.02


## Rotate the HDRI to have similar sun rotation (and similar shadows) as exported scene

if "__render_sun" in bpy.data.objects:
    sun = bpy.data.objects["__render_sun"]
    sun.data.energy = 0

    sceneSunRotation = sun.matrix_world.decompose()[1].to_euler().z
    hdrMapSunRotation = 0.86924

    bpy.data.worlds["World"].node_tree.nodes["Mapping"].inputs[2].default_value[2] = hdrMapSunRotation - sceneSunRotation


## Set the active camera
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
    camera.data.ortho_scale = xmag

bpy.context.scene.camera = camera

bpy.ops.wm.save_as_mainfile(filepath=f"./cache/scene-{sceneEnvironment}-{session}.blend")


print(f'--- render-scene-import.py execution time: {time.time() - startTime} seconds ---')
print(f'importedObjectsCount: {importedObjectsCount}')
print(f'importedMaterialsCount: {importedMaterialsCount}')
print(f'importedColorsCount: {importedColorsCount}')

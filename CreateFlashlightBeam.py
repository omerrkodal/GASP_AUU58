import unreal
import sys

def create_flashlight_material():
    package_path = '/Game/_GAME/Systems/EquippedItems/Materials'
    material_name = 'M_FlashlightBeam'
    full_path = package_path + '/' + material_name

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    # Check if exists and delete if so we can overwrite
    if unreal.EditorAssetLibrary.does_asset_exist(full_path):
        unreal.EditorAssetLibrary.delete_asset(full_path)
        
    # Create Material
    material_factory = unreal.MaterialFactoryNew()
    material = asset_tools.create_asset(material_name, package_path, unreal.Material, material_factory)

    if not material:
        unreal.log_error("Failed to create material.")
        return

    # Configure Material properties
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    
    # Disable depth test so the beam renders on top of things nicely if needed, or leave False.
    # material.set_editor_property('b_disable_depth_test', False)

    # 1. Depth Fade (softens intersection with geometry)
    depth_fade = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionDepthFade)
    depth_fade.set_editor_property('fade_distance_default', 200.0)

    # 2. Color Parameter
    color_param = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionVectorParameter)
    color_param.set_editor_property('parameter_name', 'BeamColor')
    color_param.set_editor_property('default_value', unreal.LinearColor(1.0, 0.9, 0.6, 1.0))

    # 3. Intensity Parameter
    intensity_param = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
    intensity_param.set_editor_property('parameter_name', 'Intensity')
    intensity_param.set_editor_property('default_value', 25.0)  # High value to ensure it glows!

    # Multiply Color by Intensity
    color_mult = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionMultiply)
    unreal.MaterialEditingLibrary.connect_material_expressions(color_param, '', color_mult, 'A')
    unreal.MaterialEditingLibrary.connect_material_expressions(intensity_param, '', color_mult, 'B')

    # Multiply by Depth Fade
    final_mult = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionMultiply)
    unreal.MaterialEditingLibrary.connect_material_expressions(color_mult, '', final_mult, 'A')
    unreal.MaterialEditingLibrary.connect_material_expressions(depth_fade, '', final_mult, 'B')

    # Connect to Emissive
    unreal.MaterialEditingLibrary.connect_material_property(final_mult, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    # Recompile and Save
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    
    unreal.log("Successfully created material: " + full_path)

if __name__ == "__main__":
    create_flashlight_material()

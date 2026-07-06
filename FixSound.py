import unreal

def fix_attenuation():
    asset_path = "/Game/_Assets/Equipped/MilitaryWeapSilver/Sound/Attenuation/RocketLoop_att"
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        unreal.log_error("Could not load RocketLoop_att")
        return

    # SoundAttenuation settings
    settings = asset.attenuation
    
    unreal.log("Original Falloff Distance: {}".format(settings.falloff_distance))
    unreal.log("Original Attenuation Shape: {}".format(settings.attenuation_shape))
    
    # Increase falloff distance so it doesn't cut out immediately
    settings.falloff_distance = 8000.0  # Fades out over 80 meters
    
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    unreal.log("Successfully updated Falloff Distance to 8000")

fix_attenuation()

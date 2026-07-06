import unreal
import json

concurrencies = [
    "/Game/_Assets/Equipped/TPS_System/Weapons/LyraAudio/Concurrency/SCON_Guns_LimitToOwner",
    "/Game/_Assets/Equipped/TPS_System/Weapons/LyraAudio/Concurrency/SCON_Guns_StopFarthest",
    "/Game/_Assets/Equipped/TPS_System/Weapons/LyraAudio/Concurrency/SCON_WeaponImpacts"
]

results = {}

for path in concurrencies:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset:
        try:
            settings = asset.concurrency
            results[path] = {
                "max_count": settings.max_count,
                "resolution_rule": str(settings.resolution_rule),
                "voice_steal_release_time": settings.voice_steal_release_time
            }
            
            # Optionally fix it immediately if it's 0
            if settings.voice_steal_release_time == 0.0:
                settings.voice_steal_release_time = 0.15 # 150ms fade out on steal
                unreal.EditorAssetLibrary.save_loaded_asset(asset)
                results[path]["fixed"] = True
                results[path]["new_voice_steal_release_time"] = settings.voice_steal_release_time
        except Exception as e:
            results[path] = {"error": str(e)}

output_file = r"c:\Users\kody\Documents\Unreal Projects\GASP_AUU58\ConcurrencyDetails.json"
with open(output_file, 'w') as f:
    json.dump(results, f, indent=4)

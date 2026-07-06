import unreal
import json

results = {}

montage_path = "/Game/_Assets/Equipped/TPS_System/AnimationLibrary/Shotgun/MM_Shotgun_Fire_Montage"
montage = unreal.EditorAssetLibrary.load_asset(montage_path)
if montage:
    try:
        results["Montage"] = {
            "sequence_length": montage.get_play_length(),
            "rate_scale": montage.rate_scale,
            "blend_in_time": montage.blend_in.blend_time,
            "blend_out_time": montage.blend_out.blend_time,
            "blend_out_trigger_time": montage.blend_out_trigger_time
        }
    except Exception as e:
        results["Montage"] = {"error": str(e)}

output_file = r"c:\Users\kody\Documents\Unreal Projects\GASP_AUU58\MontageDetails.json"
with open(output_file, 'w') as f:
    json.dump(results, f, indent=4)

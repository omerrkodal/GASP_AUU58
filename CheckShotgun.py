import unreal
import json

results = {}

def dump_object(obj):
    if not obj:
        return "None"
    
    props = {}
    props["class"] = obj.get_class().get_name()
    
    for prop in dir(obj):
        # Skip standard methods and private fields
        if prop.startswith("_") or prop in [
            "call_method", "get_class", "get_default_object", "get_editor_property", 
            "get_fname", "get_full_name", "get_name", "get_outer", "get_outermost", 
            "get_path_name", "get_typed_outer", "get_world", "modify", "rename", "set_editor_property",
            "cast", "static_class"
        ]:
            continue
            
        try:
            val = obj.get_editor_property(prop)
            # if it's an object, get its path
            if isinstance(val, unreal.Object):
                props[prop] = val.get_path_name()
            elif isinstance(val, unreal.StructBase):
                props[prop] = str(val)
            elif isinstance(val, list) or isinstance(val, unreal.Array):
                props[prop] = [v.get_path_name() if isinstance(v, unreal.Object) else str(v) for v in val]
            else:
                props[prop] = str(val)
        except Exception:
            pass
            
    # special cases
    if isinstance(obj, unreal.AnimMontage):
        props["sequence_length"] = obj.get_play_length()
    elif isinstance(obj, unreal.AnimSequenceBase):
        props["sequence_length"] = obj.get_play_length()
        
    return props

paths_to_check = [
    "/Game/_Assets/Equipped/TPS_System/AnimationLibrary/Shotgun/MM_Shotgun_Fire",
    "/Game/_Assets/Equipped/TPS_System/AnimationLibrary/Shotgun/MM_Shotgun_Fire_Montage",
    "/Game/_Assets/Equipped/MilitaryWeapSilver/Weapons/Animations/Fire_Shotgun_W",
    "/Game/_Assets/Equipped/TPS_System/Weapons/LyraAudio/Sounds/Weapons/Shotgun/MSS_Weapons_Shotgun_Fire",
    "/Game/_GAME/Data/DataAsset/EquippedItems/Weapon/Shotgun/DA_Shotgun_Anim",
    "/Game/_GAME/Data/DataAsset/EquippedItems/Weapon/Shotgun/DA_Shotgun_SFX",
    "/Game/_GAME/Data/DataAsset/EquippedItems/Weapon/Shotgun/DA_Shotgun",
    "/Game/_Assets/Equipped/TPS_System/Weapons/LyraAudio/AttenuationPresets/ATT_Shotgun"
]

for path in paths_to_check:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset:
        results[path] = dump_object(asset)
    else:
        results[path] = {"error": "Could not load asset"}

output_file = r"c:\Users\kody\Documents\Unreal Projects\GASP_AUU58\ShotgunDetails.json"
with open(output_file, 'w') as f:
    json.dump(results, f, indent=4)
    
unreal.log(f"Shotgun details written to {output_file}")

"""
recompile.py  -  Full clean rebuild of the Unreal project + all plugins.

What it deletes   : Binaries/  and  Intermediate/  inside the project root
                    and every folder inside Plugins/.
What it NEVER touches : Saved/  Config/  Content/  (editor settings safe).

Usage
-----
  python recompile.py           <- clean + full UBT build
  python recompile.py --launch  <- clean + build + open Unreal Editor
"""

import os, sys, json, shutil, subprocess, winreg

# ---------------------------------------------------------------------------
PROJECT_ROOT   = os.path.dirname(os.path.abspath(__file__))
CLEAN_FOLDERS  = ("Binaries", "Intermediate")   # NEVER add Saved or Config
# ---------------------------------------------------------------------------


def find_uproject(root):
    for name in os.listdir(root):
        if name.endswith(".uproject"):
            return os.path.join(root, name)
    raise FileNotFoundError(f"No .uproject found in: {root}")


def get_engine_path(assoc):
    """Look up the engine install directory from the Windows registry."""
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            reg_path = "SOFTWARE\\EpicGames\\Unreal Engine\\" + assoc
            key = winreg.OpenKey(hive, reg_path)
            path, _ = winreg.QueryValueEx(key, "InstalledDirectory")
            if os.path.isdir(path):
                return path
        except OSError:
            pass

    # Fallback: scan common drives
    for drive in ("C:", "D:", "E:", "F:"):
        candidate = os.path.join(drive + "\\", "Program Files", "Epic Games", "UE_" + assoc)
        if os.path.isdir(candidate):
            return candidate

    raise RuntimeError(
        "Engine path not found for association: " + assoc + "\n"
        "Open this script and hard-code ENGINE_PATH at the top."
    )


def clean_dir(path, label=""):
    label = label or path
    cleaned = False
    for folder in CLEAN_FOLDERS:
        target = os.path.join(path, folder)
        if os.path.isdir(target):
            print("  [DEL]  " + target)
            shutil.rmtree(target)
            cleaned = True
    if not cleaned:
        print("  [OK ]  " + label + "  (already clean)")


def run_ubt(engine_path, uproject_path, project_name):
    build_bat = os.path.join(engine_path, "Engine", "Build", "BatchFiles", "Build.bat")
    if not os.path.isfile(build_bat):
        raise FileNotFoundError("Build.bat not found: " + build_bat)

    cmd = [
        build_bat,
        project_name + "Editor",
        "Win64",
        "Development",
        uproject_path,
        "-waitmutex",
        "-NoHotReload",
    ]

    print("\n" + "-" * 60)
    print("UBT command:")
    print("  " + " ".join(('"' + c + '"' if " " in c else c) for c in cmd))
    print("-" * 60 + "\n")

    result = subprocess.run(cmd)
    return result.returncode


def open_editor(engine_path, uproject_path):
    exe = os.path.join(engine_path, "Engine", "Binaries", "Win64", "UnrealEditor.exe")
    if not os.path.isfile(exe):
        print("WARNING: UnrealEditor.exe not found at: " + exe)
        return
    print("\nLaunching Unreal Editor ...")
    subprocess.Popen([exe, uproject_path])


def main():
    want_launch = "--launch" in sys.argv

    uproject_path  = find_uproject(PROJECT_ROOT)
    project_name   = os.path.splitext(os.path.basename(uproject_path))[0]

    with open(uproject_path, encoding="utf-8") as fh:
        data = json.load(fh)

    assoc = data.get("EngineAssociation", "")
    if not assoc:
        raise RuntimeError("EngineAssociation key missing from .uproject")

    engine_path = get_engine_path(assoc)

    print("Project  : " + project_name)
    print("Engine   : " + engine_path)
    print("UProject : " + uproject_path)
    print()

    # --- Clean project root ---
    print("=== Cleaning Project ===")
    clean_dir(PROJECT_ROOT, "Project root")

    # --- Clean every plugin ---
    plugins_root = os.path.join(PROJECT_ROOT, "Plugins")
    if os.path.isdir(plugins_root):
        print("\n=== Cleaning Plugins ===")
        for name in sorted(os.listdir(plugins_root)):
            pdir = os.path.join(plugins_root, name)
            if os.path.isdir(pdir):
                clean_dir(pdir, "Plugin: " + name)

    # --- Build ---
    print("\n=== Building ===")
    code = run_ubt(engine_path, uproject_path, project_name)

    if code == 0:
        print("\nBuild succeeded!")
        if want_launch:
            open_editor(engine_path, uproject_path)
    else:
        print("\nBuild FAILED  (exit code " + str(code) + ")")
        sys.exit(code)


if __name__ == "__main__":
    main()

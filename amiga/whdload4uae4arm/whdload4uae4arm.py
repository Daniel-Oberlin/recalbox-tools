import os
import shutil
import subprocess
import csv

# --- Constants ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LHA_DIR = os.path.join(BASE_DIR, "lha")
EXPAND_DIR = os.path.join(BASE_DIR, "expand")
DB_DIR = os.path.join(BASE_DIR, "db")
ROMS_DIR = os.path.join(BASE_DIR, "roms")
AMIGA600_DIR = os.path.join(ROMS_DIR, "amiga600")
AMIGA1200_DIR = os.path.join(ROMS_DIR, "amiga1200")
CD32_DIR = os.path.join(ROMS_DIR, "amigacd32")
SCAN_SCRIPT = os.path.join(BASE_DIR, "amiga68ktools", "tools", "scan_slaves.py")
DATABASE_FILE = os.path.join(DB_DIR, "database.csv")
GAMES_CSV = os.path.join(BASE_DIR, "games.csv")

# --- Helpers ---
def clear_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def extract_lha_archives():
    """Extract LHA archives and map expanded directory names to archive filenames."""
    dir_to_archive_map = {}
    total_archives = 0
    successful_expansions = 0

    for file in os.listdir(LHA_DIR):
        if file.lower().endswith(".lha"):
            total_archives += 1
            archive_path = os.path.join(LHA_DIR, file)
            temp_dir = os.path.join(EXPAND_DIR, f"temp_{os.path.splitext(file)[0]}")

            # Create a temporary directory for extraction
            os.makedirs(temp_dir, exist_ok=True)

            # Extract the archive silently into the temporary directory
            subprocess.run(["lha", "xq", archive_path], cwd=temp_dir, check=True)

            # Find the expanded directory inside the temporary directory
            expanded_dirs_in_temp = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            if len(expanded_dirs_in_temp) != 1:
                # Print an error and continue
                print(f"[ERROR] Skipping {file}: Expected exactly one expanded directory, found {len(expanded_dirs_in_temp)}")
                shutil.rmtree(temp_dir)  # Clean up the temporary directory
                continue

            expanded_dir_name = expanded_dirs_in_temp[0]
            expanded_dir_path = os.path.join(temp_dir, expanded_dir_name)

            # Map the expanded directory name to the archive filename
            dir_to_archive_map[expanded_dir_name] = file
            successful_expansions += 1

            # Move the expanded directory up one level to the expand directory
            final_dest = os.path.join(EXPAND_DIR, expanded_dir_name)
            if os.path.exists(final_dest):
                shutil.rmtree(final_dest)
            shutil.move(expanded_dir_path, final_dest)

            # Clean up the temporary directory
            shutil.rmtree(temp_dir)

    print(f"[INFO] Successfully expanded {successful_expansions} out of {total_archives} archives.")
    return dir_to_archive_map

def run_scan_slaves():
    """Run the scan_slaves script and count the number of successfully analyzed slave files."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(BASE_DIR, "amiga68ktools", "lib")
    result = subprocess.run([
        "python3", SCAN_SCRIPT,
        EXPAND_DIR,
        DB_DIR
    ], env=env, capture_output=True, text=True, check=True)

    # Capture the output and errors
    stdout = result.stdout
    stderr = result.stderr

    # Count the number of successfully analyzed slave files
    analyzed_slaves = stdout.count(".slave") + stdout.count(".Slave")
    print(f"[INFO] Successfully analyzed {analyzed_slaves} slave files.")

    print(stderr.strip())

def load_game_names():
    """Load game names from games.csv if it exists."""
    game_name_map = {}
    if os.path.exists(GAMES_CSV):
        with open(GAMES_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                archive_name = row.get("Archive Name", "").strip()
                game_name = row.get("Game", "").strip()
                if archive_name and game_name:
                    game_name_map[archive_name] = game_name
    return game_name_map

def generate_uae_file(hidden_name, dest_base, is_aga, dir_to_archive_map, game_name_map):
    """Generate a .uae file for the given directory."""
    dest_dir = os.path.join(dest_base, hidden_name)
    system_base_dir = os.path.join(BASE_DIR, "system_base")
    if os.path.exists(system_base_dir):
        for item in os.listdir(system_base_dir):
            s = os.path.join(system_base_dir, item)
            d = os.path.join(dest_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

    # Determine the base name for the .uae file
    archive_name = dir_to_archive_map.get(hidden_name.lstrip("."), None)
    game_name = game_name_map.get(archive_name, None)
    visible_name = game_name if game_name else hidden_name.lstrip(".")

    # Write the .uae file
    out_path = os.path.join(dest_base, f"{visible_name}.uae")
    lines = [
        f"filesystem2=rw,DH0:GAME:/recalbox/share/roms/{os.path.basename(dest_base)}/{hidden_name}/,0",
        "boot1=dh0",
        "kickstart_rom_file=/recalbox/share/bios/kick40068.A1200" if is_aga else "kickstart_rom_file=/recalbox/share/bios/kick40063.A600",
        "cpu_type=68000" if not is_aga else "cpu_type=68020",
        "chipset=ecs" if not is_aga else "chipset=aga",
        "chipmem_size=2" if is_aga else "chipmem_size=2",
        "fastmem_size=8" if is_aga else "fastmem_size=8"
    ]
    with open(out_path, "w") as f:
        f.write("\n".join(lines))

def process_database(dir_to_archive_map):
    """Process the database and print errors for missing entries."""
    game_name_map = load_game_names()
    processed_dirs = set()  # Track directories processed from the database

    with open(DATABASE_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            dir_name = row['path']
            game_name = os.path.basename(os.path.dirname(dir_name))
            flags = row['flags'].split(',')
            is_aga = 'ReqAGA' in flags
            if "AGA" in game_name.upper():
                is_aga = True
            src = os.path.join(EXPAND_DIR, os.path.dirname(dir_name))
            if not os.path.exists(src):
                print(f"[WARN] Skipping missing path: {src}")
                continue

            archive_name = os.path.basename(os.path.dirname(dir_name)) + ".lha"
            game_name_override = game_name_map.get(archive_name)

            hidden_name = f".{os.path.basename(os.path.dirname(dir_name))}"
            
            # Determine the destination directory
            if "CD32" in archive_name.upper():
                dest_base = CD32_DIR
            elif is_aga:
                dest_base = AMIGA1200_DIR
            else:
                dest_base = AMIGA600_DIR

            dest_dir = os.path.join(dest_base, hidden_name)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            if os.path.isdir(src):
                shutil.copytree(src, dest_dir)
            else:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dest_dir, os.path.basename(src)))

            generate_uae_file(hidden_name, dest_base, is_aga, dir_to_archive_map, game_name_map)
            processed_dirs.add(os.path.basename(os.path.dirname(dir_name)))  # Mark directory as processed

    # Check for unprocessed directories
    unprocessed_dirs = set(dir_to_archive_map.keys()) - processed_dirs
    for unprocessed_dir in unprocessed_dirs:
        print(f"[ERROR] No database entry found for expanded directory: {unprocessed_dir}")

def process_adf_files():
    """Process .adf files and directories containing .adf files."""
    ADF_DIR = os.path.join(BASE_DIR, "adf")  # Directory containing .adf files
    if not os.path.exists(ADF_DIR):
        print(f"[ERROR] ADF directory not found: {ADF_DIR}")
        return

    for item in os.listdir(ADF_DIR):
        item_path = os.path.join(ADF_DIR, item)

        # Determine if it's a single .adf file or a directory
        if os.path.isfile(item_path) and item.lower().endswith(".adf"):
            # Single .adf file
            process_single_adf(item_path)
        elif os.path.isdir(item_path):
            # Directory containing multiple .adf files
            process_adf_directory(item_path)
        else:
            print(f"[WARN] Skipping unsupported item in ADF directory: {item_path}")


def process_single_adf(adf_path):
    """Process a single .adf file."""
    base_name = os.path.splitext(os.path.basename(adf_path))[0]
    is_aga = "AGA" in base_name.upper()
    dest_base = AMIGA1200_DIR if is_aga else AMIGA600_DIR
    hidden_name = f".{base_name}"
    dest_dir = os.path.join(dest_base, hidden_name)

    # Create the hidden directory and copy the .adf file
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(adf_path, dest_dir)

    # Determine the game name from the map
    game_name = load_game_names().get(os.path.basename(adf_path), None)
    uae_base_name = game_name if game_name else base_name

    # Generate the .uae file at the same level as the hidden directory
    generate_adf_uae_file(uae_base_name, dest_base, is_aga, [os.path.basename(adf_path)], hidden_name)


def process_adf_directory(adf_dir):
    """Process a directory containing multiple .adf files."""
    adf_files = sorted([f for f in os.listdir(adf_dir) if f.lower().endswith(".adf")])
    if not adf_files:
        print(f"[WARN] No .adf files found in directory: {adf_dir}")
        return

    # Use the base name of the first alphabetical .adf file
    first_adf = adf_files[0]
    base_name = os.path.splitext(first_adf)[0]
    is_aga = "AGA" in base_name.upper()
    dest_base = AMIGA1200_DIR if is_aga else AMIGA600_DIR
    hidden_name = f".{base_name}"
    dest_dir = os.path.join(dest_base, hidden_name)

    # Create the hidden directory and copy all .adf files
    os.makedirs(dest_dir, exist_ok=True)
    for adf_file in adf_files:
        shutil.copy2(os.path.join(adf_dir, adf_file), dest_dir)

    # Determine the game name from the map
    game_name = load_game_names().get(first_adf, None)
    uae_base_name = game_name if game_name else base_name

    # Generate the .uae file at the same level as the hidden directory
    generate_adf_uae_file(uae_base_name, dest_base, is_aga, adf_files, hidden_name)


def generate_adf_uae_file(base_name, dest_base, is_aga, adf_files, hidden_name):
    """Generate a .uae file for an ADF-based game."""
    out_path = os.path.join(dest_base, f"{base_name}.uae")  # Place .uae file at the same level as the hidden directory
    kickstart_path = "/recalbox/share/bios/kick40068.A1200" if is_aga else "/recalbox/share/bios/kick40063.A600"

    # Map the first four alphabetically ordered .adf files to floppy drives
    floppy_drives = [f"floppy{i}=/recalbox/share/roms/{os.path.basename(dest_base)}/{hidden_name}/{adf_files[i]}" for i in range(min(4, len(adf_files)))]

    # Generate the UAE configuration
    lines = [
        "use_gui=no",
        "nr_floppies=4",
        f"kickstart_rom_file={kickstart_path}",
        "chipset=aga" if is_aga else "chipset=ecs",
        "cpu_type=68020" if is_aga else "cpu_type=68000",
        "chipmem_size=2",
        "fastmem_size=8",
    ] + floppy_drives

    # Write the UAE file
    print(f"Generating UAE config: {out_path}")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")  # Ensure trailing newline
    except IOError as e:
        print(f"[ERROR] Failed to write UAE file {out_path}: {e}")

def process_iso_files():
    """Copy .iso, .wav, and .cue files from the iso directory to the CD32 ROMs directory."""
    ISO_DIR = os.path.join(BASE_DIR, "iso")  # Directory containing .iso, .wav, and .cue files
    if not os.path.exists(ISO_DIR):
        print(f"[ERROR] ISO directory not found: {ISO_DIR}")
        return

    for file in os.listdir(ISO_DIR):
        if file.lower().endswith((".iso", ".wav", ".cue")):
            src_path = os.path.join(ISO_DIR, file)
            dest_path = os.path.join(CD32_DIR, file)

            # Copy the file to the CD32 directory
            try:
                shutil.copy2(src_path, dest_path)
                print(f"[INFO] Copied {file} to {CD32_DIR}")
            except IOError as e:
                print(f"[ERROR] Failed to copy {file}: {e}")

# --- Main Execution ---
print("Starting WHDLoad preparation script...")

print("Clearing previous output directories...")
clear_dir(DB_DIR)
clear_dir(EXPAND_DIR)
clear_dir(ROMS_DIR)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(AMIGA600_DIR, exist_ok=True)
os.makedirs(AMIGA1200_DIR, exist_ok=True)
os.makedirs(CD32_DIR, exist_ok=True)  # Create CD32 directory
print("Output directories cleared and recreated.")

dir_to_archive_map = extract_lha_archives()
run_scan_slaves()
process_database(dir_to_archive_map)
process_adf_files()
process_iso_files()  # Add this step to process ISO files

print("Script finished.")
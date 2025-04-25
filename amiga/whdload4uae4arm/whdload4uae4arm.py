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
SCAN_SCRIPT = os.path.join(BASE_DIR, "amiga68ktools", "tools", "scan_slaves.py")
DATABASE_FILE = os.path.join(DB_DIR, "database.csv")
GAMES_CSV = os.path.join(LHA_DIR, "games.csv")

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
            dest_base = AMIGA1200_DIR if is_aga else AMIGA600_DIR
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

# --- Main Execution ---
clear_dir(DB_DIR)
clear_dir(EXPAND_DIR)
clear_dir(ROMS_DIR)
os.makedirs(AMIGA600_DIR, exist_ok=True)
os.makedirs(AMIGA1200_DIR, exist_ok=True)

dir_to_archive_map = extract_lha_archives()
run_scan_slaves()
process_database(dir_to_archive_map)
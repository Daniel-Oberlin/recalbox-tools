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

def generate_uae_file(uae_base_name, dest_base, hidden_dir, system_type, format_type, adf_files=None, cue_file=None):
    """
    Generate a .uae file for a game.

    Args:
        uae_base_name (str): The base name for the .uae file.
        dest_base (str): The base directory where the .uae file will be placed.
        hidden_dir (str): The hidden directory name for the game.
        system_type (str): The system type ('cd32', 'aga', 'ecs').
        format_type (str): The format type ('adf', 'whdload', 'cd32').
        adf_files (list, optional): List of .adf files for ADF-based games.
        cue_file (str, optional): The .cue file for CD32 games.
    """
    out_path = os.path.join(dest_base, f"{uae_base_name}.uae")
    lines = []

    # CPU
    lines.append("cpu_type=68ec020" if system_type == "cd32" else "cpu_type=68020" if system_type == "aga" else "cpu_type=68000")
    lines.append("cpu_speed=max" if system_type == "cd32" else None)

    # Chipset
    lines.append("chipset=aga" if system_type in ["cd32", "aga"] else "chipset=ecs")
    lines.append("akiko=true" if system_type == "cd32" else None)

    # Memory
    lines.append("chipmem_size=2" if system_type == "cd32" else "chipmem_size=4" if system_type == "aga" else "chipmem_size=2")
    lines.append("fastmem_size=8")
    lines.append(
        "kickstart_rom_file=/recalbox/share/bios/kick40060.CD32"
        if system_type == "cd32" else
        "kickstart_rom_file=/recalbox/share/bios/kick40068.A1200"
        if system_type == "aga" else
        "kickstart_rom_file=/recalbox/share/bios/kick40063.A600"
    )
    lines.append(
        "kickstart_ext_rom_file=/recalbox/share/bios/kick40060.CD32.ext"
        if system_type == "cd32" else None
    )
    lines.append("cd32nvram=true" if system_type == "cd32" else None)

    # Disk
    if format_type == "cd32" and cue_file:
        lines.append(f"cdimage0=/recalbox/share/roms/{os.path.basename(dest_base)}/{os.path.join(hidden_dir, cue_file)},image")
        lines.append("boot1=cd32")
        lines.append("cd32cd=true")
    elif format_type == "whdload":
        lines.append("boot1=dh0")
        lines.append(f"filesystem2=rw,DH0:GAME:/recalbox/share/roms/{os.path.basename(dest_base)}/{hidden_dir}/,0")
    elif format_type == "adf" and adf_files:
        lines.append("boot1=df0")
        lines.append("nr_floppies=4")
        floppy_drives = [
            f"floppy{i}=/recalbox/share/roms/{os.path.basename(dest_base)}/{hidden_dir}/{adf_files[i]}"
            for i in range(min(4, len(adf_files)))
        ]
        lines.extend(floppy_drives)

    # Misc
    lines.append("use_gui=no" if system_type == "cd32" else None)

    # Remove all None entries
    lines = [line for line in lines if line is not None]

    # Write the UAE file
    print(f"Generating UAE config: {out_path}")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")  # Ensure trailing newline
    except IOError as e:
        print(f"[ERROR] Failed to write UAE file {out_path}: {e}")

def process_database(dir_to_archive_map, game_name_map):
    """Process the database and handle WHDLoad games with kick_name logic."""
    processed_dirs = set()  # Track directories processed from the database

    with open(DATABASE_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            expand_dir_path = row['path']
            expand_dir_name = os.path.basename(os.path.dirname(expand_dir_path))
            flags = row['flags'].split(',')
            kick_name = row.get('kick_name', '').strip()  # Get the kick_name field
            is_cd32 = "CD32" in expand_dir_name.upper()
            is_aga = 'ReqAGA' in flags or "AGA" in expand_dir_name.upper()
            system_type = "cd32" if is_cd32 else "aga" if is_aga else "ecs"
            format_type = "whdload"  # WHDLoad format for database entries

            src = os.path.join(EXPAND_DIR, os.path.dirname(expand_dir_path))
            if not os.path.exists(src):
                print(f"[WARN] Skipping missing path: {src}")
                continue

            archive_name = dir_to_archive_map.get(expand_dir_name, None)
            game_name_override = game_name_map.get(archive_name)

            # Use game_name_override if set, otherwise fallback to the existing logic
            uae_base_name = game_name_override if game_name_override else expand_dir_name
            hidden_dir = f".{archive_name.rsplit('.', 1)[0]}" if archive_name else f".{expand_dir_name}"
            dest_base = CD32_DIR if system_type == "cd32" else AMIGA1200_DIR if system_type == "aga" else AMIGA600_DIR

            dest_dir = os.path.join(dest_base, hidden_dir)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            if os.path.isdir(src):
                shutil.copytree(src, dest_dir)
            else:
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dest_dir, os.path.basename(src)))

            # Copy the contents of system_base into the hidden directory
            system_base = os.path.join(BASE_DIR, "system_base")
            if os.path.exists(system_base):
                for item in os.listdir(system_base):
                    src_path = os.path.join(system_base, item)
                    dest_path = os.path.join(dest_dir, item)
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_path, dest_path)

            # Handle kick_name logic for WHDLoad games
            if format_type == "whdload" and kick_name:
                if is_valid_kick_name(kick_name):
                    copy_kickstart_file(kick_name, dest_dir)

            generate_uae_file(uae_base_name, dest_base, hidden_dir, system_type, format_type)
            processed_dirs.add(expand_dir_name)  # Mark directory as processed

    # Check for unprocessed directories
    unprocessed_dirs = set(dir_to_archive_map.keys()) - processed_dirs
    for unprocessed_dir in unprocessed_dirs:
        print(f"[ERROR] No database entry found for expanded directory: {unprocessed_dir}")

def process_adf_files(game_name_map):
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
            process_single_adf(item_path, game_name_map)
        elif os.path.isdir(item_path):
            # Directory containing multiple .adf files
            process_adf_directory(item_path, game_name_map)
        else:
            print(f"[WARN] Skipping unsupported item in ADF directory: {item_path}")


def process_single_adf(adf_path, game_name_map):
    """Process a single .adf file."""
    base_name = os.path.splitext(os.path.basename(adf_path))[0]
    is_aga = "AGA" in base_name.upper()
    system_type = "aga" if is_aga else "ecs"
    dest_base = AMIGA1200_DIR if is_aga else AMIGA600_DIR
    hidden_dir = f".{base_name}"
    dest_dir = os.path.join(dest_base, hidden_dir)

    # Create the hidden directory and copy the .adf file
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(adf_path, dest_dir)

    # Determine the game name from the map
    game_name = game_name_map.get(os.path.basename(adf_path), None)
    uae_base_name = game_name if game_name else base_name

    # Generate the .uae file
    generate_uae_file(uae_base_name, dest_base, hidden_dir, system_type, "adf", [os.path.basename(adf_path)])


def process_adf_directory(adf_dir, game_name_map):
    """Process a directory containing multiple .adf files."""
    adf_files = sorted([f for f in os.listdir(adf_dir) if f.lower().endswith(".adf")])
    if not adf_files:
        print(f"[WARN] No .adf files found in directory: {adf_dir}")
        return

    # Use the base name of the first alphabetical .adf file
    first_adf = adf_files[0]
    base_name = os.path.splitext(first_adf)[0]
    is_aga = "AGA" in adf_dir.upper()
    system_type = "aga" if is_aga else "ecs"
    dest_base = AMIGA1200_DIR if is_aga else AMIGA600_DIR
    hidden_dir = f".{base_name}"
    dest_dir = os.path.join(dest_base, hidden_dir)

    # Create the hidden directory and copy all .adf files
    os.makedirs(dest_dir, exist_ok=True)
    for adf_file in adf_files:
        shutil.copy2(os.path.join(adf_dir, adf_file), dest_dir)

    # Determine the game name from the map
    game_name = game_name_map.get(first_adf, None)
    uae_base_name = game_name if game_name else base_name

    # Generate the .uae file
    generate_uae_file(uae_base_name, dest_base, hidden_dir, system_type, "adf", adf_files)

def process_iso_files(game_name_map):
    """
    Process subdirectories in the ISO directory for CD32 games.
    Each subdirectory contains a .cue file and other files.
    """
    ISO_DIR = os.path.join(BASE_DIR, "iso")  # Directory containing subdirectories for CD32 games
    if not os.path.exists(ISO_DIR):
        print(f"[ERROR] ISO directory not found: {ISO_DIR}")
        return

    for subdir in os.listdir(ISO_DIR):
        subdir_path = os.path.join(ISO_DIR, subdir)
        if not os.path.isdir(subdir_path):
            print(f"[WARN] Skipping non-directory item in ISO directory: {subdir_path}")
            continue

        # Find the .cue file in the subdirectory
        cue_files = [f for f in os.listdir(subdir_path) if f.lower().endswith(".cue")]
        if len(cue_files) != 1:
            print(f"[ERROR] Skipping {subdir_path}: Expected exactly one .cue file, found {len(cue_files)}")
            continue

        cue_file = cue_files[0]
        base_name = os.path.splitext(cue_file)[0]  # Base name of the .cue file
        hidden_dir = f".{base_name}"  # Hidden directory name
        dest_dir = os.path.join(CD32_DIR, hidden_dir)  # Destination hidden directory

        # Determine the .uae file name
        game_name = game_name_map.get(cue_file, None)
        uae_base_name = game_name if game_name else base_name  # Use game name if available, otherwise fallback to base name

        # Create the hidden directory and copy all files from the original subdirectory
        os.makedirs(dest_dir, exist_ok=True)
        for file in os.listdir(subdir_path):
            src_path = os.path.join(subdir_path, file)
            dest_path = os.path.join(dest_dir, file)
            shutil.copy2(src_path, dest_path)

        # Generate the .uae file
        generate_uae_file(uae_base_name, CD32_DIR, hidden_dir, "cd32", "cd32", cue_file=cue_file)

def is_valid_kick_name(kick_name):
    """Validate the kick_name format: nnnnn.a*."""
    import re
    return bool(re.fullmatch(r"\d{5}\.a.*", kick_name, re.IGNORECASE))

def copy_kickstart_file(kick_name, dest_dir):
    """
    Copy the kickstart file and its corresponding .RTB file from the kickstart directory
    to the Devs/Kickstarts directory.

    Args:
        kick_name (str): The validated kick_name (e.g., "34005.a500").
        dest_dir (str): The destination directory (hidden folder).
    """
    kickstart_dir = os.path.join(BASE_DIR, "kickstart")
    kickstarts_dir = os.path.join(dest_dir, "Devs", "Kickstarts")
    os.makedirs(kickstarts_dir, exist_ok=True)

    # Construct source and destination file paths for the kickstart file
    source_file = os.path.join(kickstart_dir, f"kick{kick_name.upper()}")
    dest_file = os.path.join(kickstarts_dir, f"kick{kick_name.upper()}")

    # Copy the kickstart file
    if os.path.exists(source_file):
        shutil.copy2(source_file, dest_file)
    else:
        print(f"[WARN] Kickstart file not found: {source_file}")

    # Construct source and destination file paths for the .RTB file
    source_rtb_file = f"{source_file}.RTB"
    dest_rtb_file = f"{dest_file}.RTB"

    # Copy the .RTB file
    if os.path.exists(source_rtb_file):
        shutil.copy2(source_rtb_file, dest_rtb_file)
    else:
        print(f"[WARN] RTB file not found: {source_rtb_file}")

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
game_name_map = load_game_names()
run_scan_slaves()
process_database(dir_to_archive_map, game_name_map)
process_adf_files(game_name_map)
process_iso_files(game_name_map)  # Add this step to process ISO files

print("Script finished.")
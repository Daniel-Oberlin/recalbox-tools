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

# --- Helpers ---
def clear_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def extract_lha_archives():
    for file in os.listdir(LHA_DIR):
        if file.lower().endswith(".lha"):
            archive_path = os.path.join(LHA_DIR, file)
            subprocess.run(["lha", "x", archive_path], cwd=EXPAND_DIR)

def run_scan_slaves():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(BASE_DIR, "amiga68ktools", "lib")
    subprocess.run([
        "python3", SCAN_SCRIPT,
        EXPAND_DIR,
        DB_DIR
    ], env=env, check=True)

def generate_uae_file(hidden_name, dest_base, is_aga):

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

    game_dir = os.path.join(dest_base, hidden_name)
    visible_name = hidden_name.lstrip(".")
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

def process_database():
    with open(DATABASE_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            dir_name = row['path']
            flags = row['flags'].split(',')
            is_aga = 'ReqAGA' in flags

            dir_name_only = os.path.basename(dir_name)
            src = os.path.join(EXPAND_DIR, os.path.dirname(dir_name))
            if not os.path.exists(src):
                print(f"[WARN] Skipping missing path: {src}")
                continue

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

            generate_uae_file(hidden_name, dest_base, is_aga)

# --- Main Execution ---
clear_dir(DB_DIR)
clear_dir(EXPAND_DIR)
clear_dir(ROMS_DIR)
os.makedirs(AMIGA600_DIR, exist_ok=True)
os.makedirs(AMIGA1200_DIR, exist_ok=True)

extract_lha_archives()
run_scan_slaves()
process_database()

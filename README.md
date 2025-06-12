# Recalbox Tools

I've been working on getting Recalbox running on my Pi4, running as a PINN bootable OS.  I have a special interest in MAME, Amiga, and C64 emulation.  This README is a documentation of my notes, and the repository includes any useful data or tools that I have set up along the way.

## Recalbox

It's fun to customize the background music.  Here are some music sources:
- https://modarchive.org/index.php
- https://downloads.khinsider.com/

Use this to make the whole filesystem writeable:

```bash
mount -o remount,rw
```

Needed to edit the systemlist.xml config file that is read-only otherwise.  I think making the file system writable means that you add a writable overlay on top of the read-only SquashFS root filesystem.  I think you could change the password this way, but it involves updating the shadow file among other things.

## PINN

I needed to make a small partition on my 1TB SD card in order to accomodate the initial PINN os installation.  It was not simple to do this on the Mac because many of the partition command line options would force the partition to fill up the whole 1TB.  **TODO:** document this better.

At the time of this work, the latest version of Recalbox was 9.2.3, and there was PINN OS distribution available for this version, so I had to make my own distribution.  Here's what I did:

You first need to download and convert the compressed Recalbox image into a compressed tar archive:

recalbox-rpi4_64.img.xz -> recalbox-rpi4_64.tar.xz

PINN expects the firmware files to be directly in the root of the partition, not nested within a directory.  Also, any .sh or other files that need executable status should have their permissions changed, and mac-specific attributes should be excluded.

Once you have the image, here's how to mount it on Mac and create the tar archive:

```bash
% hdiutil attach ~/Downloads/recalbox-rpi4_64.img 
/dev/disk5         	FDisk_partition_scheme         	
/dev/disk5s1       	Windows_FAT_32                 	/Volumes/RECALBOX
# TODO: mount
% cd /Volumes/RECALBOX
% chmod +x ./boot/linux
% chmod +x ./pre-upgrade.sh
% chmod +x ./start4.elf
% chmod +x ./start4x.elf
% tar --no-xattrs -cJpf ../RECALBOX.tar.xz .
% cd ..
% sudo umount /Volumes/RECALBOX
% hdiutil detach /dev/disk5  # Adjust if your device is different
```

**TODO:** run through the above, make sure it works.  Also, why set permissions if they never existed in FAT32?

partition_setup.sh was not required.

Be sure to fill the SD card with dummy "project" partitiosn so that you can add other OS using "replace" later without re-doing the parition scheme.

Sound needs to be configured for HDMI.

**TODO:**
  - Figure out how to make small partition again, use the SD card from my drone or remote control
  - Run through the packaging process again and make sure it is correctly documented
  - Understand about the permissions and FAT32


## MAME

There are several cores that you can use to run MAME.  I was tempted to use the most recent core because I thought it would provide the best emulation, however I quickly learned that for almost all games, the MAME2003plus core works the best and is easiet to get running.  I only switched to MAME2015 for some of the more recent games, like Mortal Kombat.

Get the ROMS, samples, and artwork from a MAME2003 collection and they should just work.

**TODO:** Talk about placement of art files and sound samples wihtin the recalbox filesystem.

## Amiga

Strangely, the Amiga kernal ROMs are placed at the root of the /bios directory, not in /bios/amiga600 or in /bios/amiga1200 where I would expect them.  Also, different emulators expect the same ROMs to have different names, so they end up being duplicated.  The Recalbox BIOS checker checks for the names that are expected for uae4arm.  

**uae4arm**



ROM names and locations for Amiberry and uae4arm

**Amiberry**

Amiberry has a really cool feature where it can accept WHDLoad games directly in lha archive format.  When you select a game at runtime, it drops the lha archive into a special Workbench environment in the filesystem.  When Workbench runs, it uses lha to unpack the archive into a temporary directory and then launches it with WHDLoad.

Unfortunately, I have not yet been able to get Amiberry to run any games.  Some things on the web suggest that recent Amiberry builds have not been included in Recalbox and that maybe it is not maintained.  Even so, I would like to get Amiberry to work so as to have another emulator option available.

Amiberry looks for Kickstart ROMs in the bios directory named like "kick13.rom", "kick31.rom", which is different from the convention used by uae4arm.

**PUAE**

PUAE seems to run a lot of standard Amiga games rather slowly, for example, Stunt Car Racer is much choppier - even running on an Amiga 600.

That said, it is the only emulator core that I have been able to use to run CD32 games, and those games seem to run very well.

**Amiga TODO:**
  - **Amiberry:** Get Amiberry running on Raspberry Pi OS to see if it is worth more time getting it to work on Recalbox
  - **uae4arm:** Fix keyboard mappings for US
  - **PUAE:** Fix the intro music for Super Stardust

## C64

A few games expect to be run in PAL mode.  In some cases joysticks won't work properly unless PAL mode is enabled.  For example, "The Last V8", and one of the foreign-language versions of Archon.  The English version of Archon that I currently have feels too fast (intro music and gameplay) unless it is run in PAL mode.

**C64 TODO:**
- Is it possible to load disks into multiple drives?
- Scanline shaders?

## Apple

For the linapple emulator, sound on HDMI doesn't work.  Sound is available through the headphone jack only.  You don't need to change the Recalbox global sound mode, that can remain as HDMI and linapple will still output to headphone jack.  An easy solution is to plug in a headphone and make sure the volume is high, and then you get an almost authentic speaker sound for the Apple emulation.

**Apple TODO:**
 - Complete building library of games
 - Assign controller to keyboard mappings for appropriate games
 - Figure out how to make scaline shaders work

 ## N64

 In order to use hires textures, you must run the game with LIBRETRO MUPEN64PLUS_NEXT emulator.

 You must change settings in "Core Options -> GlideN64":
 
 - Use High-Res textures = ON
 - Use High-Res Texture Cache Compression = ON (optional, generates compressed .htc file, I think)
 - Use High-Res Full Alpha Channel = ON
 - Use enhance Hi_Res Storage = ON (optional, uses uncompressed .hts file if you have it, I think)

 

 Place the textures in, for example:
/recalbox/share/bios/Mupen64plus/hires_texture/SUPER MARIO 64/

And the .hts texture cache in, for example:
/recalbox/share/bios/Mupen64plus/cache/SUPER MARIO 64_HIRESTEXTURES.hts

If the .htc file is generated, it will be placed in the same folder, and it can take a significant time to load the first time.

For my XBox One controller, I found that I needed to add content to InputAutoCf.ini for "[Xbox One S Controller]", see the example file.

# Recalbox Tools

I've been working on getting Recalbox running on my PI4, running as a PINN bootable OS.  I have a special interest in MAME, Amiga, and C64 emulation.  This README is a documentation of my notes, and the repository includes any useful data or tools that I have set up along the way.

## Recalbox

Recalbox has a number of easy, well documented ways to work with roms and other files in the installation:

- **SSH**: SSH root credentials are well known.
- **Network Share**: Look for "RECALBOX" on your network, you can access the share directory using this
- **Web**: There is a web interface that lets you do a lot of things

It's fun to customize the music.

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
partition_setup.sh was not required.

Be sure to fill the SD card with dummy "project" partitiosn so that you can add other OS using "replace" later without re-doing the parition scheme.

Sound needs to be configured for HDMI.

## MAME

There are several cores that you can use to run MAME.  I was tempted to use the most recent core because I thought it would provide the best emulation, however I quickly learned that for almost all games, the MAME2003plus core works the best and is easiet to get running.  I only switched to MAME2015 for some of the more recent games, like Mortal Kombat.

Get the ROMS, samples, and artwork from a MAME2003 collection and they should just work.

Artwork placement...

## Amiga

  - Use this: "mount -o remount,rw /" to make the whole filesystem writeable.

## C64

## License

TBD


## Scraps
Specify the license for the project.

Steps to install and set up the project.

- **Feature 1**: Brief description of the feature.
- **Feature 2**: Brief description of the feature.
- **Feature 3**: Brief description of the feature.
- **To-Do**: List of tasks or improvements.
  - Sub-task 1
  - Sub-task 2


```python
# This is a Python code block
def hello_world():
    print("Hello, world!")
```

```bash
# This is a shell code block
echo "Hello, world!"
ls -la
```
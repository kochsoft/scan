# Scan

A UI frontend for the **Sane** library.

## About

This project aims at **ease of use** for scanning, both from flatbed and automatic
document feeder, and, as a side effect, even some cameras.

A proper wiki page is yet a **ToDo**. However, at this time at least some
screenshots are available at

https://github.com/kochsoft/scan/tree/main/doc/gallery

Right off the bat: This project employs the **Sane** library, in order to access
scanning devices from the computer. As far as I can judge, this tool is for
**Linux-like systems only**: http://www.sane-project.org/sane-support.html

## Why is it?

After all, there is xsane.

However, at least in my opinion, while doubtless powerful, xsane is a horror
in terms of user-experience.

## What is it?

This project provides a nice graphical user interface for simplistic,

* plain flatbed scanning.
* ADF (Automatic Document Feeder) scanning.
* Saving into either a single pdf or multiple pngs. Seascape if requested.
* DIN A4 paper format may be enforced if so desired.

The program collects scans in a list that may be viewed and shortened
in a secondary preview tab.

## How is it? (Setup!)

The entire program is in **Python 3**. Extra requirements are

* `tkinter`, the GUI system,
* `python-sane`, the sane library providing means to access scanners, and
* `Pillow`, data serializations software for handling images.

Copy the `./src` directories contents to where you want them.

At the top of `scan.py` is a short section **config.sys** where some
default values can be set to your needs.

Most notably, the default scanner `code`. My own scanner is embedded in
an Epson ET-4850 printer and is set as the default default in the file:

```
airscan:e0:EPSON ET-4850 Series
```

Upon starting the `scan_ui.py`, it will first look for available scanners
on your system. At the top of the main tab there is a combobox where the
scanners that have been identified are noted in form of their device codes.
Find your favorite one and replace above default code by it.

### Required Pacakges -- Arch

**Disclaimer**: This program has been developed on an Arch system, where already
quite a few packages had been installed. I attempted to use `pacman -Q | grep -i ..`
and some guess-work to determine which packages were really used.
It is possible that the below list is incomplete.

**requirements.txt**:

```
# Python bindings for the sane library.
python-sane
# Image processing.
Pillow
```
 
* `colord-sane`: Colored sane support
* `sane`: The scanner library used.
* `sane-airscan`: Not strictly required. But (at least for Epson ET4850) offers driver-less devices with improved features like ADF (Automatic Document Feeder).
* `python`: Python 3 interpreter.

### Required Packages  -- Debian

* `python-tk`: tkinter, the GUI system.
* `python-pillow`: PIL library. Holding the Image class used by this project.
* `idle`: Some testing suite? Seems to be a dependency of `python-pillow`.
* `python3-pil-imagetk`: Offers turning pillow images into tk photos. For previews.
* `python-sane`: The python-binding library for sane used by this project.
* `python3`: The python 3 interpreter. At the time of writing this was 3.11.

Very useful is `sane-airscan` for 'driver-less access'. Not quite sure, what
that really means, but it allows additional devices with, in my case,
the option of actually using the ADF (automatic document feeder).

### Required Packages -- Windows 11

I was unable to bring Scan to Windows 11. Not even when using WSL 2
(Windows Subsystem for Linux). Sane appears not have been made for this.

## Command line interface

Note, that `scan.py` is a command line tool in its own right.
The UI is actually optional.

## Running the program

After all has been set up, run the program:

```
(Py313)$ python3 scan_ui.py
```

## Help text for `scan.py`

```
(Py313)$ python3 scan.py --help

usage: scan.py [-h] [--list] [--dev DEV] [--dpi DPI] [--png] [--a4 A4]
               [--landscape | --scan | --multi]
               [pfname_out]

Smallish UI project for offering the most common scanner functions of an Epson ET 4850 device.

positional arguments:
  pfname_out   Target pfname for scanner output.

options:
  -h, --help   show this help message and exit
  --list       Identify all available devices and print the list.
  --dev DEV    At least part of a device name. From known devices will use the first one that fits. If none is given, default 'airscan' will be used.
  --dpi DPI    Either one or two dpi numbers for dpi_x and dpi_y. Default: 72
  --png        Produce a set of png graphics rather than a comprehensive pdf file.
  --a4 A4      Enforce A4 format. Give 'stretch' or 'pad' for stretching or merely pasting the original image content.
  --landscape  Do a 90 degree rotation for landscape orientation (as opposed to portrait, AKA seascape).
  --scan       Do a single flatbed scan.
  --multi      Do an Automatic Document Feeder (ADF) scan.

Example call:
$ python3 scan.py --list
```
## Known Bugs

* Enforce A4 seems to mix up resolution for large scanned images.
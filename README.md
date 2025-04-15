# Scan

A tkinter UI frontend for the **Sane** library.

A proper wiki page is yet a **ToDo**. However, at this time at least some
screenshots are available at

https://github.com/kochsoft/scan/tree/main/doc/gallery

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

Most notably, the default scanner code. My own scanner is embedded in
an Epson ET-4850 printer and is set as the default default in the ffile.

Note, that `scan.py` is a command line tool in its own right.
The UI is actually optional. One function that is not provided by the UI is

```
$ python3 scan.py --list

Chicony USB2.0 Camera: IR Camer: v4l:/dev/video2
Chicony USB2.0 Camera: Chicony : v4l:/dev/video0
ET-4850 Series: escl:https://192.168.178.130:443
PID: epson2:net:192.168.178.130
EPSON ET-4850 Series: airscan:e0:EPSON ET-4850 Series
```

It is yet a **TODO** to improve this output and make it a feature of the UI.
However, the scanner code comes after the name and the first colon.

## Running the program

After all is set up, run the program:

```
(Py313)$ python3 scan_ui.py
```

## Help text for `scan.py`

```
(Py313)$ python3 scan.py --help

usage: scan.py [-h] [--list] [--dev DEV] [--png] [--a4] [--scan | --multi] [pfname_out]

Smallish UI project for offering the most common scanner functions of an Epson ET 4850 device.

positional arguments:
  pfname_out  Target pfname for scanner output.

options:
  -h, --help  show this help message and exit
  --list      Identify all available devices and print the list.
  --dev DEV   At least part of a device name. From known devices will use the first one that fits. If none is given, default 'airscan:e0:EPSON ET-4850 Series' will be used.
  --png       Produce a set of png graphics rather than a comprehensive pdf file.
  --a4        Enforce A4 format.
  --scan      Do a single flatbed scan.
  --multi     Do an Automatic Document Feeder (ADF) scan.

Example call:
$ python3 scan_ui.py
```

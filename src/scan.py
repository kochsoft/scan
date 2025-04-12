#!/usr/bin/python3
"""
User-friendly scanner tool for the Epson ET 4850. Aiming at
+ Just scanning the current page into pdf or png.
+ Concatenating more pages, if so desired.
+ Alternatively, scanning a set of pages through the automatic feed into a multipage project.
And nothing more! Please.

Why? All this can be done using xsane. However, holy mother of god!, the user interface of that time-honored thing!

Markus-Hermann Koch, https://github.com/kochsoft/scan, April 12th 2025.

Literature:
===========
[1] Main documentation of the python sane API
    https://python-sane.readthedocs.io/en/latest/
[2] Multi Scan example. Most notable line: device.source = 'ADF' to enable automatic document feeder.
    https://github.com/python-pillow/Sane/issues/23
[3] Make even multiple PIL images into one PDF.
    https://stackoverflow.com/questions/27327513/create-pdf-from-a-list-of-images
"""
import sys
import sane
import _sane
import argparse
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import Optional, List, Tuple, Callable
import time
import logging


# > config.sys. ------------------------------------------------------
# Default values for some config parameters. Adjust to your own needs.
defaults = {
    # Target device identifier. Use --list to get options. 'dev' keys are the first entries in each device tuple.
    'dev': 'airscan:e0:EPSON ET-4850 Series',
    # Target output pfname.
    'pfname_out': 'scan.pdf',
    # Mime type of output. So far, only png and pdf are supported.
    'mime': 'pdf',
    # Working directory for temporary files.
    'pname_tmp': Path(sys.path[0]).joinpath('../tmp')  # << ../tmp from this script file's location.
}
# < ------------------------------------------------------------------


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

regexp_invalid_pfname_chars = r'[/\\?%*:|"<> !]'


class Scan:
    def __init__(self, cb_print: Callable[[str], None] = print, args: Optional[List[str]] = None):
        self.cb_print = cb_print  # type: Callable[[str], None]
        self.device = None  # type: Optional[sane.SaneDev]
        self.known_devs = None  # type: Optional[List[Tuple[str]]]
        try:
            self.info_init = sane.init()
        except _sane.error as err:
            _log.warning(f"Failure to init scanner interface: {err}")
            sys.exit(1)
        arguments = self.parse_arguments(args)
        self.pfname_out = arguments.pfname_out
        self.as_png = True if arguments.png else False
        self.dev = arguments.dev
        self.pname_tmp = arguments.pname_tmp
        self.pfnames_tmp = list()  # type: List[str]

        if arguments.list:
            self.print("Searching for available scanner devices.")
            self.get_known_devs()
            self.print(self)

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """:return Time string for introduction into file names."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def __str__(self) -> str:
        #  (sane_ver, ver_maj, ver_min, ver_patch).
        res = f"""Sane version: {'.'.join([str(j) for j in self.info_init])}"""
        res += "Known devices: "
        if self.known_devs:
            for kd in self.known_devs:
                res += f"\n  {kd}"
            res += "\n"
        else:
            res += "None\n"
        res += f"""Target device: {self.dev}
Actual Device: {self.device}"""
        return res

    def print(self, msg):
        """Local print function taking a callable. Intended for updating some statusbar in a GUI."""
        self.cb_print(msg)

    def get_known_devs(self, *, force_recache=False) -> Optional[List[Tuple[str]]]:
        """:param force_recache: If True, and if there already is a non-None list of devices, return that directly.
            Else call sane.get_devices() in any case.
        :returns the List of Tuples of str that is returned by sane.get_devices(). Or None in case of failure."""
        if force_recache:
            self.known_devs = None
        if self.known_devs is None:
            try:
                self.known_devs = sane.get_devices(localOnly=False)
            except _sane.error as err:
                self.print(f"Failure to obtain available devices: {err}")
                return None
        return self.known_devs

    def connect(self, *, force_recache=False) -> int:
        if force_recache:
            self.device = None
        if self.device:
            return 0
        self.get_known_devs()
        if not self.known_devs:
            self.print("No scanner devices could be identified.")
            return 2
        # [Note: The first entry is the device key.]
        devs = [tpl[0] for tpl in self.known_devs]

        # [Note: First try to get an exact match. If this fails, make do with a partial one. If that still fails, stop.]
        dev_target = None  # type: Optional[str]
        for d in devs:
            if self.dev == d:
                dev_target = d
                break
        if not dev_target:
            for d in devs:
                if str(self.dev).lower() in d.lower():
                    dev_target = d
                    break
        if not dev_target:
            self.print(f"Failure to find device '{self.dev}'. Options: {devs}")
            return 3
        self.print(f"Mapping requested dev code '{self.dev}' to device code '{dev_target}'")
        self.dev = dev_target

        try:
            self.device = sane.SaneDev(self.dev)
        except _sane.error as err:
            self.print(f"Failure to connect to device '{self.dev}': {err}")
            return 4

        _log.info(f"Device object obtained: {self.device}")
        self.print(f"Obtained device object for target device '{self.dev}'.")
        return 0

    def multiscan(self) -> int:
        """Perform an ADF (Automatic Document Feeder) multi-scan and write temporary png graphics."""
        if err := self.connect():
            return err
        self.pfnames_tmp = list()
        # https://github.com/python-pillow/Sane/issues/23
        # [Note: This source setting to 'ADF' ensures that the Automatic Document Feeder will be used rather than the flatbed scanner.]
        self.device.source = 'ADF'
        iterator = self.device.multi_scan()
        fname_base = f'_multi_{self.get_time()}'
        c = 0
        for image in iterator:
            fname = Path(f"{c:04}_{fname_base}.png")
            pfname_tmp = str(Path(self.pname_tmp).joinpath(fname))
            image.save(pfname_tmp)
            self.pfnames_tmp.append(pfname_tmp)
            c = c + 1
        # TODO! Hier war ich! Sammle die Bilder ein und mache ein PDF/PNG daraus. Ueber PIL kann ich mir vielleicht sogar die Tmp-Files schenken.

    def scan(self) -> int:
        if err := self.connect():
            return err
        self.pfnames_tmp = list()
        self.device.source = 'Flatbed'
        image = self.device.scan()
        image.save(self.pfname_out)
        # TODO! Hier war ich. Das funktioniert bislang nur fuer PNG.

    @staticmethod
    def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
        if args is None:
            args = sys.argv[1:]
        desc = """Smallish UI project for offering the most common scanner functions of an Epson ET 4850 device."""
        epilog = f"""Example call:
$ python3 {Path(sys.argv[0]).name}"""
        parser = argparse.ArgumentParser(prog='scan.py', description=desc, epilog=epilog, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--list', action='store_true', help="Identify all available devices and print the list.")
        parser.add_argument('--dev', type=str, help="At least part of a device name. From known devices will use the "+\
                            f"first one that fits. If none is given, default '{defaults['dev']}' will be used.", default=defaults['dev'])
        parser.add_argument('--png', action='store_true', help='Produce a set of png graphics rather than a comprehensive pdf file.')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--scan', action='store_true', help='Do a single flatbed scan.')
        group.add_argument('--multi', action='store_true', help='Do an Automatic Document Feeder (ADF) scan.')
        parser.add_argument('--pname_tmp', type=str, help=f"Working directory for temporary files. Defaults to: {defaults['pname_tmp']}")
        parser.add_argument('pfname_out', type=str, help="Target pfname for scanner output.", default=defaults['pfname_out'])
        parsed = parser.parse_args(args)
        return parsed


if __name__ == '__main__':
    scanner = Scan()
    scanner.connect()
    print("Done.")

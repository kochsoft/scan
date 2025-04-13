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
[4] Save an Image as A4 in size.
    https://stackoverflow.com/questions/27271138/python-pil-pillow-pad-image-to-desired-size-eg-a4
"""
import sys
import time
import logging
import argparse
from enum import Enum
from pathlib import Path
from argparse import RawTextHelpFormatter
from typing import Optional, List, Dict, Tuple, Callable
import sane
import _sane
from PIL.Image import Image

# > config.sys. ------------------------------------------------------
# Default values for some config parameters. Adjust to your own needs.
defaults = {
    # Target device identifier. Use --list to get options. 'dev' keys are the first entries in each device tuple.
    'dev': 'airscan:e0:EPSON ET-4850 Series',
    # Dots per inch.
    'dpi': 72
}
# < ------------------------------------------------------------------


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',datefmt='%H:%M:%S')
_log = logging.getLogger()

regexp_invalid_pfname_chars = r'[/\\?%*:|"<> !]'


class E_ScanType(Enum):
    ST_UNSPECIFIED = 0
    ST_SINGLE_FLATBED = 1
    ST_MULTI_FLATBED = 2
    ST_MULTI_ADF = 3


class E_OutputType(Enum):
    OT_UNSPECIFIED = 0
    OT_PDF = 1
    OT_PDF_A4 = 2
    OT_PNG = 3

    def to_format(self) -> Optional[str]:
        """:returns a string that can be used as 'format' parameter in a Pil.Image.Image object."""
        # https://pillow.readthedocs.io/en/stable/reference/Image.html
        if self in (E_OutputType.OT_PDF, E_OutputType.OT_PDF_A4):
            return 'PDF'
        elif self == E_OutputType.OT_PNG:
            return 'PNG'
        return None


class Device:
    def __init__(self, hint_dev: str, code_devs: List[Tuple[str, str, str, str]]):
        """:param hint_dev: Device string as may be given by the user. Could be incomplete.
        :param code_devs: List of device tuples as returned by sane.get_device().
        [Note: It is a design decision that this will not call 'sane.get_devices()' automatically.
        That call is rather expensive and should not be used more often than strictly necessary.]"""
        # This object may become invalid at any time a sane-call raises an exception.
        self.is_valid = False  # type: bool
        self._device = None  # type: Optional[sane.SaneDev]
        self.code_devs = code_devs  # type: List[Tuple[str, str, str, str]]
        if not self.code_devs:
            _log.warning("Unable to create Device. Given list of available devices is empty.")
            return
        if not hint_dev:
            hint_dev = defaults['dev']
        self.code_dev = self.get_code_dev(hint_dev)
        if not self.code_dev:
            _log.warning(f"Failure to identify target device from hint '{hint_dev}'")
            return
        self.is_valid = True

    def __str__(self):
        validity = "Valid" if self.is_valid else "Invalid"
        return f"{validity} device: {self.code_dev}"

    @property
    def dev(self) -> Optional[str]:
        """:returns this device code string for sane.open(..) or None if not available."""
        if self.code_dev is None:
            return None
        else:
            return self.code_dev

    @property
    def device(self) -> Optional[sane.SaneDev]:
        return self._device

    def create_device(self) -> Optional[sane.SaneDev]:
        """Closes a potentially existing self._device and attempts to open a new one, ready for scanning.
        Will write the resulting object into self._device.
        :return Will also return a reference to the resulting object. Or None, in case of failure."""
        dev = self.dev
        if not dev:
            return None
        if self._device:
            self._device.close()
            self._device = None
            return None
        try:
            self._device = sane.open(dev)
        except _sane.error as err:
            _log.warning(f"Failure to open device '{dev}': {err}")
        return self._device

    def close_device(self):
        """Closes the device and resets self._device to None."""
        if self._device is not None:
            self._device.close()
        self._device = None

    def get_code_dev(self, hint_dev: str) -> Optional[str]:
        """Given a user-spawned hint, return the target device code for sane.open(..).
        Or None, in case of failure."""
        for code_dev in self.code_devs:
            code = code_dev[0].lower()
            if hint_dev.lower() == code:
                return code
        for code_dev in self.code_devs:
            code = str(code_dev[0]).lower()
            if hint_dev.lower() in code:
                return code
        return None

    @staticmethod
    def code_dev2str(code: Tuple[str, str, str, str]):
        """:param code: Device code tuple, like they are returned by sane.get_devices().
        :returns: Human-readable string representation of the given device code tuple."""
        if code is None:
            return 'None'
        if len(code) != 4:
            return f"Weird device code of len=={len(code)} encountered: {code}"
        return f"{code[2]}: dev code '{code[0]}'"


class Scan:
    """Main class for the command line script of this project."""
    def __init__(self, cb_print: Callable[[str], None] = print, args: Optional[List[str]] = None):
        self.cb_print = cb_print  # type: Callable[[str], None]
        self.device = None  # type: Optional[Device]
        self.code_devs = None  # type: Optional[List[Tuple[str]]]
        try:
            self.info_init = sane.init()
        except _sane.error as err:
            _log.warning(f"Failure to init scanner interface: {err}")
            sys.exit(1)
        arguments = self.parse_arguments(args)
        self.pfname_out = arguments.pfname_out
        self.format_output = E_OutputType.OT_PNG if arguments.png else E_OutputType.OT_PDF
        self.enforce_A4 = arguments.a4
        self.scan_tp = E_ScanType.ST_SINGLE_FLATBED
        if arguments.multi:
            self.scan_tp = E_ScanType.ST_MULTI_ADF
        elif arguments.scans:
            self.scan_tp = E_ScanType.ST_MULTI_FLATBED
        self.hint_dev = arguments.dev
        if arguments.list:
            self.print("Searching for available scanner devices.")
            self.get_code_devs()
            self.print(self)
        self.images = list()  # type: List[Image]
        if __name__ == '__main__':
            self.scan()
            if self.images:
                self.print(f"Attempting to write {len(self.images)} images to file: '{self.pfname_out}'.")
                self.images2file(self.pfname_out, self.images, tp=self.format_output, enforce_A4=self.enforce_A4)
            else:
                self.print(f"Failure to scan any images.")

    @staticmethod
    def get_time(frmt: str = "%y%m%d_%H%M%S", unix_time_s: Optional[int] = None) -> str:
        """:return Time string for introduction into file names."""
        unix_time_s = int(time.time()) if unix_time_s is None else int(unix_time_s)
        return time.strftime(frmt, time.localtime(unix_time_s))

    def __str__(self) -> str:
        #  (sane_ver, ver_maj, ver_min, ver_patch).
        res = f"""Sane version: {'.'.join([str(j) for j in self.info_init])}"""
        res += "Known devices: "
        if self.code_devs:
            for kd in self.code_devs:
                res += f"\n  {kd[2]}: {kd[0]}"
            res += "\n"
        else:
            res += "None\n"
        res += f"""Requested device: {self.hint_dev}
Actual Device: {self.device}"""
        return res

    def print(self, msg):
        """Local print function taking a callable. Intended for updating some statusbar in a GUI."""
        self.cb_print(msg)

    def ensure_device(self) -> Device:
        """:return a Device object."""
        if not self.device:
            self.device = Device(self.hint_dev, self.get_code_devs())
        return self.device

    def get_code_devs(self, *, force_recache=False) -> Optional[List[Tuple[str, str, str, str]]]:
        """:param force_recache: If True, and if there already is a non-None list of devices, return that directly.
            Else call sane.get_devices() in any case.
        :returns the List of Tuples of str that is returned by sane.get_devices(). Or None in case of failure."""
        if force_recache:
            self.code_devs = None
        if self.code_devs is None:
            try:
                self.code_devs = sane.get_devices(localOnly=False)
            except _sane.error as err:
                self.print(f"Failure to obtain available devices: {err}")
                return None
        return self.code_devs

    @staticmethod
    def convert_to_A4(im_input: Image) -> Optional[Image]:
        """:param im_input: Input Image.
        :returns a new image that has been upscaled to match A4 format.
        Note: Google tells me, DIN A4 is 210 mm x 297 mm (8.27 in x 11.69 in)."""
        # https://stackoverflow.com/questions/27271138/python-pil-pillow-pad-image-to-desired-size-eg-a4
        if 'dpi' not in im_input.info:
            im_input.info['dpi'] = defaults['dpi'], defaults['dpi']
        res_xy_input = im_input.info['dpi']
        dim_A4_px = int(res_xy_input[0] * 8.27), int(res_xy_input[1] * 11.69)
        im_out = im_input.copy().resize(dim_A4_px)
        im_out = im_out.resize(dim_A4_px)
        # a4im.paste(im, im.getbbox())
        return im_out

    @staticmethod
    def images2file(pfname: str, images: List[Image], *, tp: E_OutputType = E_OutputType.OT_PDF, enforce_A4: bool = False) -> int:
        if not images:
            _log.warning(f"Failure to write target file '{pfname}': Given image list is empty.")
            return 1
        if enforce_A4:
            images_A4 = list()  # type: List[Image]
            for img in images:
                images_A4.append(Scan.convert_to_A4(img))
            images = images_A4
        if len(images) > 1:
            images[0].save(pfname, tp.to_format(), dpi=(defaults['dpi'],defaults['dpi']), save_all=True, append_images=images[1:])
        else:
            images[0].save(pfname, tp.to_format(), dpi=(defaults['dpi'],defaults['dpi']))
        return 0

    def scan_adf(self, images: Optional[List[Image]] = None) -> List[Image]:
        """Perform an ADF (Automatic Document Feeder) multi-scan and write temporary png graphics."""
        if images is None:
            images = self.images
        self.get_code_devs()
        device = self.ensure_device()  # type: Device
        device.create_device()
        if not device.device:
            _log.warning(f"Failure to create device: {device.device}")
            return images
        device.device.source = "ADF"
        try:
            iterator = self.device.device.multi_scan()
        except Exception as err:
            self.print(f"Failure to perform multi-scan: {err}")
            return images
        images = list()  # type: List[Image]
        for image in iterator:
            images.append(image.copy())
        device.close_device()
        return images

    def scan_flatbed(self, images: Optional[List[Image]] = None) -> List[Image]:
        if images is None:
            images = self.images
        self.get_code_devs()
        device = self.ensure_device()  # type: Device
        device.create_device()
        if not device.device:
            _log.warning(f"Failure to create device: {device.device}")
            return images
        device.device.source = "Flatbed"
        try:
            image = device.device.scan()
            images.append(image)
        except _sane.error as err:
            print(f"Failure to scan from device '{device}': {err}")
        device.close_device()
        return images

    def scan(self, *, clear_images: bool = False):
        if clear_images:
            self.images.clear()
        if self.scan_tp in (E_ScanType.ST_SINGLE_FLATBED, E_ScanType.ST_MULTI_FLATBED):
            self.scan_flatbed()
        elif self.scan_tp == E_ScanType.ST_MULTI_ADF:
            self.scan_adf()
        else:
            _log.warning(f"Unsupported scan type '{self.scan_tp.name}' encountered.")

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
        parser.add_argument('--a4', action='store_true', help="Enforce A4 format.")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--scan', action='store_true', help='Do a single flatbed scan.')
        group.add_argument('--scans', action='store_true', help='Do multiple single flatbed scans.')
        group.add_argument('--multi', action='store_true', help='Do an Automatic Document Feeder (ADF) scan.')
        parser.add_argument('pfname_out', type=str, help="Target pfname for scanner output.")
        parsed = parser.parse_args(args)
        return parsed


if __name__ == '__main__':
    scanner = Scan()
    print("Done.")

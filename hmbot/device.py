import sys
import time
from typing import Union
from loguru import logger
from .app.app import App
from .exception import*
from .proto import SwipeDirection
from .rfl.system_rfl import system_rfl
from .vht import VHTNode
from .window import Window

class Device(object):
    """
    The class describes a connected device
    """

    def __init__(self, device_serial, operating_system):
        """
        Initialize a device connection
        Args:
            device_serial (str): The serial of device.
            operating_system (str): The operating system of device.
        """
        self.serial = device_serial
        self.operating_system = operating_system
        try:
            connector_cls, automator_cls = system_rfl[self.operating_system]
            self.connector = connector_cls(self)
            self.automator = automator_cls(self)
        except OSKeyError:
            logger.error("%s is not supported" % operating_system)
            sys.exit(-1)
        self.window = None

    def __call__(self, **kwds):
        self.dump_window(refresh=True)
        return self.window(**kwds)

    def install_app(self, app):
        self.automator.install_app(app)

    def uninstall_app(self, app):
        self.automator.uninstall_app(app)

    def start_app(self, app):
        self.automator.start_app(app)

    def stop_app(self, app):
        self.automator.stop_app(app)

    def restart_app(self, app):
        self.automator.restart_app(app)
    
    def click(self, x, y):
        return self.automator.click(x, y)

    def _click(self, node):
        (x, y) = node.attrib['center']
        return self.automator.click(x, y)

    def long_click(self, x, y):
        return self.automator.long_click(x, y)

    def _long_click(self, node):
        (x, y) = node.attrib['center']
        return self.automator.long_click(x, y)

    def drag(self, x1, y1, x2, y2, speed=2000):
        return self.automator.drag(x1, y1, x2, y2, speed)

    def swipe(self, x1, y1, x2, y2, speed=2000):
        return self.automator.swipe(x1, y1, x2, y2, speed)

    def swipe_ext(self, direction: Union[SwipeDirection, str]):
        return self.automator.swipe_ext(direction)
    
    def input(self, node, text):
        return self.automator.input(node, text)

    def dump_hierarchy(self, device=None):
        if device is None:
            device = self
        return self.automator.dump_hierarchy(device)

    def screenshot(self, path=''):
        return self.automator.screenshot(path)

    def home(self):
        self.automator.home()

    def back(self):
        self.automator.back()

    def recent(self):
        self.automator.recent()
    
    def dump_window(self, device=None, refresh=False):
        if device is None:
            device = self
        if self.window == None or refresh:
            vht = self.dump_hierarchy(device=device)
            img = self.screenshot()
            rsc = self.get_resource_status()
            ability = self.current_ability().get('ability')
            bundle = self.current_ability().get('bundle')
            self.window = Window(vht=vht, img=img, rsc=rsc, ability=ability, bundle=bundle)
        return self.window

    def dump_page(self, split=False, app=None):
        if not split:
            window = self.dump_window()
            if window._pages:
                return window._pages[0]
        if split and isinstance(app, App):
            return self.dump_window().current_page(app)

    def current_ability(self):
        return self.connector.current_ability()

    def hop(self, dst_device_name=None, app_name=None):
        return self.automator.hop(dst_device_name, app_name)
    
    def execute(self, events):
        for event in events:
            event.execute()

    def get_audio_status(self, bundle=None):
        return self.connector.get_audio_status(bundle)

    def get_resource_status(self, bundle=None):
        return self.connector.get_resource_status(bundle)
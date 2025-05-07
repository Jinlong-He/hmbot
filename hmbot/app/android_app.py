from .app import App
from loguru import logger
from androguard.core.apk import APK

class AndroidApp(App):
    def __init__(self, app_path='', device=None):
        apk = APK(self.app_path)
        self.bundle_name = apk.get_package()
        self.entry_ability = apk.get_main_activity()
        self.main_page = apk.get_main_activity()
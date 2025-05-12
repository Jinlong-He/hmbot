import time
from .app.android_app import AndroidApp
from .app.harmony_app import HarmonyApp
from .device import Device
from .event import StartAppEvent
from .explorer.llm import LLM
from .proto import OperatingSystem, ExploreGoal, ResourceType, AudioStatus
from .testcase.generator import AudioGenerator
from .window import Window
from .wtg import WTG
from loguru import logger
import os
import shutil


class HMBot(object):
    def __init__(self, os, serials, llm_config):
        self.os = os
        self.devices = []
        self.llm_config = llm_config
        self.app = None
        for serial in serials:
            self.devices.append(Device(serial, os))

    def detect_hac(self, resource_type, wtg):
        if wtg is None:
            return
        if len(self.devices) < 2:
            return
        genarator = None

        if resource_type == ResourceType.AUDIO:
            genarator = AudioGenerator(wtg, self.devices)

        if genarator:
            genarator.generate_test_case()
            genarator.execute_test_case()

    def explore(self, args):
        if args.os == OperatingSystem.HARMONY:
            if not args.app_path.endswith('.hap'):
                logger.error("Harmony application path must end with .hap!")
                exit(1)
            else:
                self.app = HarmonyApp(args.app_path)
        elif args.os == OperatingSystem.ANDROID:
            if not args.app_path.endswith('.apk'):
                logger.error("Android application path must end with .apk!")
                exit(1)
            else:
                self.app = AndroidApp(app_path=args.app_path)

        for device in self.devices:
            llm = LLM(device=device, url=self.llm_config['base_url'], model=self.llm_config['model'],
                      api_key=self.llm_config['api_key'])
            device.install_app(self.app)
            time.sleep(5)
            device.start_app(self.app)
            time.sleep(10)

            output_dir = args.output
            if not output_dir.endswith('/'):
                output_dir = output_dir + '/'
            output_dir = output_dir + device.serial + '/'

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Explore
            if args.hardware:
                # If the exploration goal is hardware resources, the value parameter is the resource type
                for hardware in args.hardware:
                    hardware_dir = output_dir + hardware + '/'
                    if os.path.exists(hardware_dir):
                        for item in os.listdir(hardware_dir):
                            item_path = os.path.join(hardware_dir, item)
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                    else:
                        os.makedirs(hardware_dir)
                    llm.explore(key=ExploreGoal.HARDWARE, value=hardware, max_steps=args.max_steps,
                                output_dir=hardware_dir)
            elif args.testcase:
                # If the exploration goal is test-script, the value parameter is the script path
                for index, testcase in enumerate(args.testcase):
                    with open(testcase, 'r') as file:
                        script = file.read()
                        testcase_dir = output_dir + testcase + str(index) + '/'
                        if os.path.exists(testcase_dir):
                            for item in os.listdir(testcase_dir):
                                item_path = os.path.join(testcase_dir, item)
                                if os.path.isfile(item_path):
                                    os.remove(item_path)
                                elif os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                        else:
                            os.makedirs(testcase_dir)
                        llm.explore(key=ExploreGoal.TESTCASE, value=script, max_steps=args.max_steps,
                                    output_dir=testcase_dir)

    def enhancement(self, test_wtg, other_wtg_list, resource_type):
        for other_wtg in other_wtg_list:
            if isinstance(other_wtg, WTG):
                self.enhance(test_wtg, other_wtg, resource_type)

    def enhance(self, test_wtg, other_wtg, resource_type):
        if not isinstance(test_wtg, WTG) or not isinstance(other_wtg, WTG):
            return
        if not self.devices:
            return
        device = self.devices[0]
        status = {
            ResourceType.AUDIO: AudioStatus.START,
        }

        all_wtg_path = self.event_to_status(resource_type, status[resource_type])
        all_other_wtg_path = self.event_to_status(resource_type, status[resource_type], other_wtg)
        for wtg_path in all_wtg_path:
            for other_wtg_path in all_other_wtg_path:
                bundle_test = wtg_path['target_window'].bundle
                device.start_app(bundle_test)
                for event in wtg_path['events_path']:
                    event.execute()

                bundle_other = other_wtg_path['target_window'].bundle
                device.start_app(bundle_other)
                start_event = StartAppEvent(device, bundle_other)
                for event in other_wtg_path['events_path']:
                    event.execute()

                device.recent()
                device.click(0.5, 0.5)

                cur_window = device.dump_window(refresh=True)
                test_wtg.add_window(cur_window)
                test_wtg.add_edge(wtg_path['target_window'], cur_window, other_wtg_path['events_path'] + start_event)
                device.stop_app(bundle_test)
                device.stop_app(bundle_other)

    def event_to_status(self, resource_type, status, wtg=None):
        if not wtg:
            wtg = self
        all_paths = []

        def dfs(cur_window, path, events_path):
            if cur_window.rsc[resource_type] == status:
                all_paths.append({
                    "target_window": cur_window,
                    "events_path": events_path.copy()
                })
                return
            for neighbor, events in wtg._adj_list.get(cur_window, {}).items():
                if any(isinstance(e, StartAppEvent) for e in events):
                    continue
                new_path = path + [neighbor]
                new_events_path = events_path + [events]
                dfs(neighbor, new_path, new_events_path)

        for main_window in wtg.main_windows:
            dfs(main_window, [main_window], [])
        return all_paths
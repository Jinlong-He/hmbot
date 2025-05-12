import pytest
from abc import ABC, abstractmethod
from hmbot.event import *
from hmbot.proto import AudioStatus, ResourceType

class Generator(ABC):
    """
    this interface describes a generator
    """
    @abstractmethod
    def __init__(self, wtg=None):
        pass

    @abstractmethod
    def generate_test_case(self):
        pass

    @abstractmethod
    def execute_test_case(self, test_case_file):
        pass

class AudioGenerator(Generator):
    def __init__(self, wtg, os, serials):
        self.wtg = wtg
        self.os = os
        self.serials = serials
        self.app = wtg.windows[0].bundle

    # generate a python file
    # return file name
    def generate_test_case(self):
        all_paths = self.event_to_status(self.wtg)

        test_case_content = "from hmbot.device import Device\n"
        test_case_content += "\nclass TestAudio:\n"
        test_case_content += "    def __init__(self):\n"
        test_case_content += f'        self.src_device = Device(\'{self.serials[0]}\', \'{self.os}\')\n'
        test_case_content += f'        self.tgt_device = Device(\'{self.serials[1]}\', \'{self.os}\')\n'
        # todo
        src_device_name = '\''+'Ice'+'\''
        tgt_device_name = '\''+'MatePad'+'\''

        for index, p in enumerate(all_paths):
            src_window = p.get('src_window')
            src_app = src_window.bundle
            # todo
            src_app_name = 'qqmusic'
            src_events = p.get('src_events')
            tgt_window = p.get('tgt_window')
            tgt_events = p.get('tgt_events')
            tgt_app = [e.app for e in tgt_events if isinstance(e, StartAppEvent)][0]
            # todo
            tgt_app_name = 'douyin'

            test_case_content += f"\n    # {src_app} test case {index+1}\n"
            test_case_content += f"    def test_{src_app_name}_{tgt_app_name}_{index+1}(self):\n"

            src_app = '\'' + src_app + '\''
            src_app_name = '\'' + src_app_name + '\''
            tgt_app = '\'' + tgt_app + '\''
            tgt_app_name = '\'' + tgt_app_name + '\''

            test_case_content += f'        self.src_device.start_app({src_app})\n'
            src_events = [e for es in src_events for e in es]
            for e in src_events:
                if isinstance(e, ClickEvent):
                    center = e.node.attribute['center']
                    test_case_content += f'        self.src_device.click({center[0]},{center[1]})\n'
                elif isinstance(e, LongClickEvent):
                    center = e.node.attribute['center']
                    test_case_content += f'        self.src_device.long_click({center[0]},{center[1]})\n'
                # todo
                elif isinstance(e, InputEvent):
                    pass
                elif isinstance(e, SwipeExtEvent):
                    test_case_content += f'        self.src_device.swipe_ext({e.direction})\n'
                # todo
                elif isinstance(e, KeyEvent):
                    pass

            test_case_content += f'\n        self.tgt_device.start_app({tgt_app})\n'
            for e in tgt_events:
                if isinstance(e, ClickEvent):
                    center = e.node.attribute['center']
                    test_case_content += f'        self.tgt_device.click({center[0]},{center[1]})\n'
                elif isinstance(e, LongClickEvent):
                    center = e.node.attribute['center']
                    test_case_content += f'        self.tgt_device.long_click({center[0]},{center[1]})\n'
                # todo
                elif isinstance(e, InputEvent):
                    pass
                elif isinstance(e, SwipeExtEvent):
                    test_case_content += f'        self.tgt_device.swipe_ext({e.direction})\n'
                # todo
                elif isinstance(e, KeyEvent):
                    pass
                
            test_case_content += f'\n        # hop src_app to tgt_device\n'
            test_case_content += f'        self.src_device.hop({tgt_device_name}, {src_app_name})\n'
            # todo cur_window inf
            test_case_content += f'        cur_window = self.tgt_device.dump_window(refresh=True)\n'

            test_case_content += f'\n        # hop src_app back to src_device\n'
            test_case_content += f'        self.tgt_device.hop({src_device_name}, {src_app_name})\n'
            # todo cur_window inf
            test_case_content += f'        cur_window = self.src_device.dump_window(refresh=True)\n'

            test_case_content += f'\n        # hop tgt_app to src_device\n'
            test_case_content += f'        self.tgt_device.hop({src_device_name}, {tgt_app_name})\n'
            # todo cur_window inf
            test_case_content += f'        cur_window = self.src_device.dump_window(refresh=True)\n'

            test_case_content += f'\n        self.src_device.stop_app({src_app})\n'
            test_case_content += f'        self.tgt_device.stop_app({tgt_app})\n'

        test_case_file = f"test_{self.app.replace('.', '_')}.py"
        try:
            with open(test_case_file, "w", encoding="utf-8") as f:
                f.write(test_case_content)
            print(f"Test cases generated in [{test_case_file}].")
        except Exception as e:
            print(f"Error: When writing to the test case file.: {e}")

        return test_case_file

    # execute python file
    def execute_test_case(self, test_case_file):
        try:
            exit_code = pytest.main([test_case_file])
            if exit_code == 0:
                print(f"{test_case_file} execution success.")
            else:
                print(f"{test_case_file} execution failed, exit code: {exit_code}")
        except Exception as e:
            print(f"A error occurred while executing {test_case_file}. {e}")

    def event_to_status(self, wtg):
        all_paths = []
        has_incoming = set()
        for window in wtg.windows:
            for neighbor in wtg._adj_list.get(window, {}):
                has_incoming.add(neighbor)
        start_windows = [window for window in wtg.windows if window not in has_incoming]

        def dfs(cur_window, path, events_path):
                if cur_window.rsc[ResourceType.AUDIO] == AudioStatus.START:
                    for neighbor, events in wtg._adj_list.get(cur_window, {}).items():
                        if any(isinstance(e, StartAppEvent) for e in events):
                            all_paths.append({
                                "src_window": cur_window,
                                "src_events": events_path.copy(),
                                "tgt_window": neighbor,
                                "tgt_events": events
                            })
                    return
                for neighbor, events in wtg._adj_list.get(cur_window, {}).items():
                    if any(isinstance(e, StartAppEvent) for e in events):
                        continue
                    new_path = path + [neighbor]
                    new_events_path = events_path + [events]
                    dfs(neighbor, new_path, new_events_path)

        for window in start_windows:
            dfs(window, [window], [])
        return all_paths
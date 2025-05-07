import argparse
from hmbot.proto import OperatingSystem

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    parser_devices = subparsers.add_parser('devices', help='list connected devices')
    parser_explore = subparsers.add_parser('explore', help='explore the app')
    parser_detect = subparsers.add_parser('detect', help='detect bugs')

    parser_devices.add_argument('--os', type=str, help='specify the operating system of deivce')
    # parser_explore.add_argument('app_path', type=str, help='specify the app path for exploration')
    # parser_explore.add_argument('-s', '--serial', type=str, help='specify the device serial for exploration')
    # parser_explore.add_argument('-d', '--depth', type=int, default=2, help='specify the depth of exploration, default is 2')
    # parser_explore.add_argument('-o', '--output', type=str, default='output.xml', help='specify the output file path of hstg')
    # parser_explore.add_argument('-t', '--timeout', type=int, default=30, help='specify the timeout of exploration')

    # parser_detect.add_argument('--source_device', type=str, help='specify the source device serial for detection')
    # parser_detect.add_argument('--target_device', type=str, help='specify the target device serial for detection')
    # parser_detect.add_argument('--source_app', type=str, help='specify the source app path for detection')
    # parser_detect.add_argument('--target_app', type=str, help='specify the target app path for detection')
    # parser_detect.add_argument('--source_hstg', type=str, help='specify the source hstg path for detection')
    # parser_detect.add_argument('--target_hstg', type=str, help='specify the target hstg path for detection')
    # parser_detect.add_argument('-o', '--output', type=str, default='output.xml', help='specify the output file path of detection')
    args = parser.parse_args()
    if args.command == 'devices':
        if args.os:
            os = args.os
            if os == OperatingSystem.HARMONY:
                from hmbot.utils import get_harmony_available_devices
                print(get_harmony_available_devices())
            if os == OperatingSystem.ANDROID:
                from hmbot.utils import get_android_available_devices
                print(get_android_available_devices())
    # if args.command == 'explore':
    #     serial = ''
    #     if args.serial:
    #         serial = args.serial
    #     else:
    #         from hacmony.utils import get_available_devices
    #         devices = get_available_devices()
    #         if len(devices) > 0:
    #             serial = devices[0]
    #         else:
    #             logger.warning("No device connected!")
    #             exit(0)
    #     depth = args.depth
    #     timeout = args.timeout
    #     hacmony = HACMony()
    #     device = Device(serial)
    #     hstg = hacmony.explore(device, depth, args.app_path, timeout)
    #     hstg.export_xml(args.output)

    # if args.command == 'detect':
    #     source_device_serial = ''
    #     target_device_serial = ''
    #     if args.source_device:
    #         source_device_serial = args.source_device
    #     else:
    #         from hacmony.utils import get_available_devices
    #         devices = get_available_devices()
    #         if len(devices) > 1:
    #             serial = devices[0]
    #         else:
    #             logger.warning("No device connected!")
    #             exit(0)
    #     if args.target_device:
    #         target_device_serial = args.target_device
    #     else:
    #         from hacmony.utils import get_available_devices
    #         devices = get_available_devices()
    #         if len(devices) > 1:
    #             serial = devices[1]
    #         else:
    #             logger.warning("No device connected!")
    #             exit(0)
        
    #     source_app_path = ''
    #     target_app_path = ''
    #     if args.source_app:
    #         source_app_path = args.source_app
    #     else:
    #         logger.warning("No source app path!")
    #     if args.target_app:
    #         target_app_path = args.target_app
    #     else:
    #         logger.warning("No target app path!")
    #     source_hstg_path = ''
    #     target_hstg_path = ''
    #     if args.source_hstg:
    #         source_hstg_path = args.source_hstg
    #     else:
    #         logger.warning("No source hstg path!")
    #     if args.target_hstg:
    #         target_hstg_path = args.target_hstg
    #     else:
    #         logger.warning("No target hstg path!")
    #     source_device = Device(source_device_serial)
    #     target_device = Device(target_device_serial)
    #     source_app = App(source_device, source_app_path)
    #     target_app = App(target_device, target_app_path)
    #     source_hstg = HSTG(source_device)
    #     target_hstg = HSTG(target_device)
    #     source_hstg.import_xml(source_hstg_path)
    #     target_hstg.import_xml(target_hstg_path)
    #     hacmony = HACMony()
    #     statuses = hacmony.detect_hac(source_device, source_app, source_hstg, target_device, target_app, target_hstg)



# from dista.device import Device
# from dista.vht import VHTParser
# from dista.proto import OperatingSystem
# import time
# print()

# device = Device('127.0.0.1:5555', OperatingSystem.HARMONY)
# hierarchy = device.dump_hierarchy()
# # print(hierarchy)
# # root = VHTParser.parse(hierarchy)
# # VHTParser.dump(root, 'test.json', 1)
# nodes = hierarchy.all(clickable = 'true', type = 'Button')
# for node in nodes:
#     print(node.attrib['text'], node.attrib['bounds'], node.attrib['center'])
# # device.click(nodes[0])
# print(device.display_size())
# print(device.display_rotation())
# device.swipe(direction='right')
# device.recent()
# device.automator._driver.swipe_ext('up', scale=0.5)
# device.automator._driver.swipe_ext('up')
# device.drag(0.5, 0.5, 0.2, 0.5, 200)
# device.drag(630/1260, 2710/2720, 630/1260, 2400/2720, 200)
# device.drag(630, 2710, 630, 2400, 200)
# time.sleep(1)
# device.automator._driver.gesture.start(0.5, 0.93, interval = 0.5).move(0.5, 0.8).action()
# device.automator._driver.gesture.start(0.5, 0.99).move(0.5, 0.8).pause(interval=0.5).move(0.5, 0.8).action()
# device.screenshot('aaa.jpeg')
# print(hierarchy)

# from typing import List
# from pydantic import BaseModel, Field
# import json

# class ViewAttributes(BaseModel):
#     model_config = {'extra': 'allow'}
#     bounds : str

# class View(BaseModel):
#     model_config = {'extra': 'allow'}
#     attributes : ViewAttributes
#     children: List['View'] = Field(default_factory = list)

# f = open('hierarchy.json', 'r')
# model = View(**json.load(f))
# print(model.attributes.bounds)

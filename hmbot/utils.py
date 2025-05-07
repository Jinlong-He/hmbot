from .proto import OperatingSystem


def get_available_devices():
    """
    Get a list of device serials connected via adb
    :return: list of str, each str is a device serial number
    """
    import subprocess
    r = subprocess.check_output(["adb", "devices"])
    if not isinstance(r, str):
        r = r.decode()
    devices = []
    for line in r.splitlines():
        segs = line.strip().split()
        if len(segs) == 2 and segs[1] == "device":
            devices.append(segs[0])
    return devices
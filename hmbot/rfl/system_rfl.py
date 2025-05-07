from ..connector.adb import ADB
from ..connector.hdc import HDC
from ..automator.u2 import U2
from ..automator.h2 import H2
from ..proto import OperatingSystem

system_rfl = {
    OperatingSystem.ANDROID: (ADB, U2),
    OperatingSystem.HARMONY: (HDC, H2)
}
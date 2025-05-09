from abc import ABC, abstractmethod

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
    def execute_test_case(self):
        pass

class AudioGenerator(Generator):
    def __init__(self, wtg, devices):
        self.wtg = wtg
        self.src_device = devices[0]


    def generate_test_case(self):
        pass

    def execute_test_case(self):
        pass
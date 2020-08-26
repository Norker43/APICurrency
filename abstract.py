from abc import ABC, abstractmethod

class abs_api(ABC):
    @abstractmethod
    def parse(self):
        pass

    @abstractmethod
    def server(self):
        pass


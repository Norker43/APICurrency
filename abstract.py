from abc import ABC, abstractmethod

class abs_api(ABC):
    @abstractmethod
    def request_from_api(self):
        pass

    @abstractmethod
    def server(self):
        pass

    @abstractmethod
    def printer(self):
        pass
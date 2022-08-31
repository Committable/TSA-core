from abc import ABCMeta, abstractmethod


class Index(metaclass=ABCMeta):
    @abstractmethod
    def get_index(self):
        pass
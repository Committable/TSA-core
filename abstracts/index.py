import abc


class Index(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_index(self):
        pass

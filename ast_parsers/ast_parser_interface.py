from abc import ABCMeta, abstractmethod


class AstParserInterface(metaclass=ABCMeta):

    @abstractmethod
    def parse(self, text, start="sourceUnit"):
        pass

    @abstractmethod
    def parse_file(self, input_path, start="sourceUnit"):
        pass

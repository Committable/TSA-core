from abc import ABCMeta, abstractmethod
from abstracts.ast import ast_abstract


class AstWalkerInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_ast_json(self, source_unit, context):
        pass

    @abstractmethod
    def get_type(self):
        pass

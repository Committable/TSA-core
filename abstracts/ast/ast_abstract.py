import abstracts.ast.sol_selection_src
import abstracts.ast.sol_loop_src
import abstracts.ast.sol_sequence_src
import abstracts.ast.js_loop_src
import abstracts.ast.js_selection_src
import abstracts.ast.js_sequence_src


class AstAbstract:
    def __init__(self):
        self.indexes = {}
        self.registered = False

    def register_index(self, index_name):
        self.indexes[index_name] = getattr(
            __import__(f'abstracts.ast.{index_name}').ast, index_name)

    def is_registered(self):
        return self.registered

    def get_ast_abstract_json(self,
                              context,
                              ast=None,
                              ast_type='legacyAST',
                              source=None):
        abstract = {}
        for name, index in self.indexes.items():
            func = getattr(index.get_index_class(ast, ast_type, source),
                           'get_index')
            abstract[name] = func(context)

        return abstract

    def register_ast_abstracts(self, context):
        if self.registered:
            return
        for index in context.ast_abstracts:
            self.register_index(index)
        self.registered = True

    @classmethod
    def instance(cls, *args, **kwargs):
        if not hasattr(AstAbstract, "_instance"):
            AstAbstract._instance = AstAbstract()
        return AstAbstract._instance

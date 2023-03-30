import abstracts.ast.sol.sol_selection_src
import abstracts.ast.sol.sol_loop_src
import abstracts.ast.sol.sol_sequence_src
import abstracts.ast.js.js_loop_src
import abstracts.ast.js.js_selection_src
import abstracts.ast.js.js_sequence_src
import abstracts.ast.ts.ts_loop_src
import abstracts.ast.ts.ts_selection_src
import abstracts.ast.ts.ts_sequence_src
import abstracts.ast.move.move_loop_src
import abstracts.ast.move.move_selection_src
import abstracts.ast.move.move_sequence_src


class AstAbstract:
    def __init__(self):
        self.indexes = {}
        self.registered = False

    def register_index(self, index_name):
        sub_director = index_name.split("_")[0]
        self.indexes[index_name] = getattr(getattr(__import__(f'abstracts.ast.{sub_director}.{index_name}').ast,
                                                   sub_director),
                                           index_name)

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


def get_ast_abstract(ast, ast_type, source, context):
    ast_abstract_instance = AstAbstract.instance()
    ast_abstract_instance.register_ast_abstracts(context)
    return ast_abstract_instance.get_ast_abstract_json(
        context, ast, ast_type, source)

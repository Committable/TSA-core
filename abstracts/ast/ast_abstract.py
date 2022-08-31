import abstracts.ast.selection_src, abstracts.ast.loop_src, abstracts.ast.sequence_src


class AstAbstract:
    def __init__(self):
        self.indexes = {}

    def register_index(self, index_name):
        self.indexes[index_name] = getattr(__import__("abstracts.ast."+index_name).ast, index_name)

    def get_ast_abstract_json(self, ast=None, ast_type="legacyAST", source=None):
        abstract = {}
        for name in self.indexes:
            func = getattr(self.indexes[name].get_index_class(ast, ast_type, source), "get_index")
            abstract[name] = func()

        return abstract

    def register_ast_abstracts(self, context):
        for index in context.ast_abstracts:
            self.register_index(index)




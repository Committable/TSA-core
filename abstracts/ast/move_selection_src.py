from abstracts import index
from abstracts.ast.ast_visitor.json_ast_context import JsonAstContext
from abstracts.ast.ast_visitor.json_ast_visitor import JsonAstVisitor


class MoveSelectionSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.selection_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0
        if self.ast_type == 'moveAST':
            visitor = JsonAstVisitor(self.ast, condition, processing)
            ast_context = JsonAstContext()
            ast_context.add_data("selection", 0)
            visitor.visit(self.ast, ast_context)
            self.selection_src = ast_context.get_data("selection")

        return self.selection_src


def get_index_class(ast, ast_type, source):
    return MoveSelectionSrc(ast, ast_type, source)


def condition(node, context):
    if node["name"] in ["if_expression"]:
        return True
    else:
        return False


def processing(context):
    context.add_data("selection", context.get_data("selection") + 1)



from abstracts import index
from abstracts.ast.ast_visitor.json_ast_context import JsonAstContext
from abstracts.ast.ast_visitor.json_ast_visitor import JsonAstVisitor


class RustSequenceSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.sequence_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0
        if self.ast_type == 'rustAST':
            visitor = JsonAstVisitor(self.ast, condition, processing)
            ast_context = JsonAstContext()
            ast_context.add_data("sequence", 0)
            visitor.visit(self.ast, ast_context)
            self.sequence_src = ast_context.get_data("sequence")

        return self.sequence_src


def get_index_class(ast, ast_type, source):
    return RustSequenceSrc(ast, ast_type, source)


def condition(node, context):
    if "statement" in node["name"] or "declaration" in node["name"]:
        return True
    else:
        return False


def processing(context):
    context.add_data("sequence", context.get_data("sequence") + 1)



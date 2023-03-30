from abstracts import index
from abstracts.ast.ast_visitor.json_ast_context import JsonAstContext
from abstracts.ast.ast_visitor.json_ast_visitor import JsonAstVisitor


class JsLoopSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.repetition_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0
        if self.ast_type == 'tsAST':
            visitor = JsonAstVisitor(self.ast, condition, processing)
            ast_context = JsonAstContext()
            ast_context.add_data("repetition", 0)
            visitor.visit(self.ast, ast_context)
            self.repetition_src = ast_context.get_data("repetition")

        return self.repetition_src


def get_index_class(ast, ast_type, source):
    return JsLoopSrc(ast, ast_type, source)


def condition(node, context):
    if node["name"] in ["for_statement", "for_in_statement", "while_statement", "do_statement"]:
        return True
    else:
        return False


def processing(context):
    context.add_data("repetition", context.get_data("repetition") + 1)



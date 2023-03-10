from abstracts import index


class JsLoopSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type
        self.repetition_src = 0

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0

        self.repetition_src = 0

        if self.ast_type == 'jsAST':
            pass
        return self.repetition_src


def get_index_class(ast, ast_type, source):
    return JsLoopSrc(ast, ast_type, source)

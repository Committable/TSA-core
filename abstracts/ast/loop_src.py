from abstracts import index

from inputDealer.solidity_ast_walker import AstWalker


class LoopSrc(index.Index):
    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type

    def get_index(self):
        if not self.ast or not self.source:
            return 0
        content = self.source.get_content()

        repetition_src = 0

        if self.ast_type == "legacyAST":
            walker = AstWalker(ast_type="legacyAST")
            nodes = []
            walker.walk(self.ast, {"name": "Block"}, nodes)
            for block in nodes:
                for statement in block["children"]:
                    if statement["name"] in {"WhileStatement", "DoWhileStatement", "ForStatement"}:
                        repetition_src += 1
        elif self.ast_type == "ast":
            walker = AstWalker(ast_type="ast")
            nodes = []
            walker.walk(self.ast, {"nodeType": "Block"}, nodes)
            for node in nodes:
                if "statements" in node:
                    for statement in node["statements"]:
                        if statement["nodeType"] in {"WhileStatement", "DoWhileStatement", "ForStatement"}:
                            repetition_src += 1

        return repetition_src


def get_index_class(ast, ast_type, source):
    return LoopSrc(ast, ast_type, source)
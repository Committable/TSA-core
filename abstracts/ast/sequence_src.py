from abstracts import index
from input_dealer import solidity_ast_walker


class SequenceSrc(index.Index):

    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type

    def get_index(self, context):
        if not self.ast or not self.source:
            return 0

        sequence_src = 0

        if self.ast_type == 'legacyAST':
            walker = solidity_ast_walker.AstWalker(ast_type='legacyAST')
            nodes = []
            walker.walk(self.ast, {'name': 'FunctionDefinition'}, nodes)
            sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'name': 'EventDefinition'}, nodes)
            sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'name': 'Block'}, nodes)
            for block in nodes:
                for statement in block['children']:
                    del statement  # Unused, reserve for name hint
                    sequence_src += 1
        elif self.ast_type == 'ast':
            walker = solidity_ast_walker.AstWalker(ast_type='ast')
            nodes = []
            walker.walk(self.ast, {'nodeType': 'FunctionDefinition'}, nodes)
            sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'nodeType': 'EventDefinition'}, nodes)
            sequence_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Block'}, nodes)
            for node in nodes:
                if 'statements' in node:
                    for statement in node['statements']:
                        del statement  # Unused, reserve for name hint
                        sequence_src += 1

        return sequence_src


def get_index_class(ast, ast_type, source):
    return SequenceSrc(ast, ast_type, source)

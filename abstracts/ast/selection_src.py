from abstracts import index
from input_dealer import solidity_ast_walker


class SelectionSrc(index.Index):

    def __init__(self, ast, ast_type, source):
        self.ast = ast
        self.source = source
        self.ast_type = ast_type

    def get_index(self):
        if not self.ast or not self.source:
            return 0
        content = self.source.get_content()

        selection_src = 0

        if self.ast_type == 'legacyAST':
            walker = solidity_ast_walker.AstWalker(ast_type='legacyAST')
            nodes = []
            walker.walk(self.ast, {'name': 'Conditional'}, nodes)
            selection_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'name': 'Block'}, nodes)
            for block in nodes:
                for statement in block['children']:
                    if statement['name'] == 'ExpressionStatement':
                        pos = statement['src'].split(':')
                        if 'require(' in content[max(0, int(pos[0])-5):int(pos[0]) +
                                                 int(pos[1])]:
                            selection_src += 1
                        if 'assert(' in content[max(0, int(pos[0])-5):int(pos[0]) +
                                                int(pos[1])]:
                            selection_src += 1
                    if statement['name'] == 'IfStatement':
                        if 'children' in statement:
                            selection_src += len(statement['children']) - 1
        elif self.ast_type == 'ast':
            walker = solidity_ast_walker.AstWalker(ast_type='ast')
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Conditional'}, nodes)
            selection_src += len(nodes)
            nodes = []
            walker.walk(self.ast, {'nodeType': 'Block'}, nodes)
            for node in nodes:
                if 'statements' in node:
                    for statement in node['statements']:
                        if statement['nodeType'] == 'ExpressionStatement':
                            pos = statement['src'].split(':')
                            if 'require(' in content[int(pos[0]):int(pos[0]) +
                                                     int(pos[1])]:
                                selection_src += 1
                            if 'assert(' in content[int(pos[0]):int(pos[0]) +
                                                    int(pos[1])]:
                                selection_src += 1
                        if statement['nodeType'] == 'IfStatement':
                            if ('trueBody' in statement and
                                    statement['trueBody']):
                                selection_src += 1
                            if ('falseBody' in statement and
                                    statement['falseBody']):
                                selection_src += 1

        return selection_src


def get_index_class(ast, ast_type, source):
    return SelectionSrc(ast, ast_type, source)

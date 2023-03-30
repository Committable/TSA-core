from utils import util
from ast_parsers.solidity_parser import parser_new as parser
from ast_parsers.ast_walker_interface import AstWalkerInterface


class AntlrAstWalker(AstWalkerInterface):
    def __init__(self, ast_type='antlrAST'):
        self.diffs = None
        self.type = ast_type
        self.node_id = 0

    def get_type(self):
        return self.type
    
    def get_ast_json(self, source_unit, context):
        self.diffs = context.diff
        self.node_id = 0
        result = self._walk_to_json(source_unit)
        result['ast_type'] = self.type
        return result

    def _walk_to_json(self, node):
        result = self._walk_to_json_inner(node, 0)
        return result

    def _walk_to_json_inner(self, node, depth):
        json_result = {}
        if not isinstance(node, parser.Node):
            return json_result

        lines = (node['loc']['start']['line'], node['loc']['end']['line'] + 1)
        changed = util.intersect(self.diffs, lines)

        json_result['id'] = str(self.node_id)
        self.node_id += 1
        json_result['name'] = node['type']
        json_result['layer'] = depth
        json_result['children'] = []
        json_result['ischanged'] = changed
        json_result['src'] = f'{node["loc"]["start"]["line"]}:{node["loc"]["end"]["line"] + 1}'
        for x in node:
            if isinstance(node[x], parser.Node):
                json_result['children'].append(self._walk_to_json_inner(node[x], depth + 1))
            elif isinstance(node[x], list):
                for child in node[x]:
                    if isinstance(child, parser.Node):
                        json_result['children'].append(self._walk_to_json_inner(child, depth + 1))
        return json_result

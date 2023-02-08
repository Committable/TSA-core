from abstracts.ast import ast_abstract
from utils import util
from solidity_parser import parser_new as parser


class AntlrAstWalker:
    def __init__(self, ast_type='antlrAST', diffs=None):
        if diffs is None:
            diffs = []
        self.type = ast_type
        self.diffs = diffs
        self.node_id = 0

    def get_ast_json(self, source_unit, context):
        self.diffs = context.diff
        self.node_id = 0
        result = self.walk_to_json(source_unit, 0)
        result['ast_type'] = self.type
        return result

    def walk_to_json(self, node, depth):
        json_result = {}
        if not isinstance(node, parser.Node):
            return json_result

        lines = (node['loc']['start']['line'], node['loc']['end']['line']+1)
        changed = util.intersect(self.diffs, lines)

        json_result['id'] = str(self.node_id)
        self.node_id += 1
        json_result['name'] = node['type']
        json_result['layer'] = depth
        json_result['children'] = []
        json_result['ischanged'] = changed
        json_result['src'] = f'{node["loc"]["start"]["line"]}:{node["loc"]["end"]["line"]+1}'
        for x in node:
            if isinstance(node[x], parser.Node):
                json_result['children'].append(self.walk_to_json(node[x], depth + 1))
            elif isinstance(node[x], list):
                for child in node[x]:
                    if isinstance(child, parser.Node):
                        json_result['children'].append(self.walk_to_json(child, depth + 1))
        return json_result

    def get_ast_abstract(self, ast, source, context):
        ast_abstract_instance = ast_abstract.AstAbstract()
        ast_abstract_instance.register_ast_abstracts(context)
        return ast_abstract_instance.get_ast_abstract_json(
                context, ast, self.type, source)

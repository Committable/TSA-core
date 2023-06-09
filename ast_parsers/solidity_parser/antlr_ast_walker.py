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

    def walk(self, node, attributes, nodes):
        if isinstance(attributes, dict):
            self._walk_with_attrs(node, attributes, nodes)
        else:
            self._walk_with_list_of_attrs(node, attributes, nodes)

    def _walk_with_attrs(self, node, attributes, nodes):
        if self._check_attributes(node, attributes):
            nodes.append(node)
        else:
            for x in node:
                if isinstance(node[x], parser.Node):
                    self._walk_with_attrs(node[x], attributes, nodes)
                elif isinstance(node[x], list):
                    for child in node[x]:
                        if isinstance(child, parser.Node):
                            self._walk_with_attrs(child, attributes, nodes)

    def _walk_with_list_of_attrs(self, node, list_of_attributes, nodes):
        if self._check_list_of_attributes(node, list_of_attributes):
            nodes.append(node)
        else:
            for x in node:
                if isinstance(node[x], parser.Node):
                    self._walk_with_list_of_attrs(node[x], list_of_attributes, nodes)
                elif isinstance(node[x], list):
                    for child in node[x]:
                        if isinstance(child, parser.Node):
                            self._walk_with_list_of_attrs(child, list_of_attributes, nodes)

    def _check_attributes(self, node, attributes):
        for name in attributes:
            if name not in node or node[name] != attributes[name]:
                return False
        return True

    def _check_list_of_attributes(self, node, list_of_attributes):
        for attrs in list_of_attributes:
            if self._check_attributes(node, attrs):
                return True
        return False

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

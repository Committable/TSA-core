from abstracts.ast import ast_abstract
from utils import util
from js_parser import parser


class JsAstWalker:
    def __init__(self, ast_type='jsAST', diffs=None):
        if diffs is None:
            diffs = []
        self.type = ast_type
        self.diffs = diffs
        self.node_id = 0

    def get_ast_json(self, source_unit, context):
        self.diffs = context.diff
        self.node_id = 0
        root_cursor = source_unit.walk()
        result = self.walk_to_json(root_cursor)
        result['ast_type'] = self.type
        return result

    def walk_to_json(self, node):
        result = {}
        self._walk_to_json(node, 0, result, False)
        return result

    def _walk_to_json(self, cursor, depth, parent_json, is_child):
        node = cursor.node
        if parent_json == {}:
            json_result = parent_json
        else:
            json_result = {}
            parent_json['children'].append(json_result)
        lines = (node.start_point[0] + 1, node.end_point[0] + 2)  # start from 0 and [start, end)
        changed = util.intersect(self.diffs, lines)

        json_result['id'] = str(self.node_id)
        self.node_id += 1
        json_result['name'] = node.type
        json_result['layer'] = depth
        json_result['children'] = []
        json_result['ischanged'] = changed
        json_result['src'] = f'{node.start_point[0] + 1}:{node.end_point[0] + 2}'

        if cursor.goto_first_child():
            self._walk_to_json(cursor, depth + 1, json_result, True)
        if cursor.goto_next_sibling():
            self._walk_to_json(cursor, depth, parent_json, False)
        # retrace parent from child
        if is_child:
            cursor.goto_parent()

    def get_ast_abstract(self, ast, source, context):
        ast_abstract_instance = ast_abstract.AstAbstract.instance()
        ast_abstract_instance.register_ast_abstracts(context)
        return ast_abstract_instance.get_ast_abstract_json(
            context, ast, self.type, source)

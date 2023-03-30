from utils import util
from ast_parsers.ast_walker_interface import AstWalkerInterface


class TreeSitterAstWalker(AstWalkerInterface):
    def __init__(self, ast_type):
        self.diffs = None
        self.type = ast_type
        self.node_id = 0

    def get_type(self):
        return self.type

    def get_ast_json(self, source_unit, context):
        self.diffs = context.diff
        self.node_id = 0
        root_cursor = source_unit.walk()
        result = self._walk_to_json(root_cursor)
        result['ast_type'] = self.type
        return result

    def _walk_to_json(self, node):
        result = {}
        self._walk_to_json_inner(node, 0, result, False)
        return result

    def _walk_to_json_inner(self, cursor, depth, parent_json, is_child):
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
            self._walk_to_json_inner(cursor, depth + 1, json_result, True)
        if cursor.goto_next_sibling():
            self._walk_to_json_inner(cursor, depth, parent_json, False)
        # retrace parent from child
        if is_child:
            cursor.goto_parent()

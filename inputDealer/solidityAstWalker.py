class AstWalker:
    def __init__(self, ast_type="legacyAST", diffs=[]):
        self.type = ast_type
        self.diffs = diffs

    def walk(self, node, attributes, nodes):
        if self.type == "legacyAST":
            if isinstance(attributes, dict):
                self._walk_with_attrs_legacy(node, attributes, nodes)
            else:
                self._walk_with_list_of_attrs_legacy(node, attributes, nodes)

    def walk_to_graph(self, source, node, graph, depth):
        json_result = {}
        if node:
            if self.type == "legacyAST":
                node_id = str(node["id"])

                position = node["src"].split(":")
                tmp = self.lines_and_changed_line_from_position(source.line_break_positions,
                                                                int(position[0]),
                                                                int(position[1]))
                changed = tmp["changed"]
                graph.add_node(node_id,
                               type=node["name"],
                               depth=depth,
                               ischanged=changed,
                               position=node["src"],
                               line=tmp["lines"])

                json_result["id"] = node_id
                json_result["name"] = node["name"]
                json_result["layer"] = depth
                json_result["children"] = []
                json_result["ischanged"] = changed
                json_result["src"] = node["src"]
                json_result["lines"] = tmp["lines"]
                if depth > 2:
                    json_result["collapsed"] = True
                else:
                    json_result["collapsed"] = False

                if "children" in node and node["children"]:
                    for child in node["children"]:
                        position = child["src"].split(":")
                        tmp = self.lines_and_changed_line_from_position(source.line_break_positions,
                                                                        int(position[0]),
                                                                        int(position[1]))
                        child_changed = tmp["changed"]
                        edge_changed = changed and child_changed
                        graph.add_edge(node_id, str(child["id"]), depth=depth, before=node["name"],
                                       after=child["name"], ischanged=edge_changed)
                        json_result["children"].append(self.walk_to_graph(source, child, graph, depth+1))
                # else:
                #     start = int(position[0])
                #     end = int(position[0]) + int(position[1])
                #     graph._node[node_id]["content"] = source.content[start:end]
                #     json_result["content"] = source.content[start:end]
            elif self.type == "ast":
                nodeID = str(node["id"])

                position = node["src"].split(":")
                tmp = self.lines_and_changed_line_from_position(source.line_break_positions,
                                                                     int(position[0]),
                                                                     int(position[1]))
                changed = tmp["changed"]
                graph.add_node(nodeID, type=node["nodeType"], depth=depth,
                               ischanged=changed, position=node["src"],
                               line=tmp["lines"])

                json_result["id"] = nodeID
                json_result["name"] = node["nodeType"]
                json_result["layer"] = depth
                json_result["children"] = []
                json_result["ischanged"] = changed
                json_result["src"] = node["src"]
                json_result["lines"] = tmp["lines"]
                if depth > 2:
                    json_result["collapsed"] = True
                else:
                    json_result["collapsed"] = False

                children_num = 0
                for x in node:
                    if isinstance(node[x], dict):
                        if "nodeType" in node[x] and "src" in node[x] and "id" in node[x]:
                            position = node[x]["src"].split(":")
                            tmp = self.lines_and_changed_line_from_position(source.line_break_positions,
                                                                                 int(position[0]),
                                                                                 int(position[1]))
                            child_changed = tmp["changed"]
                            edge_changed = changed and child_changed

                            graph.add_edge(nodeID, str(node[x]["id"]), depth=depth+1, before=node["nodeType"],
                                           after=node[x]["nodeType"], ischanged=edge_changed)
                            children_num += 1
                            json_result["children"].append(self.walk_to_graph(source,
                                                                              node[x],
                                                                              graph,
                                                                              depth + 1))
                    elif isinstance(node[x], list):
                        for child in node[x]:
                            if isinstance(child, dict) and "nodeType" in child:
                                position = child["src"].split(":")
                                tmp = self.lines_and_changed_line_from_position(source.line_break_positions,
                                                                                     int(position[0]),
                                                                                     int(position[1]))
                                child_changed = tmp["changed"]
                                edge_changed = changed and child_changed

                                children_num += 1
                                graph.add_edge(nodeID, str(child["id"]), depth=depth, before=node["nodeType"],
                                               after=child["nodeType"], ischanged=edge_changed)
                                json_result["children"].append(self.walk_to_graph(source,
                                                                                  child,
                                                                                  graph,
                                                                                  depth + 1))
                if children_num == 0:
                    start = int(position[0])
                    end = int(position[0]) + int(position[1])
                    graph._node[nodeID]["content"] = source.content[start:end]
                    json_result["content"] = source.content[start:end]
        return json_result

    @classmethod
    def get_lines_from_position(cls, source, start, end):
        lines = []
        last = 0
        for n in range(0, len(source)):
            if start < source[n] and end > last:
                lines.append(n+1)
            if end < source[n]:
                break
            last = source[n]

        return lines

    def lines_and_changed_line_from_position(self, source, start, size):
        lines = AstWalker.get_lines_from_position(source, start, start+size)
        for x in lines:
            if x in self.diffs:
                return {"changed": True, "lines": lines}
        return {"changed": False, "lines": lines}

    def _walk_with_attrs_legacy(self, node, attributes, nodes):
        if self._check_attributes_legacy(node, attributes):
            nodes.append(node)
        else:
            if "children" in node and node["children"]:
                for child in node["children"]:
                    self._walk_with_attrs_legacy(child, attributes, nodes)

    def _walk_with_list_of_attrs_legacy(self, node, list_of_attributes, nodes):
        if self._check_list_of_attributes_legacy(node, list_of_attributes):
            nodes.append(node)
        else:
            if "children" in node and node["children"]:
                for child in node["children"]:
                    self._walk_with_list_of_attrs_legacy(child, list_of_attributes, nodes)

    def _check_attributes_legacy(self, node, attributes):
        for name in attributes:
            if name == "attributes":
                if "attributes" not in node or \
                        not self._check_attributes_legacy(node["attributes"],
                                                          attributes["attributes"]):
                    return False
            else:
                if name not in node or node[name] != attributes[name]:
                    return False
        return True

    def _check_list_of_attributes_legacy(self, node, list_of_attributes):
        for attrs in list_of_attributes:
            if self._check_attributes_legacy(node, attrs):
                return True
        return False

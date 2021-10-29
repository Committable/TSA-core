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
        if self.type == "ast":
            if isinstance(attributes, dict):
                self._walk_with_attrs(node, attributes, nodes)
            else:
                self._walk_with_list_of_attrs(node, attributes, nodes)


    def walk_to_json(self, source, node, depth):
        json_result = {}
        if node:
            if self.type == "legacyAST":
                if "id" in node:
                    node_id = str(node["id"])
                else:
                    node_id = "0"

                if "src" not in node:
                    node["src"] = "0:0:-1"
                position = node["src"].split(":")
                lines = source.get_lines_from_position(int(position[0]),
                                                       int(position[0]) + int(position[1]))
                changed = self.is_changed(lines)

                json_result["id"] = node_id
                json_result["name"] = node["name"]
                json_result["layer"] = depth
                json_result["children"] = []
                json_result["ischanged"] = changed
                json_result["src"] = node["src"]
                json_result["lines"] = lines
                if depth > 2:
                    json_result["collapsed"] = True
                else:
                    json_result["collapsed"] = False

                if "children" in node and node["children"]:
                    for child in node["children"]:
                        json_result["children"].append(self.walk_to_json(source, child, depth+1))
            elif self.type == "ast":
                nodeID = str(node["id"])

                position = node["src"].split(":")
                lines = source.get_lines_from_position(int(position[0]),
                                                       int(position[0]) + int(position[1]))
                changed = self.is_changed(lines)

                json_result["id"] = nodeID
                json_result["name"] = node["nodeType"]
                json_result["layer"] = depth
                json_result["children"] = []
                json_result["ischanged"] = changed
                json_result["src"] = node["src"]
                json_result["lines"] = lines
                if depth > 2:
                    json_result["collapsed"] = True
                else:
                    json_result["collapsed"] = False
                for x in node:
                    if isinstance(node[x], dict):
                        if "nodeType" in node[x] and "src" in node[x] and "id" in node[x]:
                            json_result["children"].append(self.walk_to_json(source,
                                                                              node[x],
                                                                              depth + 1))
                    elif isinstance(node[x], list):
                        for child in node[x]:
                            if isinstance(child, dict) and "nodeType" in child:
                                json_result["children"].append(self.walk_to_json(source,
                                                                                 child,
                                                                                 depth + 1))
        return json_result

    def is_changed(self, lines):
        for x in lines:
            if x in self.diffs:
                return True
        else:
            return False

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

    def _walk_with_attrs(self, node, attributes, nodes):
        if self._check_attributes(node, attributes):
            nodes.append(node)
        else:
            if "nodes" in node and node["nodes"]:
                for node in node["nodes"]:
                    self._walk_with_attrs(node, attributes, nodes)
            if "body" in node and node["body"]:
                for node in node["body"]:
                    self._walk_with_attrs(node, attributes, nodes)
            if "statements" in node and node["statements"]:
                for node in node["statements"]:
                    self._walk_with_attrs(node, attributes, nodes)
            if "trueBody" in node and node["trueBody"]:
                for node in node["trueBody"]:
                    self._walk_with_attrs(node, attributes, nodes)
            if "falseBody" in node and node["falseBody"]:
                for node in node["falseBody"]:
                    self._walk_with_attrs(node, attributes, nodes)


    def _walk_with_list_of_attrs(self, node, list_of_attributes, nodes):
        if self._check_list_of_attributes(node, list_of_attributes):
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

    def _check_attributes(self, node, attributes):
        for name in attributes:
            if name == "attributes":
                if "attributes" not in node or \
                        not self._check_attributes(node["attributes"],
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

    def _check_list_of_attributes(self, node, list_of_attributes):
        for attrs in list_of_attributes:
            if self._check_attributes(node, attrs):
                return True
        return False

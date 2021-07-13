class AstWalker:

    def walk(self, node, attributes, nodes):
        if isinstance(attributes, dict):
            self._walk_with_attrs(node, attributes, nodes)
        else:
            self._walk_with_list_of_attrs(node, attributes, nodes)

    def walkToGraph(self, nodeID, node, graph, depth, sequence):
        if node:
            graph.add_node(nodeID, type=node["name"], depth=depth, sequence=sequence)
            if "children" in node and node["children"]:
                i = 0
                for child in node["children"]:
                    # if child["name"] not in ["VariableDeclaration","ParameterList","InheritanceSpecifier","Identifier","IndexAccess"]:
                    # if child["name"] in ["ContractDefinition", "FunctionDefinition","Block","ExpressionStatement","Assignment", "FunctionCall", "IndexAccess","MemberAccess","Identifier"]:
                    graph.add_edge(nodeID, nodeID+"."+str(i), depth=depth, before=node["name"], after=child["name"])
                    self.walkToGraph(nodeID+"."+str(i), child, graph, depth+1, i)
                    i = i + 1
        return


    def _walk_with_attrs(self, node, attributes, nodes):
        if self._check_attributes(node, attributes):
            nodes.append(node)
        else:
            if "children" in node and node["children"]:
                for child in node["children"]:
                    self._walk_with_attrs(child, attributes, nodes)

    def _walk_with_list_of_attrs(self, node, list_of_attributes, nodes):
        if self._check_list_of_attributes(node, list_of_attributes):
            nodes.append(node)
        else:
            if "children" in node and node["children"]:
                for child in node["children"]:
                    self._walk_with_list_of_attrs(child, list_of_attributes, nodes)

    def _check_attributes(self, node, attributes):
        for name in attributes:
            if name == "attributes":
                if "attributes" not in node or not self._check_attributes(node["attributes"], attributes["attributes"]):
                    return False
            else:
                if name not in node or node[name] != attributes[name]:
                    return False
        return True

    def _check_list_of_attributes(self, node, list_of_attributes):
        for attrs in list_of_attributes:
            if self._check_attributes(node, attrs):
                return True
        return False

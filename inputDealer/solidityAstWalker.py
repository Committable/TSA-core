import global_params
class AstWalker:

    def walk(self, node, attributes, nodes):
        if isinstance(attributes, dict):
            self._walk_with_attrs(node, attributes, nodes)
        else:
            self._walk_with_list_of_attrs(node, attributes, nodes)

    def walkToGraph(self, nodeID, node, graph, depth, sequence):
        if node:
            if global_params.PROJECT == "uniswap-v2-core":
                graph.add_node(nodeID, type=node["name"], depth=depth, sequence=sequence)
                if "children" in node and node["children"]:
                    i = 0
                    for child in node["children"]:
                        # if child["name"] not in ["VariableDeclaration","ParameterList","InheritanceSpecifier","Identifier","IndexAccess"]:
                        # if child["name"] in ["ContractDefinition", "FunctionDefinition","Block","ExpressionStatement","Assignment", "FunctionCall", "IndexAccess","MemberAccess","Identifier"]:
                        graph.add_edge(nodeID, nodeID+"."+str(i), depth=depth, before=node["name"], after=child["name"])
                        self.walkToGraph(nodeID+"."+str(i), child, graph, depth+1, i)
                        i = i + 1
            elif global_params.PROJECT == "openzeppelin-contracts":
                graph.add_node(nodeID, type=node["nodeType"], depth=depth, sequence=sequence)
                i = 0
                # if "nodes" in node and node["nodes"]:
                #     for child in node["nodes"]:
                #         # if child["name"] not in ["VariableDeclaration","ParameterList","InheritanceSpecifier","Identifier","IndexAccess"]:
                #         # if child["name"] in ["ContractDefinition", "FunctionDefinition","Block","ExpressionStatement","Assignment", "FunctionCall", "IndexAccess","MemberAccess","Identifier"]:
                #         graph.add_edge(nodeID, nodeID + "." + str(i), depth=depth, before=node["nodeType"],
                #                        after=child["nodeType"])
                #         self.walkToGraph(nodeID + "." + str(i), child, graph, depth + 1, i)
                #         i = i + 1
                for x in node:
                    if isinstance(node[x], dict):
                        if "nodeType" in node[x]:
                            graph.add_node(nodeID+"."+str(i), type=node[x]["nodeType"], depth=depth, sequence=sequence)
                            graph.add_edge(nodeID, nodeID + "." + str(i), depth=depth, before=node["nodeType"],
                                           after=node[x]["nodeType"])
                            for y in node[x]:
                                if isinstance(node[x][y], list):
                                    j = 0
                                    for child in node[x][y]:
                                        # if child["name"] not in ["VariableDeclaration","ParameterList","InheritanceSpecifier","Identifier","IndexAccess"]:
                                        # if child["name"] in ["ContractDefinition", "FunctionDefinition","Block","ExpressionStatement","Assignment", "FunctionCall", "IndexAccess","MemberAccess","Identifier"]:
                                        if isinstance(child, dict) and "nodeType" in child:
                                            graph.add_edge(nodeID+"."+str(i), nodeID + "." + str(i)+"."+str(j), depth=depth+1,
                                                           before=node[x]["nodeType"],
                                                           after=child["nodeType"])
                                            self.walkToGraph(nodeID + "." + str(i)+"."+str(j), child, graph, depth + 1, j)
                                            j = j + 1
                            i = i+1


                    elif isinstance(node[x], list):
                        for child in node[x]:
                            # if child["name"] not in ["VariableDeclaration","ParameterList","InheritanceSpecifier","Identifier","IndexAccess"]:
                            # if child["name"] in ["ContractDefinition", "FunctionDefinition","Block","ExpressionStatement","Assignment", "FunctionCall", "IndexAccess","MemberAccess","Identifier"]:
                            if isinstance(child, dict) and "nodeType" in child:
                                graph.add_edge(nodeID, nodeID + "." + str(i), depth=depth, before=node["nodeType"],
                                               after=child["nodeType"])
                                self.walkToGraph(nodeID + "." + str(i), child, graph, depth + 1, i)
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

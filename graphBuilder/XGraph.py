import networkx as nx



class Node:

    def __init__(self, nodeID):
        self.nodeID = nodeID

    def getFromNodes(self, graph):
        return list(graph.perdecessors(self))

    def getToNodes(self, graph):
        return list(graph.successors(self))


class InstructionNode(Node):

    def __init__(self, instruction_name, arguments, global_pc, constraint, nodeID):
        super().__init__(nodeID)
        self.name = instruction_name
        self.arguments = arguments
        self.global_pc = global_pc
        self.constraint = constraint

    def getConstraints(self):
        return self.constraint

    def getArguments(self):
        return self.arguments


class MessageCallNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, nodeID):
        super().__init__(instruction_name, arguments, global_pc, constraint, nodeID)

    def __str__(self):
        return "MessageCallNode " + self.name + " " + str(self.nodeID)


class StateOPNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, nodeID):
        super().__init__(instruction_name, arguments, global_pc, constraint, nodeID)

    def __str__(self):
        return "StateOPNode " + self.name + " " + str(self.nodeID)


class VariableNode(Node):

    def __init__(self, name, value, nodeID):
        super().__init__(nodeID)
        self.name = name
        self.value = value


class StateNode(VariableNode):

    def __init__(self, source, name, value, position, nodeID):
        super().__init__(name, value, nodeID)
        if source == "Ia":
            self.position = position
        else:
            self.position = -1

    def __str__(self):
        return "StateNode " + str(self.name) + " " + str(self.nodeID)


class ConstNode(VariableNode):

    def __init__(self, name, value, nodeID):
        super().__init__(name, value, nodeID)

    def __str__(self):
        return "ConstNode " + str(self.value) + " " + str(self.nodeID)


class InputDataNode(VariableNode):

    def __init__(self, name, value, nodeID):
        super().__init__(name, value, nodeID)

    def __str__(self):
        return "InputDataNode " + self.name + " " + str(self.nodeID)


class BlockDataNode(VariableNode):

    def __init__(self, name, value, blockNumber, nodeID):
        super().__init__(name, value, nodeID)
        if blockNumber > 0:
            self.blockNumber = blockNumber
        else:
            self.blockNumber = -1

    def __str__(self):
        return "BlockDataNode " + self.name + " " + str(self.nodeID)


class MsgDataNode(VariableNode):

    def __init__(self, name, value, nodeID):
        super().__init__(name, value, nodeID)

    def __str__(self):
        return "MsgDataNode " + self.name + " " + str(self.nodeID)


class SelfDefinedNode(VariableNode):

    def __init__(self, name, value, nodeID):
        super().__init__(name, value, nodeID)

    def __str__(self):
        return "SelfDefinedNode " + self.name + " " + str(self.nodeID)


class ArithNode(InstructionNode):

    def __init__(self, operation, operand, global_pc, expression, nodeID):
        super().__init__(operation, operand, global_pc, expression, nodeID)

    def __str__(self):
        return "ArithNode " + self.name + " " + str(self.nodeID)


class FlowEdge:

    def __init__(self, expression):
        self.expression = expression

    def getExpression(self):
        return self.expression


class ControlEdge:

    def __init__(self, constraints):
        self.constraints = constraints

    def getConstraint(self):
        return self.constraints


class XGraph:

    def __init__(self):
        self.graph = nx.DiGraph()
        self.count = 0

    def addNode(self, nodeId):
        self.count += 1
        self.graph.add_node(nodeId, count=self.count)

    def addEdges(self, edgeList, edgeType):
        self.graph.add_edges_from(edgeList, edgeType=edgeType)

    def addEdgeList(self, fromList, toNode, edgeType):
        for fromNode in fromList:
            itemEdge = [(fromNode, toNode)]
            self.graph.add_edges_from(itemEdge, edgeType=edgeType)
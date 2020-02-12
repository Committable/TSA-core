import networkx as nx


class Node:

    def __init__(self, isStartNode):
        self.isStartNode = isStartNode

    def getFromNodes(self, graph):
        return list(graph.perdecessors(self))

    def getToNodes(self, graph):
        return list(graph.successors(self))


class InstructionNode(Node):

    def __init__(self, instruction_name, arguments, global_pc, constraint, isStartNode):
        super().__init__(isStartNode)
        self.name = instruction_name
        self.arguments = arguments
        self.global_pc = global_pc
        self.constraint = constraint

    def getConstraints(self):
        return self.constraint

    def getArguments(self):
        return self.arguments


class VariableNode(Node):

    def __init__(self, name, value, isStartNode):
        super().__init__(isStartNode)
        self.name = name
        self.value = value


class StateNode(VariableNode):

    def __init__(self, source, name, value, position, isStartNode):
        super().__init__(name, value, isStartNode)
        if source == "Ia":
            self.position = position
        else:
            self.position = -1


class ConstNode(VariableNode):

    def __init__(self, name, value, isStartNode):
        super().__init__(name, value, isStartNode)


class InputDataNode(VariableNode):

    def __init__(self, name, value, isStartNode):
        super().__init__(name, value, isStartNode)


class BlockDataNode(VariableNode):

    def __init__(self, name, value, blockNumber, isStartNode):
        super().__init__(name, value, isStartNode)
        if blockNumber > 0:
            self.blockNumber = blockNumber
        else:
            self.blockNumber = -1


class MsgDataNode(VariableNode):

    def __init__(self, name, value, isStartNode):
        super().__init__(name, value, isStartNode)


class SelfDefinedNode(VariableNode):

    def __init__(self, name, value, isStartNode):
        super().__init__(name, value, isStartNode)


class ArithNode(Node):

    def __init__(self, operation, operand, expression, isStartNode):
        super().__init__(isStartNode)
        self.operation = operation
        self.operand = operand
        self.expression = expression


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

    def addNode(self, nodeId):
        self.graph.add_node(nodeId)

    def addEdges(self, edgeList, edgeType):
        self.graph.add_edges_from(edgeList, edgeType=edgeType)

    def addEdgeList(self, fromList, toNode, edgeType):
        for fromNode in fromList:
            self.graph.add_edges_from(fromNode, toNode, edgeType=edgeType)
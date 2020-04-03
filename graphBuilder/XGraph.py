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
        self.source = source
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
        # if blockNumber > 0:
        self.blockNumber = blockNumber
        # else:
        #     self.blockNumber = -1

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


class ReturnDataNode(VariableNode):

    def __init__(self, name, value, nodeID):
        super().__init__(name, value, nodeID)

    def __str__(self):
        return "ReturnDataNode " + self.name + " " + str(self.nodeID)


class TerminalNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc, constraint, nodeID):
        super().__init__(instruction_name, arguments, global_pc, constraint, nodeID)

    def __str__(self):
        return "TerminalNode " + self.name + " " + str(self.nodeID)

class ArithNode(InstructionNode):

    def __init__(self, operation, operand, global_pc, constraint, expression, param, nodeID):
        super().__init__(operation, operand, global_pc, constraint, nodeID)
        self.expression = expression
        self.params = param

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
        self.overflow_related = ('ADD', 'SUB', 'MUL', 'EXP')
        self.instruction_nodes = []
        self.message_call_nodes = []
        self.msg_data_nodes = []
        self.arith_nodes = []
        self.input_data_nodes = []
        self.block_data_nodes = []
        self.state_op_nodes = []
        self.call_nodes = []
        self.msg_sender_nodes = []
        self.state_nodes = []
        self.sstore_nodes = []
        self.sender_node = ""

    # The function for construct the graph for the contract
    def addNode(self, nodeId):
        self.count += 1
        self.graph.add_node(nodeId, count=self.count)
        if type(nodeId) == MessageCallNode:
            self.message_call_nodes.append(nodeId)
            if nodeId.name == "CALL":
                self.call_nodes.append(nodeId)
        elif type(nodeId) == StateOPNode:
            self.state_op_nodes.append(nodeId)
            if nodeId.name == "SSTORE":
                self.sstore_nodes.append(nodeId)
        elif type(nodeId) == InputDataNode:
            self.input_data_nodes.append(nodeId)
        elif type(nodeId) == BlockDataNode:
            self.block_data_nodes.append(nodeId)
        elif type(nodeId) == MsgDataNode:
            self.msg_data_nodes.append(nodeId)
            if nodeId.name == "CALLER":
                self.msg_sender_nodes.append(nodeId)
        elif type(nodeId) == StateNode:
            if nodeId.source == "Ia":
                self.state_nodes.append(nodeId)
            elif nodeId.source == "Is":
                self.sender_node = nodeId
        elif type(nodeId) == ArithNode and nodeId.name in self.overflow_related:
            self.arith_nodes.append(nodeId)

    def addEdges(self, edgeList, edgeType, branch):
        branchList = [branch]
        self.graph.add_edges_from(edgeList, label=edgeType, branchList=branchList)

    def addEdgeList(self, fromList, toNode, edgeType):
        for fromNode in fromList:
            itemEdge = [(fromNode, toNode)]
            self.graph.add_edges_from(itemEdge, label=edgeType)

    def addBranchEdge(self, edgeList, edgeType, branch):
        for edge in edgeList:
            if self.graph.has_edge(edge[0], edge[1]) and self.graph[edge[0]][edge[1]]["label"] == edgeType:
                self.graph[edge[0]][edge[1]]["branchList"].append(branch)
            else:
                self.graph.add_edge(edge[0], edge[1], label=edgeType, branchList=[branch])

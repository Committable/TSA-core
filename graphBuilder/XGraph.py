import networkx as nx


class Node:

    def __init__(self, fromNodes = None, toNodes = None):
        self.fromeNodes = fromNodes
        self.toNodes = toNodes

    def getFromNodes(self, graph):
        if self.fromeNodes is None:
            self.fromeNodes = list(graph.perdecessors(self))
        return self.fromeNodes

    def getToNodes(self, graph):
        if self.toNodes is None:
            self.toNodes = list(graph.successors(self))
        return self.toNodes

class ExpressionNode:
    def __init__(self, expression):
        self.expression = expression

    def get_expression(self):
        return self.expression

    def set_expression(self, expression):
        self.expression = expression

class InstructionNode(Node):

    def __init__(self, instruction_name, arguments, global_pc, constraint):
        super().__init__()
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

    def __init__(self, name, value):
        super().__init__()
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

    def __init__(self, name, value):
        super().__init__(name, value)

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

    def __init__(self, operation, operand, global_pc, constraint, expression, param):
        super().__init__(operation, operand, global_pc, constraint)
        self.expression = expression
        self.params = param

    def __str__(self):
        return "ArithNode " + self.name + " " + str(self.nodeID)


# a up-down tree structure, with the sym_var represent the ultimate symbolic_var node
class SymVarTree:
    def __init__(self, nodes, flow_edges, control_edges, sym_var_node):
        self.nodes = nodes
        self.flow_edges = flow_edges
        self.control_edges = control_edges
        self.sym_var_node = sym_var_node


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
        self.instruction_nodes = []  # TODO: add comment
        self.message_call_nodes = []  # all nodes included in {call, staticcall, delegatecall, callcode}
        self.msg_data_nodes = []  # TODO: add comment
        self.arith_nodes = []  # only for {"add", "sub", "mul", "exp"}
        self.input_data_nodes = []  # for {calldataload, calldatacopy}
        self.block_data_nodes = []  # for {blockhash}
        self.state_op_nodes = []  # all nodes included in {sstore, sload}
        self.call_nodes = []  # for call instruction
        self.msg_sender_nodes = []
        self.state_nodes = []
        self.sstore_nodes = []  # for sstore instruction
        self.sender_node = ""  # for msg.sender

        # (symbolicVar, variableNode), mapping symbolic var to variableNodes
        self.mapping_sym_node = {}

        # (const, constNode), mapping real int to constNodes
        self.mapping_const_node = {}

    def getSymVariableNode(self, var):
        if var in self.mapping_sym_node:
            return self.mapping_sym_node[var]
        else:
            raise Exception("no match node for a symbolic var")

    def addSymVariableNode(self, var, node):
        self.mapping_sym_node[var] = node

    def getConstNode(self, const):
        if const in self.mapping_const_node:
            return self.mapping_const_node[const]
        else:
            node = ConstNode(const, const)
            self.mapping_const_node[const] = node
            return node

    # The function for construct the graph for the contract
    def addNode(self, node):
        self.count += 1
        self.graph.add_node(node, count=self.count)
        if type(node) == MessageCallNode:
            self.message_call_nodes.append(node)
            if node.name == "CALL":
                self.call_nodes.append(node)
        elif type(node) == StateOPNode:
            self.state_op_nodes.append(node)
            if node.name == "SSTORE":
                self.sstore_nodes.append(node)
        elif type(node) == InputDataNode:
            self.input_data_nodes.append(node)
        elif type(node) == BlockDataNode:
            self.block_data_nodes.append(node)
        elif type(node) == MsgDataNode:
            self.msg_data_nodes.append(node)
            if node.name == "CALLER":
                self.msg_sender_nodes.append(node)
        elif type(node) == StateNode:
            if node.source == "Ia":
                self.state_nodes.append(node)
            elif node.source == "Is":
                self.sender_node = node
        elif type(node) == ArithNode and node.name in self.overflow_related:
            self.arith_nodes.append(node)

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

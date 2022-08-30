import networkx as nx
import z3
from z3 import z3util

import log
import utils


class Node:
    count = 0

    def __init__(self, name, from_nodes=None, to_nodes=None):
        if to_nodes is None:
            to_nodes = set()
        if from_nodes is None:
            from_nodes = set()
        self.count = Node.count  # the node number of this node
        self.name = name
        self.from_nodes = from_nodes
        self.to_nodes = to_nodes

        Node.count += 1

    def get_from_nodes(self):
        return self.from_nodes

    def add_from_node(self, node):
        self.from_nodes.add(node)

    def add_to_node(self, node):
        self.to_nodes.add(node)

    def get_to_nodes(self):
        return self.to_nodes

    def __str__(self):
        return ('Node_' + self.name).replace('\n', '')


class InstructionNode(Node):
    """Node for instructions like SSTORE, CALL, STATICCALL, etc..

    Attributes:
        arguments: for nodes of arguments in different paths, e.g.
            for SSTORE: [[node1,node1], [node2,node3]], (node1, node2)
            be the address and value of one path.
        labels: the label of different arguments, e.g. for SSTORE,
            {0:'address', 1:'value), means first argument is 'address',
            second argument is 'value'.
        pc: global program counter for the instruction.
    """

    def __init__(self, instruction_name, arguments, global_pc, labels=None):
        """Init instruction node.

        Args:
            instruction_name: opcode name.
            arguments: for nodes of arguments in different paths, e.g.
                for SSTORE: [[node1,node1], [node2,node3]], (node1, node2)
                be the address and value of one path.
            global_pc: global program counter for the instruction.
            labels: the label of different arguments, e.g. for SSTORE,
                {0:'address', 1:'value), means first argument is 'address',
                second argument is 'value'.

        Returns:
        Raises:
        """
        super().__init__(instruction_name)
        self.arguments = arguments
        self.labels = labels
        self.pc = global_pc
        if XGraph.sourcemap is not None and len(
                XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)

    def get_pc(self):
        return self.pc

    def get_arguments(self):
        return self.arguments

    def set_labels(self, labels):
        self.labels = labels

    def add_arguments(self, node, index):
        self.arguments[index].append(node)

    def get_label(self, i):
        return self.labels[i]

    def __str__(self):
        return 'InstructionNode_' + self.name + '_' + str(self.pc)


class MessageCallNode(InstructionNode):

    def __init__(self, instruction_name, arguments, global_pc):
        super().__init__(instruction_name, arguments, global_pc)
        if self.name in ('DELEGATECALL', 'STATICCALL'):
            labels = {
                0: 'gas',
                1: 'recipient',
                2: 'start_input',
                3: 'size_input',
                4: 'start_output',
                5: 'size_output'
            }
        else:
            labels = {
                0: 'gas',
                1: 'recipient',
                2: 'transfer',
                3: 'start_input',
                4: 'size_input',
                5: 'start_output',
                6: 'size_output'
            }
        self.set_labels(labels)

    def __str__(self):
        if len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            return (self.name + '::' +
                    XGraph.sourcemap.get_contents_from_pc(self.pc)).replace(
                        '\n', '')
        return (self.name + '::' + str(self.pc)).replace('\n', '')


class SStoreNode(InstructionNode):

    def __init__(self, instruction_name, global_pc, arguments):
        super().__init__(instruction_name, arguments, global_pc)
        labels = {0: 'address', 1: 'value'}
        self.set_labels(labels)

    def __str__(self):
        if len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            return ('Write::' +
                    XGraph.sourcemap.get_contents_from_pc(self.pc)).replace(
                        '\n', '')
        else:
            return 'Write::' + str(self.pc)


class TerminalNode(InstructionNode):

    def __init__(self, instruction_name, global_pc):
        super().__init__(instruction_name, [], global_pc)

    def __str__(self):
        return self.name


class ArithNode(InstructionNode):

    def __init__(self, operation, operands, global_pc):
        super().__init__(operation, operands, global_pc)

    def __str__(self):
        return ('ArithNode_' + self.name + '_' + str(self.pc)).replace('\n', '')


class VariableNode(Node):

    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def get_value(self):
        return self.value

    def __str__(self):
        return 'var_' + str(self.count)


class ConstNode(VariableNode):

    def __str__(self):
        return str(self.value).replace('\n', '')


class ExpressionNode(VariableNode):

    def __str__(self):
        return 'EXPR_' + str(self.count)


class ConstraintNode(VariableNode):

    def __init__(self, value, pc, path, name=''):
        super().__init__(name, value)
        self.pc = pc

        # len(paths) == len(values) and value of index i means
        # the constraint expression of path of index i

        self.values = [value]
        self.paths = [path]
        self.name = name

        if XGraph.sourcemap:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)
        else:
            self.lines = []

    def add_constraint(self, value, path):
        self.values.append(value)
        self.paths.append(path)

    def __str__(self):
        if self.name:
            return self.name
        if XGraph.sourcemap is None or len(self.lines) != 1:
            return 'BRANCH_' + str(self.pc)
        else:
            return XGraph.sourcemap.get_contents_from_pc(self.pc).replace(
                '\n', '')


class StateNode(VariableNode):

    def __init__(self, name, value, position, pc):
        super().__init__(name, value)
        self.position = position
        self.pc = pc
        if XGraph.sourcemap is not None and len(
                XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)

    def get_position(self):
        return self.position

    def __str__(self):
        if len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            return ('State::' +
                    XGraph.sourcemap.get_contents_from_pc(self.pc)).replace(
                        '\n', '')
        else:
            return 'State::' + str(self.pc)


class InputDataNode(VariableNode):

    def __init__(self, name, value, start, end):  # include start, exclude end
        super().__init__(name, value)
        self.start = start
        self.end = end

    def __str__(self):
        if z3.is_expr(self.start) or z3.is_expr(self.end):
            return 'input_' + str(self.count)
        else:
            return 'input_' + str(self.start) + '_' + str(self.end)


class InputDataSizeNode(VariableNode):

    def __str__(self):
        return 'inputSize'


class ExpNode(VariableNode):

    def __init__(self, name, value, base, exponent):
        super().__init__(name, value)
        self.base = base
        self.exponent = exponent

    def get_base(self):
        return self.base

    def get_exponent(self):
        return self.exponent

    def __str__(self):
        return 'exp_' + str(self.count)


class GasPriceNode(VariableNode):

    def __str__(self):
        return 'gasPrice'


class OriginNode(VariableNode):

    def __str__(self):
        return 'origin'


class CoinbaseNode(VariableNode):

    def __str__(self):
        return 'coinbase'


class DifficultyNode(VariableNode):

    def __str__(self):
        return 'difficulty'


class GasLimitNode(VariableNode):

    def __str__(self):
        return 'gasLimit'


class ChainIdNode(VariableNode):

    def __str__(self):
        return 'chainId'


class BaseFeeNode(VariableNode):

    def __str__(self):
        return 'baseFee'


class BlockNumberNode(VariableNode):

    def __str__(self):
        return 'blockNum'


class TimeStampNode(VariableNode):

    def __str__(self):
        return 'timeStamp'


class AddressNode(VariableNode):

    def __str__(self):
        label = 'symbolic_value'
        try:
            label = '0x' + str(
                format(int(str(z3.simplify(utils.to_symbolic(self.value)))),
                       '040x'))
        except:  # pylint: disable=bare-except
            pass
        return 'Address(' + label + ')'.replace('\n', '')


class BlockhashNode(VariableNode):

    def __init__(self, name, value, block_number):
        super().__init__(name, value)
        self.block_number = block_number

    def get_block_number(self):
        return self.block_number

    def __str__(self):
        return ('Blockhash_' + str(self.count)).replace('\n', '')


class GasNode(VariableNode):

    def __str__(self):
        return ('Gas_' + str(self.count)).replace('\n', '')


class ShaNode(VariableNode):

    def __init__(self, name, value, pc, param=None):
        super().__init__(name, value)
        self.param = param
        self.pc = pc

    # param may be None
    def get_param(self):
        return self.param

    def __str__(self):
        if len(XGraph.sourcemap.get_lines_from_pc(self.pc)) == 1:
            self.lines = XGraph.sourcemap.get_lines_from_pc(self.pc)
            return ('SHA_' +
                    XGraph.sourcemap.get_contents_from_pc(self.pc)).replace(
                        '\n', '')
        else:
            return ('SHA_' + str(self.pc)).replace('\n', '')


class MemoryNode(VariableNode):  # 32 bytes

    def __init__(self, name, value, position):
        super().__init__(name, value)
        self.position = position  # start offset of the memory symbolic variable

    def get_position(self):
        return self.position

    def __str__(self):
        return ('MemoryNode_' + str(self.count)).replace('\n', '')


class ExtcodeSizeNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def get_address(self):
        return self.address

    def __str__(self):
        return ('ExtcodeSizeNode_' + str(self.count)).replace('\n', '')


class ExtcodeHashNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def get_address(self):
        return self.address

    def __str__(self):
        return ('ExtcodeHashNode_' + str(self.count)).replace('\n', '')


class DepositValueNode(VariableNode):

    def __str__(self):
        return 'Iv'


class BalanceNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def get_address(self):
        return self.address

    def __str__(self):
        return ('balance_' + str(self.count)).replace('\n', '')


class ReturnDataNode(VariableNode):

    def __str__(self):
        return ('ReturnDataNode_' + str(self.count)).replace('\n', '')


class ReturnStatusNode(VariableNode):

    def __init__(self, name, value, pc):
        super().__init__(name, value)
        self.pc = pc

    def __str__(self):
        return 'ReturnStatus_' + str(self.pc)


class ReturnDataSizeNode(VariableNode):

    def __str__(self):
        return ('ReturnDataSizeNode_' + str(self.count)).replace('\n', '')


class CodeNode(VariableNode):

    def __init__(self, name, value, address):
        super().__init__(name, value)
        self.address = address

    def __str__(self):
        return ('CodeNode_' + str(self.count)).replace('\n', '')


class SenderNode(VariableNode):

    def __str__(self):
        return 'msg.sender'


class ReceiverNode(VariableNode):

    def __str__(self):
        return 'msg.receiver'


class XGraph:
    sourcemap = None

    def __init__(self, cname, sourcemap=None):
        XGraph.sourcemap = sourcemap

        # @global is the default func
        self.graphs = {'@global': nx.DiGraph(name=cname)}
        self.current_function = '@global'

        # nodes in graph
        self.arith_nodes = set()  # only for {'add', 'sub', 'mul', 'exp'}
        self.input_data_nodes = set()  # for {calldataload, calldatacopy}
        self.terminal_nodes = set()  # for 'revert'
        self.sender_node = None  # for msg.sender
        self.receiver_node = None  # for receiver
        self.deposit_value_node = None  # Iv
        self.origin_node = None  # for 'origin'
        self.coin_base_node = None
        self.difficulty_node = None
        self.gas_limit_node = None
        self.time_stamp_node = None
        self.block_number_nodes = set()
        self.exp_nodes = set()
        self.sha_nodes = set()
        self.blockhash_nodes = set()
        self.return_status_nodes = set()  # for all return status nodes
        # (expr, ExpressionNode)
        self.mapping_expr_node = {}
        # (constrain, ConstrainNode)
        self.mapping_constraint_node = {}
        # (expr/var, AddressNode)
        self.mapping_address_node = {}
        # (pc, MessageCallNode)
        self.mapping_pc_message_call_node = {}
        # (pc, StateOpNode)
        self.mapping_pc_state_op_node = {}
        # (pc, TerminalNode(
        self.mapping_pc_terminal_node = {}
        # (position, StateNode)
        self.mapping_position_state_node = {}
        # (address, BalanceNode)
        self.mapping_address_balance_node = {}
        # constraint tree root
        self.constraint_root = None

        # TODO(Chao): Move to method docstring
        # nodes may not in graph, but cached
        # (Var, VariableNode), mapping symbolic variable or real int to
        # variableNodes or constNodes
        self.mapping_var_node = {}

    # add and initial a DiGraph for a function
    def add_func_graph(self, function_name):
        self.graphs[function_name] = nx.DiGraph(name=function_name)

    # get the DiGraph of a function by function name
    def get_func_graph(self, function_name):
        if function_name in self.graphs:
            return self.graphs[function_name]
        else:
            return None

    # add a variable node to mapping_var_node indexed by var(symbolic or const)
    # without adding to graph
    def cache_var_node(self, var, node):
        if var in self.mapping_var_node:
            return self.mapping_var_node[var]
        self.mapping_var_node[var] = node
        return node

    # add a const or variable node of var value and add it to graph:
    # if cached in mapping_var_node, add the node;
    # if not cached in mapping_var_node, create a new node.
    def add_var(self, var):
        if var in self.mapping_var_node:
            self._add_node(self.mapping_var_node[var])
            return self.mapping_var_node[var]
        else:
            if z3.is_expr(var):
                node = VariableNode(str(var), var)
            else:
                node = ConstNode(str(var), var)
            return self.add_var_node(var, node)

    # add a const or variable node to graph,
    # if cached in mapping_var_node, add the old node
    def add_var_node(self, var, node):
        node = self.cache_var_node(var, node)
        self._add_node(node)
        return node

    # edge_list: nodes, e.g. [(n1, n2), (n3, n4)]
    # edge_type: value_flow, constraint_flow, control_flow
    # path: path id, e.g. 11...
    # label: edge's label in this path, e.g. position, value, from, to
    # path and label should both be None or given value
    def add_branch_edge(self, edge_list, edge_type, path=None, label=None):
        graph = self.graphs[self.current_function]
        for edge in edge_list:
            if graph.has_edge(
                    edge[0],
                    edge[1]) and graph[edge[0]][edge[1]]['type'] == edge_type:
                if path and label:
                    graph[edge[0]][edge[1]]['paths'].append(path)
                    graph[edge[0]][edge[1]]['labels'].append(label)
            elif graph.has_edge(
                    edge[0],
                    edge[1]) and graph[edge[0]][edge[1]]['type'] != edge_type:
                log.mylogger.error('(%s, %s) are both %s and %s', str(edge[0]),
                                   str(edge[1]),
                                   graph[edge[0]][edge[1]]['type'], edge_type)
            else:
                if path and label:
                    graph.add_edge(edge[0],
                                   edge[1],
                                   type=edge_type,
                                   paths=[path],
                                   labels=[label])
                else:
                    graph.add_edge(edge[0],
                                   edge[1],
                                   type=edge_type,
                                   paths=[],
                                   labels=[])

    # add an expression node of expr value to graph,
    # if cached in mapping_expr_node, add the old node
    def add_expression_node(self, expr):
        # be a const or a variable, e.g. 0 or BitVecVal('a', 256)
        if not z3.is_expr(expr) or z3.is_const(expr):
            return self.add_var(expr)
        graph = self.graphs[self.current_function]
        # search expr in mapping_expr_node, and add it to graph
        for key, e_node in self.mapping_expr_node.items():
            if utils.convert_result_to_int(key - expr) == 0:
                if not graph.has_node(e_node):
                    graph.add_node(e_node)
                    flow_edges = []
                    for n in e_node.get_from_nodes():
                        flow_edges.append((n, e_node))
                        if not graph.has_node(n):
                            graph.add_node(n)
                    self.add_branch_edge(flow_edges, 'value_flow')
                return e_node
        # expr not in mapping_expr_node, create it and add it to
        # mapping_expr_node and graph
        e_node = ExpressionNode(str(expr), expr)
        self.mapping_expr_node[expr] = e_node
        graph.add_node(e_node)

        flow_edges = []
        for var in z3util.get_vars(expr):
            node = self.add_var(var)
            e_node.add_from_node(node)
            flow_edges.append((node, e_node))
        self.add_branch_edge(flow_edges, 'value_flow')
        return e_node

    # add a constraint node of constraint
    def add_constraint_node(self, path_conditions, pc, path, name=''):
        constraint = path_conditions['path_condition'][-1]
        constraint_nodes = path_conditions['path_condition_node']
        branch_flags = path_conditions['branch_flag']

        e_node = self.get_constraint_node(pc)
        if e_node is None:
            e_node = ConstraintNode(constraint, pc, path, name)
            # # data_flow from variable to constraint
            # flow_edges = []
            # if not is_const(constraint):
            #     for var in get_vars(constraint):
            #         node = self.get_var_node(var)
            #         flow_edges.append((node, e_node))
            # self.add_branch_edge(flow_edges, 'value_flow', None)
            self.mapping_constraint_node[pc] = e_node
        else:
            e_node.add_constraint(constraint, path)

        graph = self.graphs[self.current_function]
        graph.add_node(e_node)
        if len(constraint_nodes) > 0:
            if not graph.has_node(constraint_nodes[-1]):
                graph.add_node(constraint_nodes[-1])
            self.add_branch_edge([(constraint_nodes[-1], e_node)],
                                 'control_flow', path, str(branch_flags[-2]))

        path_conditions['path_condition_node'].append(e_node)
        return e_node

    def get_constraint_node(self, key):
        if key in self.mapping_constraint_node:
            return self.mapping_constraint_node[key]
        else:
            return None

    def add_message_call_node(self, name, pc, parameters, return_node, path_id,
                              path_conditions):
        if pc in self.mapping_pc_message_call_node:
            node = self.mapping_pc_message_call_node[pc]
        else:
            if name in ('DELEGATECALL', 'STATICCALL'):
                node = MessageCallNode(name, [[], [], [], [], [], []], pc)
            else:
                node = MessageCallNode(name, [[], [], [], [], [], [], []], pc)
            self.mapping_pc_message_call_node[pc] = node
        for i in range(0, len(parameters)):
            if i == 1:
                p_node = self.add_address_node(parameters[i])
            else:
                p_node = self.add_expression_node(parameters[i])
            node.add_arguments(p_node, i)
            self.add_branch_edge([(p_node, node)], 'value_flow', path_id,
                                 node.get_label(i))

        self.add_var_node(return_node.get_value(), return_node)
        self.add_branch_edge([(node, return_node)], 'value_flow')

        # add constraints for this instruction
        constraint_nodes = path_conditions['path_condition_node']
        if len(constraint_nodes) > 0:
            c_node = constraint_nodes[-1]
            flag = path_conditions['branch_flag'][-1]
            self.add_branch_edge([(c_node, node)], 'constraint_flow', path_id,
                                 str(flag))

        return node

    def add_terminal_node(self, node, path_conditions, path_id):
        if node.get_pc() in self.mapping_pc_terminal_node:
            node = self.mapping_pc_terminal_node[node.get_pc()]
        else:
            self.mapping_pc_terminal_node[node.get_pc()] = node
        # add constraints for this instruction
        constraint_nodes = path_conditions['path_condition_node']
        if len(constraint_nodes) > 0:
            c_node = constraint_nodes[-1]
            flag = path_conditions['branch_flag'][-1]
            self.add_branch_edge([(c_node, node)], 'constraint_flow', path_id,
                                 str(flag))

    # add address node of expr to graph
    def add_address_node(self, expr):
        graph = self.graphs[self.current_function]

        # get address node from mapping address node
        for key, a_node in self.mapping_address_node.items():
            if utils.convert_result_to_int(key - expr) == 0:
                if not graph.has_node(a_node):
                    graph.add_node(a_node)
                flow_edge = []
                for n in a_node.get_from_nodes():
                    flow_edge.append((n, a_node))
                    if not graph.has_node(n):
                        graph.add_node(n)
                self.add_branch_edge(flow_edge, 'value_flow')
                return a_node

        # create a new address node
        a_node = AddressNode(str(expr), expr)
        self.mapping_address_node[expr] = a_node
        graph.add_node(a_node)
        flow_edges = []
        if not z3.is_expr(expr):
            node = self.add_var(expr)
            flow_edges.append((node, a_node))
            a_node.add_from_node(node)
        else:
            for var in z3util.get_vars(expr):
                node = self.add_var(var)
                flow_edges.append((node, a_node))
                a_node.add_from_node(node)
        self.add_branch_edge(flow_edges, 'value_flow')
        return a_node

    # add sstore node to graph, if not exist in mapping_pc_state_op_node,
    # create a new SStoreNode
    # opcode: the opcode of sstore instruction
    # pc: the pc of the sstore instruction
    # arguments: the arguments of the sstore instruction in this path
    # path_id: the path id of the sstore instruction of this path
    def add_sstore_node(self, opcode, pc, arguments, path_id, path_conditions):
        if pc in self.mapping_pc_state_op_node:
            node = self.mapping_pc_state_op_node[pc]
        else:
            node = SStoreNode(opcode, pc, [[], []])
        # add new arguments nodes of the sstore node for this path to
        # sstore node and arguments edges to graph
        for i in range(0, len(arguments)):
            p_node = self.add_expression_node(arguments[i])
            node.add_arguments(p_node, i)
            if node.labels is not None:
                self.add_branch_edge([(p_node, node)], 'value_flow', path_id,
                                     node.labels[i])
            else:
                self.add_branch_edge([(p_node, node)], 'value_flow', path_id,
                                     str(i))
        # add constraints for this instruction
        constraint_nodes = path_conditions['path_condition_node']
        if len(constraint_nodes) > 0:
            c_node = constraint_nodes[-1]
            flag = path_conditions['branch_flag'][-1]
            self.add_branch_edge([(c_node, node)], 'constraint_flow', path_id,
                                 str(flag))
        return node

    # add node and other necessary nodes and edges to graph
    def _add_node(self, node):
        graph = self.graphs[self.current_function]
        if graph.has_node(node):
            return
        graph.add_node(node)

        # Todo(Yang): add start and end node to input_data_node
        if isinstance(node, InputDataNode):
            self.input_data_nodes.add(node)
        elif isinstance(node, ArithNode):
            self.arith_nodes.add(node)
        elif isinstance(node, TerminalNode):
            self.terminal_nodes.add(node)
        elif isinstance(node, SenderNode):  #
            self.sender_node = node
        elif isinstance(node, ReceiverNode):  #
            self.receiver_node = node
        elif isinstance(node, ReturnStatusNode):
            self.return_status_nodes.add(node)
        elif isinstance(node, DepositValueNode):  #
            self.deposit_value_node = node
        elif isinstance(node, BalanceNode):
            # add value_flow from address_node to balance_node
            address_node = self.add_address_node(node.get_address())
            self.add_branch_edge([(address_node, node)], 'value_flow', -1,
                                 'address')
            self.mapping_address_balance_node[node.get_address()] = node
        elif isinstance(node, OriginNode):  #
            self.origin_node = node
        elif isinstance(node, CoinbaseNode):  #
            self.coin_base_node = node
        elif isinstance(node, BlockNumberNode):  #
            self.block_number_nodes.add(node)
        elif isinstance(node, DifficultyNode):  #
            self.difficulty_node = node
        elif isinstance(node, GasLimitNode):  #
            self.gas_limit_node = node
        elif isinstance(node, TimeStampNode):
            self.time_stamp_node = node
        elif isinstance(node, ExpNode):
            # add value from base_node and exponent_node to exp_node
            base_expr_node = self.add_expression_node(node.get_base())
            self.add_branch_edge([(base_expr_node, node)], 'value_flow', -1,
                                 'base')
            exponent_expr_node = self.add_expression_node(node.get_exponent())
            self.add_branch_edge([(exponent_expr_node, node)], 'value_flow', -1,
                                 'exp')
            self.exp_nodes.add(node)
        elif isinstance(node, ShaNode):
            # add value from var_node in param to sha_node
            param = node.get_param()
            if param is not None:
                if not z3.is_const(param):
                    for var in z3util.get_vars(param):
                        var_node = self.add_var(var)
                        self.add_branch_edge([(var_node, node)], 'value_flow')
                else:
                    var_node = self.add_var(param)
                    self.add_branch_edge([(var_node, node)], 'value_flow')
            self.sha_nodes.add(node)
        elif isinstance(node, ExtcodeSizeNode):
            # add value_flow from address_node to ext_code_size_node
            address_node = self.add_address_node(node.get_address())
            self.add_branch_edge([(address_node, node)], 'value_flow')
        elif isinstance(node, BlockhashNode):
            block_number_node = self.add_expression_node(
                node.get_block_number())
            self.add_branch_edge([(block_number_node, node)], 'value_flow')
            self.blockhash_nodes.add(node)
        elif isinstance(node, MemoryNode):
            position_node = self.add_expression_node(node.get_position())
            self.add_branch_edge([(position_node, node)], 'value_flow')
        elif isinstance(node, StateNode):
            position_node = self.add_expression_node(node.get_position())
            self.add_branch_edge([(position_node, node)], 'value_flow', -1,
                                 'position')

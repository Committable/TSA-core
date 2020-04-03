import re
from checker.algorithm import *
from graphBuilder.XGraph import *
from z3 import *


class Overflow:
    def __init__(self, XGraph):
        self.XGraph = XGraph
        self.Instruction = ('ADD', 'MUL', 'EXP', 'SUB')

    def check(self):
        overflow_nodes = []
        underflow_nodes = []
        taint_node_list = self.XGraph.input_data_nodes + self.XGraph.msg_data_nodes
        state_related_flow_node = self.XGraph.state_nodes + self.XGraph.message_call_nodes
        state_related_control_node = []


        # state_related_node = state_related_flow_node + state_related_control_node

        for arith_node in self.XGraph.arith_nodes:
            if arith_node.name in self.Instruction:
                if check_reachable_from_list(self.XGraph.graph, taint_node_list, arith_node):

                    for node in state_related_flow_node:
                        state_related_node = get_control_node(self.XGraph.graph, node)
                        for state_node in state_related_node:
                            if check_reach_in_same_branch(self.XGraph.graph, arith_node, state_node):
                                if arith_node.name in ('ADD', 'MUL', 'EXP'):
                                    constraint = UGT(arith_node.params[0], arith_node.expression)
                                    if query_satisfy_add_expr(arith_node, constraint):
                                        overflow_nodes.append(arith_node)
                                else:
                                    constraint = UGT(arith_node.params[1], arith_node.params[0])
                                    if query_satisfy_add_expr(arith_node, constraint):
                                        underflow_nodes.append(arith_node)
        return overflow_nodes, underflow_nodes
                        # if check_reachable_to_list(self.XGraph.graph, arith_node, state_related_node):

                            # overflow_nodes.append(arith_node)





import re
from checker.algorithm import *
from graphBuilder.XGraph import *
from z3 import *


class Overflow:
    def __init__(self, XGraph):
        self.XGraph = XGraph

    def check(self):
        overflow_nodes = []
        taint_node_list = self.XGraph.input_data_nodes + self.XGraph.msg_data_nodes
        state_related_flow_node = self.XGraph.state_nodes + self.XGraph.message_call_nodes
        state_related_control_node = []
        for node in state_related_flow_node:
            state_related_control_node = state_related_control_node + get_control_node(self.XGraph.graph, node)
        state_related_node = state_related_flow_node + state_related_control_node

        for arith_node in self.XGraph.arith_nodes:
            if check_reachable_from_list(self.XGraph.graph, taint_node_list, arith_node):
                if check_reachable_to_list(self.XGraph.graph, arith_node, state_related_node):
                    overflow_nodes.append(arith_node)





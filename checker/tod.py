import re
from checker.algorithm import *
from graphBuilder.XGraph import *
from z3 import *


class TOD:
    def __init__(self, XGraph):
        self.XGraph = XGraph

    def check(self):
        tod_nodes = []
        message_call_control_nodes = []
        taint_node_list = self.XGraph.input_data_nodes + self.XGraph.msg_data_nodes
        msg_sender_nodes = self.XGraph.msg_sender_nodes
        for message_call_node in self.XGraph.message_call_nodes:
            control_nodes = get_control_node(self.XGraph.graph, message_call_node)
            message_call_control_nodes = message_call_control_nodes + control_nodes
        message_call_related_node = message_call_control_nodes + self.XGraph.message_call_nodes
        for state_node in self.XGraph.state_nodes:

            if check_reachable_to_list(self.XGraph.graph, state_node, message_call_related_node):
                sstore_list = get_taint_sstore_list(self.XGraph.graph, state_node, taint_node_list, msg_sender_nodes)
                # sstore_nodes = self.graph.predecessors(state_node)
                # for sstore_node in sstore_nodes:
                #     if check_reachable_from_list(self.graph, taint_node_list, sstore_node):
                tod_nodes = tod_nodes + sstore_list
                # if check_storage_taintable(self.graph, state_node, taint_node_list, msg_sender_nodes):




            #
            # sstore_nodes = self.graph.predecessors(state_node)
            # sload_nodes = self.graph
            # sstore_list = get_branchID_list(self.graph, sstore_nodes, state_node)





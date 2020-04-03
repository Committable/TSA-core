import re
from checker.algorithm import *
from graphBuilder.XGraph import *
from z3 import *


class TOD:
    def __init__(self, XGraph):
        self.XGraph = XGraph

    def check(self):
        tod_nodes = []

        taint_node_list = self.XGraph.input_data_nodes + self.XGraph.msg_data_nodes
        msg_sender_nodes = self.XGraph.msg_sender_nodes
        sender_node = self.XGraph.sender_node
        for message_call_node in self.XGraph.message_call_nodes:
            message_call_related_node = get_control_node(self.XGraph.graph, message_call_node)
            # message_call_control_nodes = message_call_control_nodes + control_nodes
            # message_call_related_node = list(control_nodes).append(message_call_node)
            for state_node in self.XGraph.state_nodes:
                tod_sstore = []
                if check_reachable_to_list(self.XGraph.graph, state_node, message_call_related_node):
                    sstore_list = get_taint_sstore_list(self.XGraph.graph, state_node, taint_node_list,
                                                        msg_sender_nodes, sender_node, self.XGraph.state_nodes)
                    for sstore_node in sstore_list:
                        if query_satisfy(sstore_node, message_call_node):
                            tod_sstore.append(sstore_node)
                            tod_sstore.append(message_call_node)

                    tod_nodes = tod_nodes + tod_sstore
        return tod_nodes





import re
from checker.algorithm import *
from graphBuilder.XGraph import *
from z3 import *


class Reentrancy:
    def __init__(self, XGraph):
        self.XGraph = XGraph

    def check(self):
        reentrancy_call_node = []
        call_nodes = self.XGraph.call_nodes
        taint_node_list = self.XGraph.input_data_nodes + self.XGraph.msg_data_nodes
        for call_node in call_nodes:
            call_param = get_argument_or_flow_node(self.XGraph.graph, call_node)
            branch_id_list = self.XGraph.graph[call_param[0]][call_node]['branchList']
            branches = []
            # arguments = call_node.arguments
            outgas = call_node.arguments[0]
            recipient_node = call_node.arguments[1]
            for branch_id in branch_id_list:
                if not check_state_change(self.XGraph.graph, branch_id, call_node):
                    branches.append(branch_id)

            if len(branches) > 0:
                from_taint_list = get_reachable_list_in_branch(self.XGraph.graph, taint_node_list, recipient_node, branches)
                from_storage_list = get_reachable_list(self.XGraph.graph, self.XGraph.state_nodes, recipient_node)
                if len(from_taint_list) > 0:
                    control_nodes = get_control_node(self.XGraph.graph, call_node)
                    if only_owner_check(self.XGraph.graph, control_nodes, self.XGraph.msg_sender_nodes):
                        break
                elif len(from_storage_list) > 0:
                    for storage_node in from_storage_list:
                        if check_storage_taintable(self.XGraph.graph, storage_node, taint_node_list, self.XGraph.msg_sender_nodes):
                            reentrancy_call_node.append(call_node)








            # recipient = call_node.arguments[1]
            # transfer_amount = call_node.arguments[2]
            # start_data_input = call_node.arguments[3]
            # size_data_input = call_node.arguments[4]
            # start_data_output = call_node.arguments[5]
            # size_data_ouput = call_node.arguments[6]


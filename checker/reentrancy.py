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
        sender_node = self.XGraph.sender_node
        for call_node in call_nodes:
            call_param = get_argument_or_flow_node(self.XGraph.graph, call_node)
            branch_id_list = self.XGraph.graph[call_param[0]][call_node]['branchList']
            branches = []
            # arguments = call_node.arguments
            outgas = call_node.arguments[0]

            solver = Solver()
            solver.set("timeout", 200)
            solver.push()
            solver.add(call_node.constraint)
            if type(outgas) == ArithNode:
                solver.add(outgas.expression > 2300)
            else:
                solver.add(outgas.value > 2300)
            if solver.check() == unsat:
                solver.pop()
                break
            solver.pop()
            recipient_node = call_node.arguments[1]
            for branch_id in branch_id_list:
                if not check_state_change(self.XGraph.graph, branch_id, call_node):
                        branches.append(branch_id)
            if len(branches) > 0:
                from_taint_list = get_reachable_list_in_branch(self.XGraph.graph, taint_node_list, recipient_node, branches)
                from_storage_list = get_reachable_list(self.XGraph.graph, self.XGraph.state_nodes, recipient_node)
                if len(from_taint_list) > 0:
                    control_nodes = get_control_node(self.XGraph.graph, call_node)
                    if only_owner_check(self.XGraph.graph, control_nodes, self.XGraph.msg_sender_nodes, self.XGraph.state_nodes, self.XGraph.sender_node):
                        break
                    reentrancy_call_node.append(call_node)
                elif len(from_storage_list) > 0:
                    for storage_node in from_storage_list:
                        if check_storage_taintable(self.XGraph.graph, storage_node, taint_node_list, self.XGraph.msg_sender_nodes, self.XGraph.state_nodes, sender_node):
                            reentrancy_call_node.append(call_node)
        return reentrancy_call_node


from checker import utils
from checker.algorithm import *
from graphBuilder.XGraph import *
from z3 import *


class Unfairpay:
    def __init__(self, XGraph):
        self.XGraph = XGraph

    def check(self):
        unfairpayment_node = []
        call_nodes = self.XGraph.call_nodes
        sstore_nodes = self.XGraph.sstore_nodes
        taint_node_list = self.XGraph.input_data_nodes + self.XGraph.msg_data_nodes
        sender_node = self.XGraph.sender_node
        call_samebranch_list = []
        call_branch_dict = {}
        sstore_branch_dict = {}
        if len(self.XGraph.msg_data_nodes) > 0:
            msgValue = self.XGraph.msg_data_nodes[0].value
        # get the branch_id_list of call instruction
        for call_node in call_nodes:
            call_param = get_argument_or_flow_node(self.XGraph.graph, call_node)
            branch_id_list = self.XGraph.graph[call_param[0]][call_node]['branchList']
            call_branch_dict[call_node] = branch_id_list
        # get the branch_id_list of sstore instruction
        for sstore_node in sstore_nodes:
            sstore_param = get_argument_or_flow_node(self.XGraph.graph, sstore_node)
            branch_id_list = self.XGraph.graph[sstore_param[0]][sstore_node]['branchList']
            sstore_branch_dict[sstore_node] = branch_id_list
            # print(branch_id_list)
        # the copy for recovering call_branch_dict in for loop
        call_branch_dict_copy = call_branch_dict.copy()
        templist = []
        for key_out in call_branch_dict:
            # define a branches list for checking callee
            for key_in in call_branch_dict:
                if key_out.nodeID == key_in.nodeID:
                    continue
                a = [x for x in call_branch_dict[key_out] if x in call_branch_dict[key_in]]
                if a:
                    call_branch_dict[key_out] = a
                    templist.append(key_in)
                    # filter some messagecall nodes,like sha256,keccak256
                    if isinstance(key_out.arguments[2], ConstNode) and key_out.arguments[2].value == 0:
                        templist.pop(-1)
                    templist.append(key_out)
                    if isinstance(key_in.arguments[2], ConstNode) and key_in.arguments[2].value == 0:
                        templist.pop(-1)
                else:
                    templist.append(key_in)
                    if isinstance(key_in.arguments[2], ConstNode) and key_in.arguments[2].value == 0:
                        templist.pop(-1)
                # templist = sorted(list(set(templist)), key=lambda node: node.nodeID)
                if templist:
                    call_samebranch_list.append(sorted(list(set(templist)), key=lambda node: node.nodeID))
            call_branch_dict[key_out] = call_branch_dict_copy[key_out]
            templist.clear()

        # if there is only one callNode in the branch or any two callNodes are not in the same branch
        # put the callNodes into the call_samebranch_list
        if not call_samebranch_list and len(call_nodes) > 0:
            for call_entry in call_nodes:
                call_samebranch_list.append(call_entry)
                # filter some messagecall nodes,like sha256,keccak256
                if isinstance(key_out.arguments[2], ConstNode) and key_out.arguments[2].value == 0:
                    continue
                # traverse the call_samebranch_list and detect unfair payment vulnerability
                self.find_unfairpayment_callnode(call_samebranch_list, msgValue, call_branch_dict, sstore_branch_dict,
                                                 taint_node_list, sender_node, unfairpayment_node)
        # traverse the call_samebranch_list and detect unfair payment vulnerability
        else:
            for sublist in call_samebranch_list:
                self.find_unfairpayment_callnode(sublist, msgValue, call_branch_dict, sstore_branch_dict,
                                                 taint_node_list, sender_node, unfairpayment_node)
        call_samebranch_list.clear()
        # for entry in unfairpayment_node:
        #     print("nodeID: "+entry.nodeID)
        return unfairpayment_node

    def check_sstore_call_samebranch(self, last_call_node, call_branch_dict, sstore_branch_dict):
        for branch_id in call_branch_dict[last_call_node]:
            for key_sstore in sstore_branch_dict:
                if branch_id in sstore_branch_dict[key_sstore] and key_sstore.nodeID < last_call_node.nodeID:
                    print("call and sstore instructions match success")
                    return True
        return False

    def find_unfairpayment_callnode(self, sublist, msgvalue, call_branch_dict, sstore_branch_dict,
                                    taint_node_list, sender_node, unfairpayment_node):
        if sublist:
            branches = []
            totalpay = BitVecVal("0", 256)
            solver = Solver()
            solver.set("timeout", 500)
            solver.push()
            for callNode in sublist:
                outgas = callNode.arguments[0]
                # solver.add(callNode.constraint)
                if type(outgas) == ArithNode:
                    solver.add(outgas.expression > 2300)
                else:
                    solver.add(outgas.value > 2300)
                if isinstance(callNode.arguments[2], ArithNode):
                    totalpay += callNode.arguments[2].expression
                elif isinstance(callNode.arguments[2], InputDataNode):
                    totalpay += callNode.arguments[2].value
                elif isinstance(callNode.arguments[2], ConstNode):
                    totalpay += BitVecVal(str(callNode.arguments[2].value), 256)
                else:
                    raise ValueError("wrong node type", isinstance(callNode.arguments[2]))
            totalpay = simplify(totalpay)
            solver.add(msgvalue > totalpay)
            if utils.check_sat(solver) == unsat:
                for callSuspected in sublist:
                    unfairpayment_node.append(callSuspected)
                print("unsat:UnfairPayment vulnerability was found")
                print(str(totalpay))
                print("**********************")
            elif utils.check_sat(solver) == sat:
                # find a sstore instruction in the branch of the last callNode
                # and nodeID is smaller than callNode's nodeID
                last_call_node = sublist[-1]
                if not self.check_sstore_call_samebranch(last_call_node, call_branch_dict, sstore_branch_dict):
                    unfairpayment_node.append(last_call_node)
                    print("lack of sstore before call:UnfairPayment vulnerability was found")
                    solver.pop()
                    return
                # add two constraints:
                recipient_node = last_call_node.arguments[1]
                for branch_id in call_branch_dict[last_call_node]:
                    if not check_state_change(self.XGraph.graph, branch_id, last_call_node):
                        branches.append(branch_id)
                if len(branches) > 0:
                    from_taint_list = get_reachable_list_in_branch(self.XGraph.graph, taint_node_list,
                                                                   recipient_node, branches)
                    from_storage_list = get_reachable_list(self.XGraph.graph, self.XGraph.state_nodes,
                                                           recipient_node)
                    if len(from_taint_list) > 0:
                        control_nodes = get_control_node(self.XGraph.graph, last_call_node)
                        if only_owner_check(self.XGraph.graph, control_nodes, self.XGraph.msg_sender_nodes,
                                            self.XGraph.state_nodes, self.XGraph.sender_node):
                            solver.pop()
                            return
                        unfairpayment_node.append(last_call_node)
                        print("no owner check:UnfairPayment vulnerability was found")
                        print(str(totalpay))
                        print("**********************")
                    elif len(from_storage_list) > 0:
                        for storage_node in from_storage_list:
                            if check_storage_taintable(self.XGraph.graph, storage_node, taint_node_list,
                                                       self.XGraph.msg_sender_nodes, self.XGraph.state_nodes,
                                                       sender_node):
                                unfairpayment_node.append(last_call_node)
                                print("storage taintable:UnfairPayment vulnerability was found")
                                print(str(totalpay))
                                print("**********************")
            else:
                print("current callNode is safe")
            solver.pop()
        return


def main():
    call_branch_dict = {}
    call_node_1 = 'call_node_1'
    call_node_2 = 'call_node_2'
    call_node_3 = 'call_node_3'
    call_node_4 = 'call_node_4'
    branch_list_1 = [1, 9, 10]
    branch_list_2 = [2, 9]
    branch_list_3 = [3, ]
    branch_list_4 = [5, ]
    call_branch_dict[call_node_1] = branch_list_1
    call_branch_dict[call_node_2] = branch_list_2
    call_branch_dict[call_node_3] = branch_list_3
    call_branch_dict[call_node_4] = branch_list_4
    call_node_list = []
    templist = []
    call_branch_dict_copy = call_branch_dict.copy()
    for key_out in call_branch_dict:
        for key_in in call_branch_dict:
            if (key_out == key_in):
                continue
            a = [x for x in call_branch_dict[key_out] if x in call_branch_dict[key_in]]

            if (a):
                call_branch_dict[key_out] = a
                templist.append(key_in)
                templist.append(key_out)
            else:
                templist.append(key_out)
        templist = sorted(list(set(templist)), key=lambda call_node: call_node)
        call_node_list.append(sorted(list(set(templist)), key=lambda call_node: call_node))
        print(call_node_list)
        call_branch_dict[key_out] = call_branch_dict_copy[key_out]
        templist.clear()
    print(len(call_node_list))
    call_node_list.append([])
    print(len(call_node_list))


if __name__ == '__main__':
    main()

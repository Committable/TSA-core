import logging
import traceback
from collections import namedtuple
from numpy import long
from graphBuilder.XGraph import *
import interpreter.params
import six
from z3 import *
import zlib, base64
from interpreter.symbolicVarGenerator import *
from uinttest.global_test_params import PICKLE_PATH
from utils import *
import interpreter.opcodes as opcodes
from graphBuilder.evmGraph import *
import networkx as nx
import global_params
import pickle

log = logging.getLogger(__name__)
Edge = namedtuple("Edge", ["v1", "v2"])

UNSIGNED_BOUND_NUMBER = 2**256 - 1
CONSTANT_ONES_159 = BitVecVal((1 << 160) - 1, 256)


class EVMInterpreter:
    def __init__(self, runtime):
        self.gen = Generator()
        self.solver = Solver()
        self.runtime = runtime

        self.graph = XGraph()
        self.path_conditions = []

        self.total_no_of_paths = {"normal": 0, "exception": 0}  # number of paths, terminated by normal or exception
        self.total_visited_pc = {}  # visited pc and its times
        self.total_visited_edges = {}  # visited edges and its times

        # (key, value), key for the value of seeds and value for the symbolic expression of sha3
        self.sha3_dict = {}
        # (key, value), key(v0, v1) for the stack[0] and stack2 of exp instruction, value for the symbolic expression of
        # exp(stack[0], stack[1])
        self.exp_dict = {}
        # (key, value), key formatted by (start, end) from stack
        self.input_dict = {}

        self.call_data_size = None

    def sym_exec(self):
        path_conditions_and_vars = {"path_condition": [], "path_condition_node": []}
        global_state = {"balance": {}, "pc": 0}
        self._init_global_state(path_conditions_and_vars, global_state)
        params = Parameter(path_conditions_and_vars=path_conditions_and_vars, global_state=global_state)
        return self._sym_exec_block(params, 0, 0)

    # Symbolically executing a block from the start address
    def _sym_exec_block(self, params, block, pre_block):
        visited = params.visited

        global_state = params.global_state

        if block < 0 or block not in self.runtime.vertices:
            self.total_no_of_paths["exception"] += 1
            log.debug("Unknown jump address %d. Terminating this path ...", block)
            return 1

        log.debug("Reach block address %d \n", block)

        current_edge = Edge(pre_block, block)

        # update visited edges for current path
        if current_edge in visited:
            updated_count_number = visited[current_edge] + 1
            visited.update({current_edge: updated_count_number})
        else:
            visited.update({current_edge: 1})

        # update visited edges for global symbolic execution
        if current_edge in self.total_visited_edges:
            updated_count_number = self.total_visited_edges[current_edge] + 1
            self.total_visited_edges.update({current_edge: updated_count_number})
        else:
            self.total_visited_edges.update({current_edge: 1})

        # TODO: how to implement real loop dectection?
        # now we only detect occurancly of the same edge under loop_limit
        if visited[current_edge] > interpreter.params.LOOP_LIMIT:
            self.total_no_of_paths["normal"] += 1
            log.debug("Overcome a number of loop limit. Terminating this path ...")
            return 0

        # TODO: gas_used cannot be calculated accurately because of miu, now we keep the less used gas by instructions
        #  and less memory used, and there should be someone to learn about gas calculation of evm exactly
        if params.gas > interpreter.params.GAS_LIMIT:
            self.total_no_of_paths["normal"] += 1
            log.debug("Run out of gas. Terminating this path ... ")
            return 0

        block_ins = self.runtime.vertices[block].get_instructions()

        # Execute every instruction, one at a time
        try:
            for instr in block_ins:
                self._sym_exec_ins(params, block, instr)
        except Exception as error:
            self.total_no_of_paths["exception"] += 1
            log.debug("This path results in an exception: %s, Terminating this path ...", str(error))
            return 1

        if self.is_testing_evm():
            self.compare_storage_and_gas_unit_test(global_state, global_params.UNIT_TEST)

        # Go to next Basic Block(s)
        if self.runtime.jump_type[block] == "terminal":
            self.total_no_of_paths += 1

            branch_id = self.gen.gen_branch_id()
            control_edge_list = params.control_edge_list
            flow_edge_list = params.flow_edge_list
            self.graph.addBranchEdge(flow_edge_list, "flowEdge", branch_id)
            self.graph.addBranchEdge(control_edge_list, "controlEdge", branch_id)

            log.debug("TERMINATING A PATH ...")

        elif self.runtime.jump_type[block] == "unconditional":  # executing "JUMP"
            # TODO: how to deal with symbolic jump targets and more than one jump targets for unconditoinal jump
            # now we only deal with unconditional jump with only one real target
            successor = self.runtime.vertices[block].get_jump_targets()[-1]
            params.global_state["pc"] = successor
            self._sym_exec_block(params, successor, block)

        elif self.runtime.jump_type[block] == "falls_to":  # just follow to the next basic block
            successor = self.runtime.vertices[block].get_falls_to()
            # assert successor
            params.global_state["pc"] = successor
            self._sym_exec_block(params, successor, block)

        elif self.runtime.jump_type[block] == "conditional":  # executing "JUMPI"
            # A choice point, we proceed with depth first search
            branch_expression = self.runtime.vertices[block].get_branch_expression()
            branch_expression_node = self.runtime.vertices[block].get_branch_expression_node()
            negated_branch_expression_node = self.runtime.vertices[block].get_negated_branch_expression_node()

            log.debug("Branch expression: " + str(branch_expression))

            self.solver.push()
            self.solver.add(branch_expression)

            flag = True  # mark if constrains are feasible
            try:
                if self.solver.check() == unsat:
                    flag = False
                    self.total_no_of_paths["normal"] += 1
                    log.debug("This path results in an unfeasible conditional True branch, Terminating this path ...")
            except Exception:
                pass
            finally:
                if flag:
                    # there is only one real jump target for conditional jumpi
                    left_branch = self.runtime.vertices[block].get_jump_targets()[-1]
                    new_params = params.copy()
                    new_params.global_state["pc"] = left_branch
                    new_params.path_conditions_and_vars["path_condition"].append(branch_expression)
                    new_params.path_conditions_and_vars["path_condition_node"].append(branch_expression_node)
                    self._sym_exec_block(new_params, left_branch, block)

                self.solver.pop()

            flag = True
            self.solver.push()
            negated_branch_expression = Not(branch_expression)
            self.solver.add(negated_branch_expression)

            log.debug("Negated branch expression: " + str(negated_branch_expression))

            try:
                if self.solver.check() == unsat:
                    flag = False
                    self.total_no_of_paths["normal"] += 1
                    log.debug("This path results in an unfeasible conditional Flase branch, Terminating this path ...")
            except Exception:
                pass
            finally:
                if flag:
                    right_branch = self.runtime.vertices[block].get_falls_to()
                    params.global_state["pc"] = right_branch
                    params.path_conditions_and_vars["path_condition"].append(negated_branch_expression)
                    params.path_conditions_and_vars["path_condition_node"].append(negated_branch_expression_node)
                    self._sym_exec_block(params, right_branch, block)

                self.solver.pop()
        else:
            raise Exception('Unknown Jump-Type')

        return 0

    # TODO: 1.slot precision; 2.memory model; 3.sha3; 4.system contracts call; 5.evm instructions expansion;
    # memory model  : model versioned memory as mem{(start, end):value} and memory[byte], and every write of memory will
    #                 result in a new version of memory, but now we only treat memory when there address can be exactly
    #                 the same by transformed to string when they are symbolic, and real address only locate memory[]
    # slot precision: slot precision should be treated by checker
    # sha3          : if sha3 a0, a1 => memory{(a0, a0+a1): (concat(a,b,c)} , we maitain a dic sha3_list{concat(a,
    #                 b, c): sha3_sym)}, and everytime "sha3" instruction is executed, if str(key) is exactly the same,
    #                 we get the same sha3_sym, otherwise, we will construct a new (key2, sha3_sym2); and everytime a
    #                 constrain include both sha3_sym1, sha3_sym2, the sha3_sym2 is substituted by sha2_sym1, with const
    #                 -rain key1 == key2, because we only cares about the equality of two sha3_sym
    # scc           : todo
    # instructions  : todo
    def _sym_exec_ins(self, params, block, instr):
        stack = params.stack
        node_stack = params.node_stack

        mem = params.mem
        node_mem = params.node_mem
        memory = params.memory
        node_memory = params.node_memory

        global_state = params.global_state

        path_conditions_and_vars = params.path_conditions_and_vars
        calls = params.calls
        control_edge_list = params.control_edge_list
        flow_edge_list = params.flow_edge_list

        instr_parts = str.split(instr, ' ')
        opcode = instr_parts[1]

        if len(stack) != len(node_stack):
            raise Exception("stack length exception: len(stack) != len(node_stack")

        log.debug("==============================")
        log.debug("EXECUTING: " + instr)

        #
        #  0s: Stop and Arithmetic Operations
        #
        if opcode == "STOP":
            return
        elif opcode == "INVALID":
            return
        elif opcode == "ADD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first + second) & UNSIGNED_BOUND_NUMBER

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MUL":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first * second & UNSIGNED_BOUND_NUMBER

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SUB":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first - second) & UNSIGNED_BOUND_NUMBER

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "DIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                self.solver.push()
                self.solver.add(Not(second == 0))
                if check_unsat(self.solver):
                    computed = 0
                else:
                    computed = UDiv(first, second)

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SDIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                self.solver.push()
                self.solver.add(Not(second == 0))
                if check_unsat(self.solver):
                    computed = 0
                else:
                    computed = (first / second) & UNSIGNED_BOUND_NUMBER
                self.solver.pop()

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                self.solver.push()
                self.solver.add(Not(second == 0))
                if check_unsat(self.solver):
                    # it is provable that second is indeed equal to zero
                    computed = 0
                else:
                    computed = URem(first, second)
                self.solver.pop()

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SMOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                self.solver.push()
                self.solver.add(Not(second == 0))
                if check_unsat(self.solver):
                    # it is provable that second is indeed equal to zero
                    computed = 0
                else:
                    first = to_symbolic(first)
                    sign = If(first < 0, -1, 1)
                    z3_abs = lambda x: If(x >= 0, x, -x)
                    first = z3_abs(first)
                    second = z3_abs(second)
                    computed = sign * (first % second)
                self.solver.pop()

                stack.insert(0, convertResult(computed))

            else:
                raise ValueError('STACK underflow')
        elif opcode == "ADDMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                first = to_symbolic(first)
                second = to_symbolic(second)
                third = to_symbolic(third)
                self.solver.push()
                self.solver.add(Not(third == 0))
                if check_unsat(self.solver):
                    computed = 0
                else:
                    computed = URem((first + second), third)
                self.solver.pop()

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MULMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                first = to_symbolic(first)
                second = to_symbolic(second)
                third = to_symbolic(third)
                self.solver.push()
                self.solver.add(Not(third == 0))
                if check_unsat(self.solver):
                    computed = 0
                else:
                    computed = URem(first * second, third)
                self.solver.pop()

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EXP":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                base = stack.pop(0)
                exponent = stack.pop(0)
                # Type conversion is needed when they are mismatched
                if isAllReal(base, exponent):
                    computed = pow(base, exponent, 2 ** 256)
                else:
                    # The computed value is unknown, this is because power is
                    # not supported in bit-vector theory
                    base = simplify(to_symbolic(base))
                    exponent = simplify(to_symbolic(exponent))
                    computed = None

                    # we check the same value by solver the most less constrains with less accurence
                    s = Solver()
                    for key in self.exp_dict:
                        s.push()
                        s.add(Not(key[0] == base and key[1] == exponent))
                        if check_unsat(s):
                            computed = self.exp_dict[key]
                            s.pop()
                            break
                        s.pop()
                    del s
                    # computed == None means that we don't fine the used value and we need a new one
                    if not computed:
                        new_var_name = self.gen.gen_exp_var(base, exponent)
                        computed = BitVec(new_var_name, 256)
                        self.exp_dict[(base, exponent)] = computed

                stack.insert(0, computed)

            else:
                raise ValueError('STACK underflow')
        elif opcode == "SIGNEXTEND":
            if len(stack) > 1:
                # todo: reveiw this process
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    if first >= 32:
                        computed = second
                    else:
                        signbit_index_from_right = 8 * first + 7
                        if second & (1 << signbit_index_from_right):
                            computed = second | (2 ** 256 - (1 << signbit_index_from_right))
                        else:
                            computed = second & ((1 << signbit_index_from_right) - 1)
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)
                    self.solver.push()
                    self.solver.add(Not(UGE(first, 32)))
                    if check_unsat(self.solver):
                        computed = second
                    else:
                        signbit_index_from_right = 8 * first + 7
                        self.solver.push()
                        self.solver.add(second & (1 << signbit_index_from_right) == 0)
                        if check_unsat(self.solver):
                            computed = second | (2 ** 256 - (1 << signbit_index_from_right))
                        else:
                            computed = second & ((1 << signbit_index_from_right) - 1)
                        self.solver.pop()
                    self.solver.pop()

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        #
        #  10s: Comparison and Bitwise Logic Operations
        #
        elif opcode == "LT":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                computed = If(ULT(first, second), BitVec(1, 256), BitVec(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "GT":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                computed = If(UGT(first, second), BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                computed = If(first < second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SGT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                second = to_symbolic(second)
                computed = If(first > second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EQ":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(first == second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "ISZERO":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)

                computed = If(first == 0, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "AND":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first & second

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "OR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first | second

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "XOR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first ^ second

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "NOT":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)

                computed = (~first)  # todo: should there be like: (~first) & UNSIGNED_BOUND_NUMBER

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "BYTE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                byte_index = 31 - first
                second = stack.pop(0)

                first = to_symbolic(first)
                self.solver.push()
                self.solver.add(Not(Or(UGE(first, 32))))
                if check_unsat(self.solver):
                    computed = 0
                else:
                    computed = second & (255 << (8 * byte_index))
                    computed = LShR(computed, (8 * byte_index))
                self.solver.pop()
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        #
        # 20s: SHA3
        #
        elif opcode == "SHA3":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                s0 = stack.pop(0)
                s1 = stack.pop(0)
                if isAllReal(s0, s1):
                    # simulate the hashing of sha3
                    data = [x for x in memory[s0: s0 + s1]]
                    value = to_symbolic(data[0])
                    for x in data[1:]:
                        value = Concat(value, to_symbolic(x))

                    computed = None
                    # we check the same value by solver the most less constrains with less accurence
                    s = Solver()
                    for key in self.sha3_dict:
                        s.push()
                        s.add(Not(value == key))
                        if check_unsat(s):
                            computed = self.sha3_dict[key]
                            s.pop()
                            break
                        s.pop()
                    del s

                    # computed == None means that we don't fine the used value and we need a new one
                    if not computed:
                        value = simplify(value)
                        new_var_name = self.gen.gen_sha3_var(value)
                        computed = BitVec(new_var_name, 256)
                        self.exp_dict[value] = computed
                else:
                    # todo:push into the stack a fresh symbolic variable, how to deal with symbolic address and size
                    new_var_name = self.gen.gen_arbitrary_var()
                    new_var = BitVec(new_var_name, 256)
                    stack.insert(0, new_var)
                    computed = new_var
            else:
                raise ValueError('STACK underflow')
        #
        # 30s: Environment Information
        #
        elif opcode == "ADDRESS":  # get address of currently executing account
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, path_conditions_and_vars["Ia"])
        elif opcode == "BALANCE":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = simplify(to_symbolic(stack.pop(0)))
                new_var_name = self.gen.gen_balance_var(address)
                # todo: global_state is initiated with global_state["balance"]["Ia"], how to deal with it? useless?
                if new_var_name in global_state["balance"]:
                    new_var = global_state["balance"]
                else:
                    new_var = BitVec(new_var_name, 256)
                    global_state["balance"][address] = new_var

                stack.insert(0, new_var)
                # todo: graph
                update_graph_balance(self.graph, node_stack, global_state, flow_edge_list)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLER":  # get caller address
            # that is directly responsible for this execution
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["sender_address"])
        elif opcode == "ORIGIN":  # get execution origination address
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["origin"])
        elif opcode == "CALLVALUE":  # get value of this transaction
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["value"])
        elif opcode == "CALLDATALOAD":  # from input data from environment
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                start = simplify(to_symbolic(stack.pop(0)))
                end = simplify(start+31)

                value = None
                s = Solver()
                for key in self.input_dict:
                    s.push()
                    s.add(Not(And(key[0] == start, key[1] == end)))
                    if check_unsat(s):
                        value = self.input_dict[key]
                        break
                # no used inputData found
                if not value:
                    new_var_name = self.gen.gen_data_var(start, end)
                    value = BitVec(new_var_name, 256)
                    self.input_dict[(start, end)] = value
                stack.insert(0, value)

                # todo: graph
                update_graph_inputdata(self.graph, node_stack, value, str(value), global_state)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLDATASIZE":
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, self.call_data_size)
        elif opcode == "CALLDATACOPY":  # Copy input data to memory
            #  TODO: Don't know how to simulate this yet
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                memory_start = stack.pop(0)
                input_start = stack.pop(0)
                size = stack.pop(0)

                input_end = simplify(input_start + size)




                self.write_memory(memory_start, memory_start + size, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CODESIZE":
            if self.disasm_file.endswith('.disasm'):
                evm_file_name = self.disasm_file[:-7]
            else:
                evm_file_name = self.disasm_file
            with open(evm_file_name, 'r') as evm_file:
                evm = evm_file.read()[:-1]
                code_size = len(evm) / 2
                stack.insert(0, code_size)
        elif opcode == "CODECOPY":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                mem_location = stack.pop(0)
                code_from = stack.pop(0)
                no_bytes = stack.pop(0)
                current_miu_i = global_state["miu_i"]

                if isAllReal(mem_location, current_miu_i, code_from, no_bytes):

                    temp = int(math.ceil((mem_location + no_bytes) / float(32)))

                    if temp > current_miu_i:
                        current_miu_i = temp

                    if self.runtime.disasm_file.endswith('.disasm'):
                        evm_file_name = self.runtime.disasm_file[:-7]
                    else:
                        evm_file_name = self.disasm_file
                    with open(evm_file_name, 'r') as evm_file:
                        evm = evm_file.read()[:-1]
                        start = code_from * 2
                        end = start + no_bytes * 2
                        code = evm[start: end]
                    mem[mem_location] = int(code, 16)
                else:
                    new_var_name = self.gen.gen_code_var("Ia", code_from, no_bytes)
                    if new_var_name in path_conditions_and_vars:
                        new_var = path_conditions_and_vars[new_var_name]
                    else:
                        new_var = BitVec(new_var_name, 256)
                        path_conditions_and_vars[new_var_name] = new_var

                    temp = ((mem_location + no_bytes) / 32) + 1
                    current_miu_i = to_symbolic(current_miu_i)
                    expression = current_miu_i < temp
                    self.solver.push()
                    self.solver.add(expression)
                    if check_sat(self.solver) != unsat:
                        current_miu_i = If(expression, temp, current_miu_i)
                    self.solver.pop()
                    mem.clear()  # very conservative
                    mem[str(mem_location)] = new_var
                global_state["miu_i"] = current_miu_i
            else:
                raise ValueError('STACK underflow')
        elif opcode == "RETURNDATACOPY":
            if len(stack) > 2:
                global_state["pc"] += 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "RETURNDATASIZE":
            global_state["pc"] += 1
            new_var_name = self.gen.gen_arbitrary_var()
            new_var = BitVec(new_var_name, 256)
            stack.insert(0, new_var)
        elif opcode == "GASPRICE":
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["gas_price"])
        elif opcode == "EXTCODESIZE":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)
                    # not handled yet
                new_var_name = self.gen.gen_code_size_var(address)
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var
                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EXTCODECOPY":
            if len(stack) > 3:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)
                mem_location = stack.pop(0)
                code_from = stack.pop(0)
                no_bytes = stack.pop(0)
                current_miu_i = global_state["miu_i"]
                new_var_name = self.gen.gen_code_var(address, code_from, no_bytes)
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var

                temp = ((mem_location + no_bytes) / 32) + 1
                current_miu_i = to_symbolic(current_miu_i)
                expression = current_miu_i < temp
                self.solver.push()
                self.solver.add(expression)

                if check_sat(self.solver) != unsat:
                    current_miu_i = If(expression, temp, current_miu_i)
                self.solver.pop()
                mem.clear()  # very conservative
                mem[str(mem_location)] = new_var
                global_state["miu_i"] = current_miu_i
            else:
                raise ValueError('STACK underflow')
        #
        #  40s: Block Information
        #
        elif opcode == "BLOCKHASH":  # information from block header
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                stack.pop(0)
                new_var_name = "IH_blockhash"
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var
                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "COINBASE":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentCoinbase"])
            block_related_value = global_state["currentCoinbase"]
        elif opcode == "TIMESTAMP":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentTimestamp"])
            block_related_value = global_state["currentTimestamp"]
        elif opcode == "NUMBER":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentNumber"])
            block_related_value = global_state["currentNumber"]
        elif opcode == "DIFFICULTY":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentDifficulty"])
            block_related_value = global_state["currentDifficulty"]
        elif opcode == "GASLIMIT":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentGasLimit"])
            block_related_value = global_state["currentGasLimit"]
        #
        #  50s: Stack, Memory, Storage, and Flow Information
        #
        elif opcode == "POP":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                stack.pop(0)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MLOAD":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)
                # node_address = node_stack.pop(0)
                new_var = ""
                current_miu_i = global_state["miu_i"]
                if isAllReal(address, current_miu_i) and address in mem:

                    temp = int(math.ceil((address + 32) / float(32)))
                    if temp > current_miu_i:
                        current_miu_i = temp
                    value = mem[address]
                    # node_value = node_mem[address]
                    stack.insert(0, value)
                    # node_stack.insert(0, node_value)
                else:
                    temp = ((address + 31) / 32) + 1
                    current_miu_i = to_symbolic(current_miu_i)
                    expression = current_miu_i < temp
                    self.solver.push()
                    self.solver.add(expression)

                    if check_sat(self.solver) != unsat:
                        # this means that it is possibly that current_miu_i < temp
                        current_miu_i = If(expression, temp, current_miu_i)
                    self.solver.pop()
                    new_var_name = self.gen.gen_mem_var(address)
                    if new_var_name in path_conditions_and_vars:
                        new_var = path_conditions_and_vars[new_var_name]
                    else:
                        new_var = BitVec(new_var_name, 256)
                        path_conditions_and_vars[new_var_name] = new_var
                    stack.insert(0, new_var)
                    # node_stack.insert(0, 0)
                    if isReal(address):
                        mem[address] = new_var
                        # node_mem[address] = new_var
                    else:
                        mem[str(address)] = new_var
                        # node_mem[str(address)] = new_var
                global_state["miu_i"] = current_miu_i
                update_graph_mload(self.graph, address, current_miu_i, mem, node_stack, new_var, node_mem, global_state)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MSTORE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)
                # node_stored_address = node_stack.pop(0)
                # node_stored_value = node_stack.pop(0)
                current_miu_i = global_state["miu_i"]
                if isReal(stored_address):
                    # preparing data for hashing later
                    old_size = len(memory) // 32
                    new_size = ceil32(stored_address + 32) // 32
                    mem_extend = (new_size - old_size) * 32
                    memory.extend([0] * mem_extend)
                    value = stored_value
                    for i in range(31, -1, -1):
                        memory[stored_address + i] = value % 256
                        value /= 256
                if isAllReal(stored_address, current_miu_i):

                    temp = int(math.ceil((stored_address + 32) / float(32)))
                    if temp > current_miu_i:
                        current_miu_i = temp
                    mem[stored_address] = stored_value  # note that the stored_value could be symbolic
                else:
                    temp = ((stored_address + 31) / 32) + 1
                    expression = current_miu_i < temp
                    self.solver.push()
                    self.solver.add(expression)

                    if check_sat(self.solver) != unsat:
                        # this means that it is possibly that current_miu_i < temp
                        current_miu_i = If(expression, temp, current_miu_i)
                    self.solver.pop()
                    mem.clear()  # very conservative
                    mem[str(stored_address)] = stored_value
                global_state["miu_i"] = current_miu_i
                update_graph_mstore(self.graph, stored_address, stored_value, current_miu_i, node_mem, node_stack)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MSTORE8":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                temp_value = stack.pop(0)
                stored_value = temp_value % 256  # get the least byte
                current_miu_i = global_state["miu_i"]
                if isAllReal(stored_address, current_miu_i):

                    temp = int(math.ceil((stored_address + 1) / float(32)))
                    if temp > current_miu_i:
                        current_miu_i = temp
                    mem[stored_address] = stored_value  # note that the stored_value could be symbolic
                else:
                    temp = (stored_address / 32) + 1
                    if isReal(current_miu_i):
                        current_miu_i = BitVecVal(current_miu_i, 256)
                    expression = current_miu_i < temp
                    self.solver.push()
                    self.solver.add(expression)

                    if check_sat(self.solver) != unsat:
                        # this means that it is possibly that current_miu_i < temp
                        current_miu_i = If(expression, temp, current_miu_i)
                    self.solver.pop()
                    mem.clear()  # very conservative
                    mem[str(stored_address)] = stored_value
                global_state["miu_i"] = current_miu_i
                update_graph_mstore(self.graph, stored_address, stored_value, current_miu_i, node_mem, node_stack)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLOAD":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                position = stack.pop(0)
                # node_position = node_stack.pop(0)
                new_var_name = ""
                new_var = ""
                if isReal(position) and position in global_state["Ia"]:
                    value = global_state["Ia"][position]
                    stack.insert(0, value)
                else:
                    if str(position) in global_state["Ia"]:
                        value = global_state["Ia"][str(position)]
                        stack.insert(0, value)
                    else:
                        if is_expr(position):
                            position = simplify(position)
                        new_var_name = self.gen.gen_owner_store_var(position)

                        if new_var_name in path_conditions_and_vars:
                            new_var = path_conditions_and_vars[new_var_name]
                        else:
                            new_var = BitVec(new_var_name, 256)
                            path_conditions_and_vars[new_var_name] = new_var
                        stack.insert(0, new_var)

                        if isReal(position):
                            global_state["Ia"][position] = new_var
                        else:
                            global_state["Ia"][str(position)] = new_var
                update_graph_sload(self.graph, path_conditions_and_vars, node_stack, global_state, position, new_var_name, new_var, control_edge_list, flow_edge_list)
            else:
                raise ValueError('STACK underflow')

        elif opcode == "SSTORE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)
                if isReal(stored_address):
                    # if stored_address in global_state["Ia"]:
                    global_state["Ia"][stored_address] = stored_value
                else:
                    # note that the stored_value could be unknown
                    global_state["Ia"][str(stored_address)] = stored_value
                update_graph_sstore(self.graph, node_stack, stored_address, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "JUMP":
            if len(stack) > 0:
                target_address = stack.pop(0)
                if isSymbolic(target_address):
                    try:
                        target_address = int(str(simplify(target_address)))
                    except:
                        raise TypeError("Target address must be an integer")
                self.runtime.vertices[block].set_jump_target(target_address)
                if target_address not in self.runtime.edges[block]:
                    self.runtime.edges[block].append(target_address)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "JUMPI":
            # We need to prepare two branches
            if len(stack) > 1:
                target_address = stack.pop(0)
                # node_target_address = node_stack.pop(0)
                if isSymbolic(target_address):
                    try:
                        target_address = int(str(simplify(target_address)))
                    except:
                        raise TypeError("Target address must be an integer")
                self.runtime.vertices[block].set_jump_target(target_address)
                flag = stack.pop(0)
                # node_flag = node_stack.pop(0)
                branch_expression = (BitVecVal(0, 1) == BitVecVal(1, 1))
                if isReal(flag):
                    if flag != 0:
                        branch_expression = True
                else:
                    branch_expression = (flag != 0)
                    # compare_node = ConstNode("", 0, False)
                    # operand = [node_flag, compare_node]
                    # ADD Edge
                self.runtime.vertices[block].set_branch_expression(branch_expression)
                if target_address not in self.runtime.edges[block]:
                    self.runtime.edges[block].append(target_address)
                update_jumpi(self.graph, node_stack, self.runtime.vertices[block], flag, branch_expression,
                             global_state, control_edge_list, flow_edge_list)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "PC":
            stack.insert(0, global_state["pc"])
            global_state["pc"] = global_state["pc"] + 1
        elif opcode == "MSIZE":
            global_state["pc"] = global_state["pc"] + 1
            msize = 32 * global_state["miu_i"]
            stack.insert(0, msize)
        elif opcode == "GAS":
            # In general, we do not have this precisely. It depends on both
            # the initial gas and the amount has been depleted
            # we need o think about this in the future, in case precise gas
            # can be tracked
            global_state["pc"] = global_state["pc"] + 1
            new_var_name = self.gen.gen_gas_var()
            new_var = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = new_var
            stack.insert(0, new_var)
            update_gas(node_stack, opcode, new_var, global_state)
        elif opcode == "JUMPDEST":
            # Literally do nothing
            global_state["pc"] = global_state["pc"] + 1
        #
        #  60s & 70s: Push Operations
        #
        elif opcode.startswith('PUSH', 0):  # this is a push instruction
            position = int(opcode[4:], 10)
            global_state["pc"] = global_state["pc"] + 1 + position
            pushed_value = int(instr_parts[1], 16)
            stack.insert(0, pushed_value)
            update_graph_const(self.graph, node_stack, pushed_value, global_state)
        #
        #  80s: Duplication Operations
        #
        elif opcode.startswith("DUP", 0):
            global_state["pc"] = global_state["pc"] + 1
            position = int(opcode[3:], 10) - 1
            if len(stack) > position:
                duplicate = stack[position]
                stack.insert(0, duplicate)
                update_dup(node_stack, position)
            else:
                raise ValueError('STACK underflow')

        #
        #  90s: Swap Operations
        #
        elif opcode.startswith("SWAP", 0):
            global_state["pc"] = global_state["pc"] + 1
            position = int(opcode[4:], 10)
            if len(stack) > position:
                temp = stack[position]
                stack[position] = stack[0]
                stack[0] = temp
                update_swap(node_stack, position)
            else:
                raise ValueError('STACK underflow')

        #
        #  a0s: Logging Operations
        #
        elif opcode in ("LOG0", "LOG1", "LOG2", "LOG3", "LOG4"):
            global_state["pc"] = global_state["pc"] + 1
            # We do not simulate these log operations
            num_of_pops = 2 + int(opcode[3:])
            while num_of_pops > 0:
                stack.pop(0)
                num_of_pops -= 1

        #
        #  f0s: System Operations
        #
        elif opcode == "CREATE":
            if len(stack) > 2:
                global_state["pc"] += 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)

                new_var_name = self.gen.gen_arbitrary_var()
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALL":
            # TODO: Need to handle miu_i
            if len(stack) > 6:
                calls.append(global_state["pc"])
                global_state["pc"] = global_state["pc"] + 1
                outgas = stack.pop(0)
                recipient = stack.pop(0)
                transfer_amount = stack.pop(0)
                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_ouput = stack.pop(0)

                # in the paper, it is shaky when the size of data output is
                # min of stack[6] and the | o |

                if isReal(transfer_amount):
                    if transfer_amount == 0:
                        stack.insert(0, 1)  # x = 0
                        # node_stack.insert(0, 0)
                        return

                # Let us ignore the call depth
                balance_ia = global_state["balance"]["Ia"]
                is_enough_fund = (transfer_amount <= balance_ia)
                self.solver.push()
                self.solver.add(is_enough_fund)

                if check_sat(self.solver) == unsat:
                    # this means not enough fund, thus the execution will result in exception
                    self.solver.pop()
                    stack.insert(0, 0)  # x = 0
                else:
                    # the execution is possibly okay
                    stack.insert(0, 1)  # x = 1
                    self.solver.pop()
                    self.solver.add(is_enough_fund)
                    path_conditions_and_vars["path_condition"].append(is_enough_fund)
                    last_idx = len(path_conditions_and_vars["path_condition"]) - 1
                    new_balance_ia = (balance_ia - transfer_amount)
                    global_state["balance"]["Ia"] = new_balance_ia
                    address_is = path_conditions_and_vars["Is"]
                    address_is = (address_is & CONSTANT_ONES_159)
                    boolean_expression = (recipient != address_is)
                    self.solver.push()
                    self.solver.add(boolean_expression)
                    if check_sat(self.solver) == unsat:
                        self.solver.pop()
                        new_balance_is = (global_state["balance"]["Is"] + transfer_amount)
                        global_state["balance"]["Is"] = new_balance_is
                    else:
                        self.solver.pop()
                        if isReal(recipient):
                            new_address_name = "concrete_address_" + str(recipient)
                        else:
                            new_address_name = self.gen.gen_arbitrary_address_var()
                        old_balance_name = self.gen.gen_arbitrary_var()
                        old_balance = BitVec(old_balance_name, 256)
                        path_conditions_and_vars[old_balance_name] = old_balance
                        constraint = (old_balance >= 0)
                        self.solver.add(constraint)
                        path_conditions_and_vars["path_condition"].append(constraint)
                        new_balance = (old_balance + transfer_amount)
                        global_state["balance"][new_address_name] = new_balance
                update_call(self.graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLCODE":
            # TODO: Need to handle miu_i
            if len(stack) > 6:
                calls.append(global_state["pc"])
                global_state["pc"] = global_state["pc"] + 1
                outgas = stack.pop(0)
                recipient = stack.pop(0)  # this is not used as recipient

                transfer_amount = stack.pop(0)
                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_ouput = stack.pop(0)
                # in the paper, it is shaky when the size of data output is
                # min of stack[6] and the | o |

                if isReal(transfer_amount):
                    if transfer_amount == 0:
                        stack.insert(0, 1)  # x = 0
                        return

                # Let us ignore the call depth
                balance_ia = global_state["balance"]["Ia"]
                is_enough_fund = (transfer_amount <= balance_ia)
                self.solver.push()
                self.solver.add(is_enough_fund)

                if check_sat(self.solver) == unsat:
                    # this means not enough fund, thus the execution will result in exception
                    self.solver.pop()
                    stack.insert(0, 0)  # x = 0
                    # node_stack.insert(0, 0)
                else:
                    # the execution is possibly okay
                    stack.insert(0, 1)  # x = 1
                    # node_stack.insert(0, 0)
                    self.solver.pop()
                    self.solver.add(is_enough_fund)
                    path_conditions_and_vars["path_condition"].append(is_enough_fund)
                    last_idx = len(path_conditions_and_vars["path_condition"]) - 1
                update_callcode(self.graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list)

            else:
                raise ValueError('STACK underflow')
        elif opcode in ("DELEGATECALL", "STATICCALL"):
            if len(stack) > 5:
                global_state["pc"] += 1
                stack.pop(0)
                recipient = stack.pop(0)
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)
                new_var_name = self.gen.gen_arbitrary_var()
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                update_delegatecall(self.graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list)

            else:
                raise ValueError('STACK underflow')
        elif opcode in ("RETURN", "REVERT"):
            # TODO: Need to handle miu_i
            if len(stack) > 1:
                stack.pop(0)
                stack.pop(0)
                if opcode == "REVERT":
                    update_graph_terminal(self.graph, node_stack, global_state, path_conditions_and_vars, control_edge_list)
                # TODO
                pass
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SUICIDE":
            global_state["pc"] = global_state["pc"] + 1
            recipient = stack.pop(0)
            transfer_amount = global_state["balance"]["Ia"]
            global_state["balance"]["Ia"] = 0
            if isReal(recipient):
                new_address_name = "concrete_address_" + str(recipient)
            else:
                new_address_name = self.gen.gen_arbitrary_address_var()
            old_balance_name = self.gen.gen_arbitrary_var()
            old_balance = BitVec(old_balance_name, 256)
            path_conditions_and_vars[old_balance_name] = old_balance
            constraint = (old_balance >= 0)
            self.solver.add(constraint)
            path_conditions_and_vars["path_condition"].append(constraint)
            new_balance = (old_balance + transfer_amount)
            global_state["balance"][new_address_name] = new_balance
            # TODO

            update_suicide(self.graph, node_stack, global_state, path_conditions_and_vars, control_edge_list, flow_edge_list)
            return
        else:
            log.debug("UNKNOWN INSTRUCTION: " + opcode)
            raise Exception('UNKNOWN INSTRUCTION: ' + opcode)
        if opcode in overflow_related:
            if opcode == "EXP":
                param = [base, exponent]
            else:
                param = [first, second]
            update_graph_computed(self.graph, node_stack, opcode, computed, path_conditions_and_vars, global_state,
                                  control_edge_list, flow_edge_list, param)
        elif (opcode in two_operand_opcode) or (opcode in three_operand_opcode) or (opcode in one_operand_opcode):
            # print(opcode)
            update_graph_computed(self.graph, node_stack, opcode, computed, path_conditions_and_vars, global_state, control_edge_list, flow_edge_list, "")
        elif opcode in pass_opcode:
            update_pass(node_stack, opcode, global_state)
        elif opcode in block_opcode:
            update_graph_block(self.graph, node_stack, opcode, block_related_value, global_state["currentNumber"], global_state)
        elif opcode in msg_opcode:
            update_graph_msg(self.graph, node_stack, opcode, global_state)

    def _init_global_state(self, path_conditions_and_vars, global_state):
        sender_address = BitVec("Is", 256)
        receiver_address = BitVec("Ia", 256)
        deposited_value = BitVec("Iv", 256)  # value of transaction
        init_is = BitVec("init_Is", 256)  # balance of sender
        init_ia = BitVec("init_Ia", 256)  # balance of receiver

        self.call_data_size = BitVec("Id_size", 256)  # size of input data

        new_var_name = self.gen.gen_gas_price_var()
        gas_price = BitVec(new_var_name, 256)

        new_var_name = self.gen.gen_origin_var()
        origin = BitVec(new_var_name, 256)

        new_var_name = self.gen.gen_coin_base()
        currentCoinbase = BitVec(new_var_name, 256)

        new_var_name = self.gen.gen_number()
        currentNumber = BitVec(new_var_name, 256)

        new_var_name = self.gen.gen_difficult()
        currentDifficulty = BitVec(new_var_name, 256)

        new_var_name = self.gen.gen_gas_limit()
        currentGasLimit = BitVec(new_var_name, 256)

        new_var_name = self.gen.gen_timestamp()
        currentTimestamp = BitVec(new_var_name, 256)

        # set all the world state before symbolic execution of tx
        global_state["Ia"] = {}  # the state of the current current contract
        global_state["miu_i"] = 0
        global_state["value"] = deposited_value
        global_state["sender_address"] = sender_address
        global_state["receiver_address"] = receiver_address
        global_state["gas_price"] = gas_price
        global_state["origin"] = origin
        global_state["currentCoinbase"] = currentCoinbase
        global_state["currentTimestamp"] = currentTimestamp
        global_state["currentNumber"] = currentNumber
        global_state["currentDifficulty"] = currentDifficulty
        global_state["currentGasLimit"] = currentGasLimit

        constraint = (deposited_value >= BitVecVal(0, 256))
        path_conditions_and_vars["path_condition"].append(constraint)
        constraint = (init_is >= deposited_value)
        path_conditions_and_vars["path_condition"].append(constraint)
        constraint = (init_ia >= BitVecVal(0, 256))
        path_conditions_and_vars["path_condition"].append(constraint)

        # update the balances of the "caller" and "callee", global_state["balance"] is {}, indexed by address(real or
        # symbolic
        global_state["balance"][global_state["sender_address"]] = (init_is - deposited_value)
        global_state["balance"][global_state["receiver_address"]] = (init_ia + deposited_value)

        global_state["nodeID"] = 0
        global_state["pos_to_node"] = {}

        init_state(self.graph, global_state)

    def is_testing_evm(self):
        return global_params.UNIT_TEST != 0

    def compare_storage_and_gas_unit_test(self, global_state, UNIT_TEST):
        unit_test = pickle.load(open(PICKLE_PATH, 'rb'))
        test_status = unit_test.compare_with_symExec_result(global_state, UNIT_TEST)
        exit(test_status)

    def write_memory(self, start, end, value, params):
        pass


class Parameter:

    def __init__(self, **kwargs):
        attr_defaults = {
            # for all elem in stack, they should be either real unsigned int of python or BitVec(256) of z3,i.e without BitVecRef
            # or other types of data
            "stack": [],
            "node_stack": [],
            # all variables located with real type of address and size is stored and loaded by memory, and with one
            # symbolic var in address or size, the value is stored and loaded in mem
            "memory": [],
            "mem": {},
            "node_memory": [],
            "node_mem": {},

            "control_edge_list": [],
            "flow_edge_list": [],
            "calls": [],


            # mark all the visited edges of current_path, for detecting loops and control the loop_depth under limits
            # {Edge:num}
            "visited": {},
            # (address, value), the balance of address
            "balance": {},

            "state_to_node": {},
            "path_conditions_and_vars": {},
            "global_state": {},
            # gas should be always kept real type
            "gas": 0,
            "func_block": None
        }
        for (attr, default) in six.iteritems(attr_defaults):
            setattr(self, attr, kwargs.get(attr, default))

    def copy(self):
        _kwargs = custom_deepcopy(self.__dict__)
        return Parameter(**_kwargs)
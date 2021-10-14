import logging
import traceback
from collections import namedtuple

import psutil
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
from solver.symbolicVar import subexpression, SSolver
from interpreter.opcodes import  opcode_by_name
from graphBuilder import evmGraph
import time

log = logging.getLogger(__name__)
Edge = namedtuple("Edge", ["v1", "v2"])

# Mnemonic for values in memory to inputdata, evm bytecode of current and ext address, returndata
MemInput = namedtuple("MemInput", ["start", "end"])  # indexed by bytes
MemEvm = namedtuple("MemEvm", ["start", "end"])  # indexed by bytes
# indexed by bytes, and pc is the pc of most recent call instruction
MemReturn = namedtuple("MemReturn", ["start", "end", "pc"])
# indexed by bytes, and address is the address of code
MemExtCode = namedtuple("MemExtCode", ["start", "end", "address"])

UNSIGNED_BOUND_NUMBER = 2**256 - 1
CONSTANT_ONES_159 = BitVecVal((1 << 160) - 1, 256)


class EVMInterpreter:
    def __init__(self, runtime):
        self.gen = Generator()

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
        # (key, value), key is the start address and the size is always 256 bits
        self.input_dict = {}
        # (key, value), key is the start address and the size is always 8 bits
        self.evm_dict = {}
        # (address: {(start: value)})
        self.ext_code_dict = {}
        # (address: value)
        self.ext_code_size = {}

        # (key, value), key for block_number
        self.blockhash_dict = {}

        self.call_data_size = None
        self.evm = None

    def sym_exec(self):
        path_conditions_and_vars = {"path_condition": [], "path_condition_node": []}
        global_state = {"balance": {}, "pc": 0}
        self._init_global_state(path_conditions_and_vars, global_state)
        params = Parameter(path_conditions_and_vars=path_conditions_and_vars, global_state=global_state)
        return self._sym_exec_block(params, 0, 0)

    # Symbolically executing a block from the start address
    def _sym_exec_block(self, params, block, pre_block):
        visited = params.visited
        start_time = time.time()
        global_state = params.global_state

        if block < 0 or block not in self.runtime.vertices:
            self.total_no_of_paths["exception"] += 1
            log.info("Unknown jump address %d. Terminating this path ...", block)
            return

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

        log.debug("visiting edge: "+str(current_edge.v1) + "->" + str(current_edge.v2) + " ;path times: " + str(visited[current_edge]) + " ;total times: " + str(self.total_visited_edges[current_edge]))

        # TODO: how to implement better loop dectection?
        # now we only detect occurancly of the same edge under loop_limit
        if (visited[current_edge] > interpreter.params.LOOP_LIMIT and self.runtime.jump_type[block] == "conditional") or self.total_visited_edges[current_edge] > 5:
            self.total_no_of_paths["normal"] += 1
            self.gen.gen_path_id()
            log.debug("Overcome a number of loop limit. Terminating this path ...")
            return

        # TODO: gas_used cannot be calculated accurately because of miu, now we keep the less used gas by instructions
        #  and less memory used, and there should be someone to learn about gas calculation of evm exactly
        if params.gas > interpreter.params.GAS_LIMIT:
            self.total_no_of_paths["normal"] += 1
            self.gen.gen_path_id()
            log.debug("Run out of gas. Terminating this path ... ")
            return

        block_ins = self.runtime.vertices[block].get_instructions()

        memory_inf = psutil.virtual_memory()
        log.debug("Before instructions free memory: %d M" % int(memory_inf.free / (1024 * 1024)))
        # Execute every instruction, one at a time
        try:
            for instr in block_ins:
                memory_inf = psutil.virtual_memory()
                last = int(memory_inf.free / (1024 * 1024))
                last_time = time.time()

                self._sym_exec_ins(params, block, instr)

                memory_inf = psutil.virtual_memory()

                log.debug("Instruction: " + str(instr) + ";Memory: "+ str(last - int(memory_inf.free / (1024 * 1024))))
                log.debug("Instruction: " + str(instr) + ";Time: " + str(int(time.time() - last_time)))

        except Exception as error:
            self.total_no_of_paths["exception"] += 1
            self.gen.gen_path_id()
            # log.debug("This path results in an exception: %s, Terminating this path ...", str(error))
            log.critical("This path results in an exception: %s, Terminating this path ...", str(error))
            traceback.print_exc()
            return

        log.debug("After instructions free memory: %d M" % int(memory_inf.free / (1024 * 1024)))

        if self.is_testing_evm():
            self.compare_storage_and_gas_unit_test(global_state, global_params.UNIT_TEST)

        # Go to next Basic Block(s)
        if self.runtime.jump_type[block] == "terminal":
            self.total_no_of_paths["normal"] += 1
            self.gen.gen_path_id()

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
            str_expr = str(branch_expression)
            log.debug("Branch expression: " + str_expr)
            if str_expr != "False":
                left_branch = self.runtime.vertices[block].get_jump_targets()[-1]
                new_params = params.copy()
                new_params.global_state["pc"] = left_branch
                new_params.path_conditions_and_vars["path_condition"].append(branch_expression)
                new_params.path_conditions_and_vars["path_condition_node"].append(branch_expression_node)
                self._sym_exec_block(new_params, left_branch, block)

            negated_branch_expression = Not(branch_expression)

            log.debug("Negated branch expression: " + str(negated_branch_expression))
            if str_expr != "True":
                right_branch = self.runtime.vertices[block].get_falls_to()
                params.global_state["pc"] = right_branch
                params.path_conditions_and_vars["path_condition"].append(negated_branch_expression)
                params.path_conditions_and_vars["path_condition_node"].append(negated_branch_expression_node)
                self._sym_exec_block(params, right_branch, block)
        else:
            raise Exception('Unknown Jump-Type')
        end_time = time.time()
        executiontime = end_time - start_time
        log.debug("Block: " + str(block) + " symbolic execution time: %.8s s" % executiontime)

        return

    # TODO: 1.slot precision; 2.memory model; 3.sha3; 4.system contracts call; 5.evm instructions expansion;
    # memory model  : model versioned memory as mem{(start, end):value} and memory[byte], and every write of memory will
    #                 result in a new version of memory, but now we only treat memory when there address can be exactly
    #                 the same by transforming to string when they are symbolic, and real address only locate memory[]
    # slot precision: slot precision should be treated by checker
    # sha3          : if sha3 a0, a1 => memory{(a0, a0+a1): (concat(a,b,c)} , we maintain a dict sha3_list{concat(a,
    #                 b, c): sha3_sym)}, and every time "sha3" instruction is executed, if str(key) is exactly the same,
    #                 we get the same sha3_sym, otherwise, we will construct a new (key2, sha3_sym2); and every time a
    #                 constrain include both sha3_sym1, sha3_sym2, the sha3_sym2 is substituted by sha2_sym1, with const
    #                 -rain key1 == key2, because we only cares about the equality of two sha3_sym
    # scc           : todo
    # instructions  : todo
    def _sym_exec_ins(self, params, block, instr):
        stack = params.stack
        b_len = len(stack)

        mem = params.mem
        memory = params.memory

        global_state = params.global_state

        path_conditions_and_vars = params.path_conditions_and_vars
        calls = params.calls


        instr_parts = str.split(instr, ' ')
        opcode = instr_parts[1]

        # log.debug("==============================")
        # log.debug("EXECUTING: " + instr + "LENG_MEM:" + str(len(memory)))
        # log.debug("STACK: " + str(stack))
        # log.info("==============================")
        # log.info("EXECUTING: " + instr + "LENG_MEM:" + str(len(memory)))
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

                computed = (first * second) & UNSIGNED_BOUND_NUMBER

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

                computed = UDiv(to_symbolic(first), second)

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SDIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first / second) & UNSIGNED_BOUND_NUMBER


                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = URem(first, to_symbolic(second))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SMOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                sign = If(first < 0, -1, 1)
                z3_abs = lambda x: If(x >= 0, x, -x)
                first = z3_abs(first)
                second = z3_abs(second)
                computed = sign * (first % second)

                stack.insert(0, convertResult(computed))

            else:
                raise ValueError('STACK underflow')
        elif opcode == "ADDMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                computed = URem(first + second, to_symbolic(third))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MULMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                computed = URem(first * second, to_symbolic(third))

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
                    computed = None

                    # computed == None means that we don't fine the used value and we need a new one
                    if not computed:
                        new_var_name = self.gen.gen_exp_var(base, exponent)
                        computed = BitVec(new_var_name, 256)
                        # add to graph
                        node = ExpNode(new_var_name, computed)
                        self.graph.addVarNode(computed, node)
                        self.exp_dict[(base, exponent)] = computed

                        for var in get_vars(to_symbolic(base)):
                            seed_node = self.graph.getVarNode(var)
                            self.graph.addBranchEdge([(seed_node, node)], "flowEdge", self.gen.get_path_id())
                        for var in get_vars(to_symbolic(exponent)):
                            seed_node = self.graph.getVarNode(var)
                            self.graph.addBranchEdge([(seed_node, node)], "flowEdge", self.gen.get_path_id())

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
                    signbit_index_from_right = 8 * first + 7
                    computed = second & ((1 << signbit_index_from_right) - 1)

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

                computed = If(ULT(first, to_symbolic(second)), BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "GT":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(UGT(first, to_symbolic(second)), BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(first < second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SGT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

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

                computed = LShR(to_symbolic(second), (8 * byte_index))

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        #
        # 20s: SHA3
        #
        elif opcode == "SHA3" or opcode == "KECCAK256":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                s0 = stack.pop(0)
                s1 = stack.pop(0)
                if isAllReal(s0, s1):
                    # simulate the hashing of sha3
                    data = [x for x in memory[s0: s0 + s1]]
                    value = to_symbolic(data[0], 8)
                    for x in data[1:]:
                        value = Concat(value, to_symbolic(x, 8))

                    computed = None

                    # computed == None means that we don't fine the used value and we need a new one
                    if computed is None:
                        value = simplify(value)
                        new_var_name = self.gen.gen_sha3_var(value)
                        computed = BitVec(new_var_name, 256)
                        # add to node
                        node = ShaNode(new_var_name, computed, value)
                        self.graph.addVarNode(computed, node)
                        for var in get_vars(value):
                            seed_node = self.graph.getVarNode(var)
                            self.graph.addBranchEdge([(seed_node, node)], "flowEdge", self.gen.get_path_id())


                        self.sha3_dict[value] = computed
                else:
                    # todo:push into the stack a fresh symbolic variable, how to deal with symbolic address and size
                    new_var_name = self.gen.gen_sha3_var("unkonwn_" + str(global_state["pc"]-1)+"_"+self.gen.get_path_id())
                    new_var = BitVec(new_var_name, 256)
                    computed = new_var
                    # add to node
                    node = ShaNode(new_var_name, computed, None)
                    self.graph.addVarNode(computed, node)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        #
        # 30s: Environment Information
        #
        elif opcode == "ADDRESS":  # get address of currently executing account
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["receiver_address"])
        elif opcode == "BALANCE" or opcode == "SELFBALANCE":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)
                # get balance of address
                new_var = None

                for x in global_state["balance"]:
                    if str(x) == str(address):
                        new_var = global_state["balance"][x]
                        break

                if new_var is None:
                    new_var_name = self.gen.gen_balance_of(address)
                    new_var = BitVec(new_var_name, 256)
                    global_state["balance"][address] = new_var

                    # add to graph
                    a_node = addAddressNode(self.graph, address, self.gen.get_path_id())
                    b_node = BalanceNode(new_var_name, new_var, address)
                    self.graph.addVarNode(new_var, b_node)
                    self.graph.addBranchEdge([(a_node, b_node)], "flowEdge", self.gen.get_path_id())

                stack.insert(0, new_var)
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
                start = stack.pop(0)

                value = self.load_inputdata(start, params)

                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLDATASIZE":
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, self.call_data_size)
        elif opcode == "CALLDATACOPY":  # Copy input data to memory
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                memory_start = stack.pop(0)
                input_start = stack.pop(0)
                size = stack.pop(0)

                input_end = simplify(input_start + size - 1)

                value = MemInput(input_start, input_end)
                self.write_memory(memory_start, memory_start + size - 1, value, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CODESIZE":
                code_size = int((len(self.evm)+1) / 2)
                stack.insert(0, code_size)
        elif opcode == "CODECOPY":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                mem_start = stack.pop(0)
                code_start = stack.pop(0)
                size = stack.pop(0)  # in bytes

                value = MemEvm(code_start, code_start + size - 1)
                self.write_memory(mem_start, mem_start+size-1, value, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "RETURNDATACOPY":
            if len(stack) > 2:
                global_state["pc"] += 1
                mem_start = stack.pop(0)
                return_start = stack.pop(0)
                size = stack.pop(0)  # in bytes

                value = MemReturn(return_start, return_start+size-1, calls[-1])
                self.write_memory(mem_start, mem_start+size-1, value, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "RETURNDATASIZE":
            global_state["pc"] += 1
            new_var_name = self.gen.gen_return_data_size(calls[-1], self.gen.get_path_id())
            new_var = BitVec(new_var_name, 256)
            # add to graph
            node = ReturnDataSizeNode(new_var_name, new_var)
            self.graph.addVarNode(new_var, node)

            stack.insert(0, new_var)
        elif opcode == "GASPRICE":
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["gas_price"])
        elif opcode == "EXTCODESIZE":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)

                new_var = None

                if new_var is None:
                    new_var_name = self.gen.gen_code_size_var(address)
                    new_var = BitVec(new_var_name, 256)
                    # add to graph
                    a_node = addAddressNode(self.graph, address, self.gen.get_path_id())
                    node = ExtcodeSizeNode(new_var_name, new_var, address)
                    self.graph.addBranchEdge([(a_node, node)], "flowEdge", self.gen.get_path_id())
                    self.graph.addVarNode(new_var, node)

                    self.ext_code_size[address] = new_var
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

                value = MemExtCode(code_from, code_from+no_bytes-1, address)
                self.write_memory(mem_location, mem_location+no_bytes-1, value, params)
            else:
                raise ValueError('STACK underflow')
        #
        #  40s: Block Information
        #
        elif opcode == "BLOCKHASH":  # information from block header
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                block_number = stack.pop(0)

                value = None

                # no used blockhash founded
                if value is None:
                    new_var_name = self.gen.gen_blockhash(block_number)
                    value = BitVec(new_var_name, 256)
                    node = BlockhashNode(new_var_name, value, block_number)

                    # add to graph
                    if is_expr(block_number) and not is_const(block_number):
                        e_node = addExpressionNode(self.graph, block_number, self.gen.get_path_id())
                        self.graph.addBranchEdge([(e_node, node)], "flowEdge", self.gen.get_path_id())
                    elif is_expr(block_number) and not is_const(block_number):
                        e_node = self.graph.getVarNode(block_number)
                        self.graph.addBranchEdge([(e_node, node)], "flowEdge", self.gen.get_path_id())
                    self.graph.addVarNode(value, node)

                    self.blockhash_dict[block_number] = value

                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "COINBASE":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentCoinbase"])
        elif opcode == "TIMESTAMP":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentTimestamp"])
        elif opcode == "NUMBER":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentNumber"])
        elif opcode == "DIFFICULTY":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentDifficulty"])
        elif opcode == "GASLIMIT":  # information from block header
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["currentGasLimit"])
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

                value = self.load_memory(address, params)

                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MSTORE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                self.write_memory(stored_address, stored_address + 31, stored_value, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MSTORE8":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                temp_value = stack.pop(0)

                self.write_memory(stored_address, stored_address, temp_value, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLOAD":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                position = stack.pop(0)

                value = None
                for key in global_state["Ia"]:
                    try:
                        if int(str(simplify(to_symbolic(key-position)))) == 0:
                            value = global_state["Ia"][key]
                            break
                    except:
                        pass

                if value is None:
                    new_var_name = self.gen.gen_storage_var(position)
                    value = BitVec(new_var_name, 256)
                    node = StateNode(new_var_name, value, position)
                    # add to graph
                    if is_expr(position) and not is_const(position):
                        p_node = addExpressionNode(self.graph, position, self.gen.get_path_id())
                        self.graph.addBranchEdge([(p_node, node)], "flowEdge", self.gen.get_path_id())
                    elif is_expr(position) and is_const(position):
                        p_node = self.graph.getVarNode(position)
                        self.graph.addBranchEdge([(p_node, node)], "flowEdge", self.gen.get_path_id())
                    self.graph.addVarNode(value, node)
                    self.graph.addStateNode(position, node)

                    global_state["Ia"][position] = value
                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')

        elif opcode == "SSTORE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                global_state["Ia"][stored_address] = stored_value

                # add to graph
                node = self.graph.getStateNode(stored_address)
                if node is None:
                    new_var_name = self.gen.gen_storage_var(stored_address)
                    value = BitVec(new_var_name, 256)
                    node = StateNode(new_var_name, value, stored_address)
                    self.graph.addVarNode(value, node)
                    self.graph.addStateNode(stored_address, node)
                    if is_expr(stored_address) and not is_const(stored_address):
                        p_node = addExpressionNode(self.graph, stored_address, self.gen.get_path_id())
                        self.graph.addBranchEdge([(p_node, node)], "flowEdge", self.gen.get_path_id())
                    elif is_expr(stored_address) and not is_const(stored_address):
                        p_node = self.graph.getVarNode(stored_address)
                        self.graph.addBranchEdge([(p_node, node)], "flowEdge", self.gen.get_path_id())

                e_node = addExpressionNode(self.graph, stored_value, self.gen.get_path_id())
                SStore_node = StateOPNode(opcode, [stored_value, stored_address], global_state["pc"]-1,
                                          path_conditions_and_vars["path_condition"], self.gen.get_path_id())
                self.graph.addNode(SStore_node)

                control_edges = []
                pushEdgesToNode(path_conditions_and_vars["path_condition_node"], SStore_node, control_edges)
                self.graph.addBranchEdge(control_edges, "controlEdge", self.gen.get_path_id())
                self.graph.addBranchEdge([(e_node, SStore_node), (SStore_node, node)], "flowEdge", self.gen.get_path_id())

                self.graph.ssgAddNode(SStore_node,self.gen.get_path_id())


            else:
                raise ValueError('STACK underflow')
        elif opcode == "JUMP":
            if len(stack) > 0:
                target_address = stack.pop(0)

                if isSymbolic(target_address):
                    raise TypeError("Target address must be an real integer but it is: %s", str(target_address))
                self.runtime.vertices[block].set_jump_targets(target_address)
                if target_address not in self.runtime.edges[block]:
                    self.runtime.edges[block].append(target_address)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "JUMPI":
            # We need to prepare two branches
            if len(stack) > 1:
                target_address = stack.pop(0)
                if isSymbolic(target_address):
                    raise TypeError("Target address must be an integer: but it is %s", str(target_address))
                self.runtime.vertices[block].set_jump_targets(target_address)
                if target_address not in self.runtime.edges[block]:
                    self.runtime.edges[block].append(target_address)

                flag = stack.pop(0)
                if type(flag) == int and flag == 0:
                    branch_expression = BoolVal(False)
                elif type(flag) == int and flag != 0:
                    branch_expression = BoolVal(True)
                else:
                    branch_expression = simplify(to_symbolic(flag != 0))
                branch_e_node = addConstrainNode(self.graph, branch_expression, self.gen.get_path_id())
                try:
                    branch_n_e_node = addConstrainNode(self.graph, Not(branch_expression), self.gen.get_path_id())
                except:
                    branch_n_e_node = addConstrainNode(self.graph, Not(True), self.gen.get_path_id())
                self.runtime.vertices[block].set_branch_expression(branch_expression)
                self.runtime.vertices[block].set_branch_node_expression(branch_e_node)
                self.runtime.vertices[block].set_negated_branch_node_expression(branch_n_e_node)


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
            # we need to think about this in the future, in case precise gas
            # can be tracked
            global_state["pc"] = global_state["pc"] + 1
            new_var_name = self.gen.gen_gas_var(global_state["pc"]-1)
            new_var = BitVec(new_var_name, 256)
            # add to graph
            node = GasNode(new_var_name, new_var)
            self.graph.addVarNode(new_var, node)

            stack.insert(0, new_var)
        elif opcode == "JUMPDEST":
            # Literally do nothing
            global_state["pc"] = global_state["pc"] + 1
        #
        #  60s & 70s: Push Operations
        #
        elif opcode.startswith('PUSH', 0):  # this is a push instruction
            position = int(opcode[4:], 10)
            global_state["pc"] = global_state["pc"] + 1 + position
            pushed_value = int(instr_parts[2], 16)
            stack.insert(0, pushed_value)
            # add to graph
            node = ConstNode(str(pushed_value), pushed_value)
            self.graph.addVarNode(pushed_value, node)
        #
        #  80s: Duplication Operations
        #
        elif opcode.startswith("DUP", 0):
            global_state["pc"] = global_state["pc"] + 1
            position = int(opcode[3:], 10) - 1
            if len(stack) > position:
                duplicate = stack[position]
                stack.insert(0, duplicate)
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

                new_var_name = self.gen.gen_address(global_state["pc"]-1)
                new_var = BitVec(new_var_name, 256)
                node = AddressNode(new_var_name, new_var)
                self.graph.addVarNode(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALL":
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

                # Let us ignore the call depth
                balance_ia = global_state["balance"][global_state["receiver_address"]]
                is_enough_fund = (transfer_amount <= balance_ia)

                # the execution is possibly okay
                new_var_name = self.gen.gen_return_status(calls[-1], self.gen.get_path_id())
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)  # x = 1
                # add to graph
                node = ReturnStatusNode(new_var_name, new_var)
                self.graph.addVarNode(new_var, node)

                # add enough_fund condition to path_conditions
                path_conditions_and_vars["path_condition"].append(is_enough_fund)
                # update the balance of call's sender that's this contract's address
                new_balance_ia = convertResult(balance_ia - transfer_amount)
                global_state["balance"][global_state["receiver_address"]] = new_balance_ia
                # update the balance of call's recipient
                old_balance = None
                for key in global_state["balance"]:
                    try:
                        if int(str(simplify(to_symbolic(key-recipient)))):
                            old_balance = global_state["balance"].pop(key)
                            break
                    except:
                        pass
                if old_balance is None:
                    new_address_value_name = self.gen.gen_balance_of(recipient)
                    old_balance = BitVec(new_address_value_name, 256)
                    # add to graph
                    a_node = addAddressNode(self.graph, recipient, self.gen.get_path_id())
                    b_node = BalanceNode(new_var_name, old_balance, recipient)
                    self.graph.addVarNode(old_balance, b_node)
                    self.graph.addBranchEdge([(a_node, b_node)], "flowEdge", self.gen.get_path_id())

                    path_conditions_and_vars["path_condition"].append(old_balance >= 0)  # the init balance should > 0
                new_balance = old_balance + transfer_amount
                global_state["balance"][recipient] = new_balance
                # copy returndata to memory
                self.write_memory(start_data_output, start_data_output+size_data_ouput-1,
                                  MemReturn(0, size_data_ouput-1, calls[-1]), params)

                # add to graph
                node_stack = []
                node_gas = addExpressionNode(self.graph, outgas, self.gen.get_path_id())
                node_stack.insert(0, node_gas)
                node_recipient = addAddressNode(self.graph, recipient, self.gen.get_path_id())
                node_stack.insert(0, node_recipient)
                node_transfer_amount = addExpressionNode(self.graph, transfer_amount, self.gen.get_path_id())
                node_stack.insert(0, node_transfer_amount)
                node_start_data_input = addExpressionNode(self.graph, start_data_input, self.gen.get_path_id())
                node_stack.insert(0, node_start_data_input)
                node_size_data_input = addExpressionNode(self.graph, size_data_input, self.gen.get_path_id())
                node_stack.insert(0, node_size_data_input)
                node_start_data_output = addExpressionNode(self.graph, start_data_output, self.gen.get_path_id())
                node_stack.insert(0, node_start_data_output)
                node_size_data_output = addExpressionNode(self.graph, size_data_ouput, self.gen.get_path_id())
                node_stack.insert(0, node_size_data_output)

                if stack[0] == 0:
                    node_return_status = zeorReturnStatusNode
                else:
                    node_return_status = self.graph.getVarNode(stack[0])
                node_stack.insert(0, node_return_status)

                node_call_return_data = CallReturnDataNode(opcode, global_state["pc"], self.gen.get_path_id())
                self.graph.addCallReturnNode(global_state["pc"]-1, node_call_return_data)

                node_stack.insert(0, node_call_return_data)

                update_call(self.graph, opcode, node_stack, global_state, path_conditions_and_vars, self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLCODE":

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

                # Let us ignore the call depth
                balance_ia = global_state["balance"][global_state["receiver_address"]]
                is_enough_fund = (transfer_amount <= balance_ia)

                # the execution is possibly okay
                new_var_name = self.gen.gen_return_status(calls[-1], self.gen.get_path_id())
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                # add to graph
                node = ReturnStatusNode(new_var_name, new_var)
                self.graph.addVarNode(new_var, node)
                # add enough_fund condition to path_conditions
                path_conditions_and_vars["path_condition"].append(is_enough_fund)
                # update the balance of call's sender that's this contract's address
                new_balance_ia = convertResult(balance_ia - transfer_amount)
                global_state["balance"][global_state["receiver_address"]] = new_balance_ia
                # update the balance of call's recipient
                old_balance = None
                for key in global_state["balance"]:
                    try:
                        if int(str(simplify(to_symbolic(recipient - key)))) == 0:
                            old_balance = global_state["balance"].pop(key)
                            break
                    except:
                        pass
                if old_balance is None:
                    new_address_value_name = self.gen.gen_balance_of(recipient)
                    old_balance = BitVec(new_address_value_name, 256)
                    # add to graph
                    a_node = addAddressNode(self.graph, recipient, self.gen.get_path_id())
                    b_node = BalanceNode(new_address_value_name, old_balance, recipient)
                    self.graph.addVarNode(b_node)
                    self.graph.addBranchEdge([(a_node, b_node)], "flowEdge", self.gen.get_path_id())

                    path_conditions_and_vars["path_condition"].append(
                        old_balance >= 0)  # the init balance should > 0
                new_balance = old_balance + transfer_amount
                global_state["balance"][recipient] = new_balance
                # copy returndata to memory
                self.write_memory(start_data_output, start_data_output + size_data_ouput - 1,
                                  MemReturn(0, size_data_ouput-1, calls[-1]), params)



                # add to graph
                node_stack = []
                node_gas = addExpressionNode(self.graph, outgas, self.gen.get_path_id())
                node_stack.insert(0, node_gas)
                node_recipient = addAddressNode(self.graph, recipient, self.gen.get_path_id())
                node_stack.insert(0, node_recipient)
                node_transfer_amount = addExpressionNode(self.graph, transfer_amount, self.gen.get_path_id())
                node_stack.insert(0, node_transfer_amount)
                node_start_data_input = addExpressionNode(self.graph, start_data_input, self.gen.get_path_id())
                node_stack.insert(0, node_start_data_input)
                node_size_data_input = addExpressionNode(self.graph, size_data_input, self.gen.get_path_id())
                node_stack.insert(0, node_size_data_input)
                node_start_data_output = addExpressionNode(self.graph, start_data_output, self.gen.get_path_id())
                node_stack.insert(0, node_start_data_output)
                node_size_data_output = addExpressionNode(self.graph, size_data_ouput, self.gen.get_path_id())
                node_stack.insert(0, node_size_data_output)

                if stack[0] == 0:
                    node_return_status = zeorReturnStatusNode
                else:
                    node_return_status = self.graph.getVarNode(stack[0])
                node_stack.insert(0, node_return_status)

                node_call_return_data = CallReturnDataNode(self.opcode + ":" + str(global_state["pc"]) + "_" +
                                                           str(self.gen.get_path_id()), global_state["pc"],
                                                           self.gen.get_path_id())
                self.graph.addCallReturnNode(global_state["pc"]-1, node_call_return_data)

                node_stack.insert(0, node_call_return_data)

                update_call(self.graph, opcode, node_stack, global_state, path_conditions_and_vars, self.gen.get_path_id())

            else:
                raise ValueError('STACK underflow')
        elif opcode in ("DELEGATECALL", "STATICCALL"):
            if len(stack) > 5:
                calls.append(global_state["pc"])
                global_state["pc"] = global_state["pc"] + 1
                outgas = stack.pop(0)
                recipient = stack.pop(0)

                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_ouput = stack.pop(0)

                # copy returndata to memory
                self.write_memory(start_data_output, start_data_output + size_data_ouput - 1,
                                  MemReturn(0, size_data_ouput-1, calls[-1]), params)

                # the execution is possibly okay
                new_var_name = self.gen.gen_return_status(calls[-1], self.gen.get_path_id())
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                # add to graph
                node = ReturnStatusNode(new_var_name, new_var)
                self.graph.addVarNode(new_var, node)

                # add to graph
                node_stack = []
                node_gas = addExpressionNode(self.graph, outgas, self.gen.get_path_id())
                node_stack.insert(0, node_gas)
                node_recipient = addAddressNode(self.graph, recipient, self.gen.get_path_id())
                node_stack.insert(0, node_recipient)
                node_start_data_input = addExpressionNode(self.graph, start_data_input, self.gen.get_path_id())
                node_stack.insert(0, node_start_data_input)
                node_size_data_input = addExpressionNode(self.graph, size_data_input, self.gen.get_path_id())
                node_stack.insert(0, node_size_data_input)
                node_start_data_output = addExpressionNode(self.graph, start_data_output, self.gen.get_path_id())
                node_stack.insert(0, node_start_data_output)
                node_size_data_output = addExpressionNode(self.graph, size_data_ouput, self.gen.get_path_id())
                node_stack.insert(0, node_size_data_output)

                if stack[0] == 0:
                    node_return_status = zeorReturnStatusNode
                else:
                    node_return_status = self.graph.getVarNode(stack[0])
                node_stack.insert(0, node_return_status)

                node_call_return_data = CallReturnDataNode(opcode + ":" + str(global_state["pc"]) + "_" +
                                                           str(self.gen.get_path_id()), global_state["pc"],
                                                           self.gen.get_path_id())
                self.graph.addCallReturnNode(global_state["pc"]-1, node_call_return_data)

                node_stack.insert(0, node_call_return_data)

                update_delegatecall(self.graph, opcode, node_stack, global_state,
                                    path_conditions_and_vars, self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode in ("RETURN", "REVERT"):
            # TODO: Need to handle miu_i
            if len(stack) > 1:
                stack.pop(0)
                stack.pop(0)
                if opcode == "REVERT":
                    update_graph_terminal(self.graph, opcode, global_state, path_conditions_and_vars, self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SUICIDE":
            global_state["pc"] = global_state["pc"] + 1
            recipient = stack.pop(0)
            # get transfer_amount and update the new balance
            transfer_amount = None
            for key in global_state["balance"]:
                try:
                    if int(str(simplify(to_symbolic(key - global_state["receiver_address"])))) == 0:
                        transfer_amount = global_state["balance"][key]
                        global_state["balance"][key] = 0
                        break
                except:
                    pass
            if transfer_amount is None:
                raise Exception("transfer amount of currentAddress must not be None")
            # get the balance of recipient and update recipient's balance
            balance_recipent = None
            for key in global_state["balance"]:
                try:
                    if int(str(simplify(to_symbolic(key == recipient)))) == 0:
                        balance_recipent = global_state["balance"].pop(key)
                        break
                except:
                    pass
            if balance_recipent is None:
                new_address_value_name = self.gen.gen_balance_of(recipient)
                old_balance = BitVec(new_address_value_name, 256)
                # add to graph
                a_node = addAddressNode(self.graph, recipient, self.gen.get_path_id())
                b_node = BalanceNode(new_address_value_name, old_balance, recipient)
                self.graph.addVarNode(b_node)
                self.graph.addBranchEdge([(a_node, b_node)], "flowEdge", self.gen.get_path_id())


                path_conditions_and_vars["path_condition"].append(
                    old_balance >= 0)  # the init balance should > 0
            new_balance = old_balance + transfer_amount
            global_state["balance"][recipient] = new_balance
            # add to graph
            node_stack = []
            node_recipient = addAddressNode(self.graph, recipient, self.gen.get_path_id())
            node_amount = addExpressionNode(self.graph, recipient, self.gen.get_path_id())
            node_stack.insert(0, node_recipient)
            node_stack.insert(0, node_amount)
            update_suicide(self.graph, node_stack, global_state, path_conditions_and_vars, self.gen.get_path_id())
            return
        elif opcode == "SAR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (to_symbolic(first) >> second)

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SHR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = LShR(to_symbolic(first), second)

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SHL":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (to_symbolic(first) << second)

                stack.insert(0, convertResult(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CREATE2":
            if len(stack) > 4:
                global_state["pc"] += 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)

                new_var_name = self.gen.gen_address(global_state["pc"]-1)
                new_var = BitVec(new_var_name, 256)
                node = AddressNode(new_var_name, new_var)
                self.graph.addVarNode(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        else:
            log.debug("UNKNOWN INSTRUCTION: " + opcode)
            raise Exception('UNKNOWN INSTRUCTION: ' + opcode)
        a_len = len(stack)
        if (a_len - b_len) != (opcode_by_name(opcode).push - opcode_by_name(opcode).pop):
            raise Exception("Stack push and pop unmatch")



    def _init_global_state(self, path_conditions_and_vars, global_state):

        new_var = BitVec("Is", 256)
        sender_address = simplify(new_var & CONSTANT_ONES_159)
        # add to graph
        s_node = SenderNode("Is", new_var)
        self.graph.addVarNode(new_var, s_node)

        new_var = BitVec("Ia", 256)
        receiver_address = simplify(new_var & CONSTANT_ONES_159)
        # add to graph
        r_node = ReceiverNode("Ia", new_var)
        self.graph.addVarNode(new_var, r_node)

        deposited_value = BitVec("Iv", 256)  # value of transaction
        # add to graph
        dv_node = DepositValueNode("Iv", deposited_value)
        self.graph.addVarNode(deposited_value, dv_node)

        init_is = BitVec("init_Is", 256)  # balance of sender
        # add to graph
        isb_node = BalanceNode("init_Is", init_is, sender_address)
        self.graph.addBranchEdge([(s_node, isb_node)], "flowEdge", self.gen.get_path_id())
        self.graph.addVarNode(init_is, isb_node)

        init_ia = BitVec("init_Ia", 256)  # balance of receiver
        # add to graph
        irb_node = BalanceNode("init_Ia", init_is, receiver_address)
        self.graph.addBranchEdge([(r_node, irb_node)], "flowEdge", self.gen.get_path_id())
        self.graph.addVarNode(init_ia, irb_node)

        new_var_name = self.gen.gen_data_size()
        new_var = BitVec(new_var_name, 256)
        # add to graph
        ds_node = InputDataSizeNode(new_var_name, new_var)
        self.graph.addVarNode(new_var, ds_node)
        self.call_data_size = new_var  # size of input data
        # the bytecode of evm bytecode
        if self.runtime.disasm_file.endswith('.disasm'):
            evm_file_name = self.runtime.disasm_file[:-6] + "evm"
            with open(evm_file_name, 'r') as evm_file:
                self.evm = evm_file.read()
        else:
            self.evm = self.runtime.evm
        new_var_name = self.gen.gen_gas_price_var()
        gas_price = BitVec(new_var_name, 256)
        # add to graph
        gp_node = GasPriceNode(new_var_name, gas_price)
        self.graph.addVarNode(gas_price, gp_node)

        new_var_name = self.gen.gen_origin_var()
        origin = BitVec(new_var_name, 256)
        # add to graph
        os_node = OriginNode(new_var_name, origin)
        self.graph.addVarNode(origin, os_node)

        new_var_name = self.gen.gen_coin_base()
        currentCoinbase = BitVec(new_var_name, 256)
        # add to graph
        cb_node = CoinbaseNode(new_var_name, currentCoinbase)
        self.graph.addVarNode(currentCoinbase, cb_node)

        new_var_name = self.gen.gen_number()
        currentNumber = BitVec(new_var_name, 256)
        # add to graph
        bn_node = CurrentNumberNode(new_var_name, currentNumber)
        self.graph.addVarNode(currentNumber, bn_node)

        new_var_name = self.gen.gen_difficult()
        currentDifficulty = BitVec(new_var_name, 256)
        # add to graph
        d_node = DifficultyNode(new_var_name, currentDifficulty)
        self.graph.addVarNode(currentDifficulty, d_node)

        new_var_name = self.gen.gen_gas_limit()
        currentGasLimit = BitVec(new_var_name, 256)
        # add to graph
        gl_node = GasLimitNode(new_var_name, currentGasLimit)
        self.graph.addVarNode(currentGasLimit, gl_node)

        new_var_name = self.gen.gen_timestamp()
        currentTimestamp = BitVec(new_var_name, 256)
        # add to graph
        ts_node = TimeStampNode(new_var_name, currentTimestamp)
        self.graph.addVarNode(currentTimestamp, ts_node)

        # set all the world state before symbolic execution of tx
        global_state["Ia"] = {}  # the state of the current current contract
        global_state["miu_i"] = 0  # the size of memory in use, 1 == 32 bytes == 256 bits
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
        global_state["balance"][global_state["sender_address"]] = simplify(init_is - deposited_value)
        global_state["balance"][global_state["receiver_address"]] = simplify(init_ia + deposited_value)

    def is_testing_evm(self):
        return global_params.UNIT_TEST != 0

    def compare_storage_and_gas_unit_test(self, global_state, UNIT_TEST):
        unit_test = pickle.load(open(PICKLE_PATH, 'rb'))
        test_status = unit_test.compare_with_symExec_result(global_state, UNIT_TEST)
        exit(test_status)

    # real type of start and end will not locate symbolic type of start and end, start and end are both include(i.e. [
    # start, end]
    # value is type of {BitVec(256), , MemInput, MemEvm, real},
    # elements in mem/memory are of {BitVec(256)/BitVec(8), MemInput, MemEvm, real}
    def write_memory(self, start, end, value, params):
        try:
            if isAllReal(start, end):
                memory = params.memory
                old_size = len(memory) // 32
                new_size = ceil32(end) // 32
                mem_extend = (new_size - old_size) * 32
                memory.extend([0] * mem_extend)
                size = end - start
                for i in range(size, -1, -1):
                    if type(value) == MemInput:  # CallDataCopy
                        memory[start + i] = MemInput(value.start+i, value.start+i)
                    elif type(value) == MemEvm:  # CodeCopy
                        memory[start + i] = MemEvm(value.start+i, value.start+i)
                    elif type(value) == MemReturn:
                        memory[start + i] = MemReturn(value.start+i, value.start+i, value.pc)
                    elif type(value) == MemExtCode:
                        memory[start + i] = MemExtCode(value.start+i, value.start+i, value.address)
                    else:
                        assert(size <= 31)  # MSTORE8 or MSTORE
                        value = to_symbolic(value)
                        memory[start + i] = convertResult(Extract(8 * (size - i) + 7, 8 * (size - i), value))
            else:
                # todo: the overlaps between symbolic vars should be dealed with? but it's very difficult.
                for key in params.mem:
                    try:
                        if int(str(start - key)) == 0:
                            params.mem.pop(key)
                    except:
                        pass

                params.mem[(start, end)] = value
        except Exception as err:
            log.error(str(err))
        return

    def getSubstitudeExpr(self, expr, mapping_overflow_var_expr):
        result = to_symbolic(expr)
        while True:
            flag = False
            l_vars = get_vars(result)
            for var in l_vars:
                if var in mapping_overflow_var_expr:
                    flag = True
                    result = z3.substitute(result, (var, mapping_overflow_var_expr[var]))
            if not flag:
                break

        return convertResult(result)

    # load a value of 32 bytes size from memory indexed by "start"(in byte)
    # the sort of return value should be in { real int, BitVec(256)}
    def load_memory(self, start, params):
        try:
            if isReal(start):
                data = []
                for i in range(0, 32):  # [31, 30, ..., 0]
                    if start+i >= len(params.memory):
                        return 0
                    value = params.memory[start+i]
                    if type(value) == MemInput:   # a Mnemonic of a need of input data
                        value = self.load_inputdata(value.start, params, one_byte=True)
                    elif type(value) == MemEvm:  # a Mnemonic of a need of evm bytecode
                        if isAllReal(value.start, value.end):  # we can get the real value from bytecode file
                            value = int(self.evm[value.start*2:(value.end+1)*2], 16)
                        else:  # we have to construct a new symbolic value from evm
                            value = self.load_evm_data(value.start, params, one_byte=True)
                    elif type(value) == MemReturn:
                        value = self.load_returndata(value.start, value.pc, params, one_byte=True)
                    elif type(value) == MemExtCode:
                        value = self.load_extcode(value.start, value.address, params, one_byte=True)
                    else:  # the value from memory is exactly what we want, so nothing is needed to do
                        value = to_symbolic(value, 8)  # it maybe real
                    data.append(value)

                result = to_symbolic(data[0])
                for i in range(1, 32):
                    result = Concat(result, to_symbolic(data[i]))
            else:
                result = None

                for (v1, v2) in params.mem:
                    key = v1  # todo: v2 is not used for detection of out of bounds
                    subs = subexpression(to_symbolic(key), start)
                    if subs is None:
                        continue
                    else:
                        value = params.mem[(v1, v2)]
                        if type(value) == MemInput:
                            result = self.load_inputdata(convertResult(subs + value.start), params)
                        elif type(value) == MemEvm:
                            if isReal(convertResult(subs)) and isAllReal(value.start, value.end):
                                result = int(self.evm[(convertResult(subs) + value.start)*2:
                                                      ((convertResult(subs) + value.start)+32)*2], 16)
                            else:
                                result = self.load_evm_data(convertResult(subs + value.start), params)
                        elif type(value) == MemReturn:
                            result = self.load_returndata(convertResult(subs + value.start), value.pc, params)
                        elif type(value) == MemExtCode:
                            result = self.load_extcode(convertResult(subs + value.start), value.address, params)
                        else:  # BitVec(256) or real
                            assert (type(value) == six.integer_types or value.sort() == BitVecSort(256))
                            if str(subs) != "0":  # conditions we don't expect
                                log.info("conditions we don't expect from memory load of symbolic indexs")
                            result = value

                        break
        except Exception as err:
            log.error(str(err))

        if result is None:
            log.info("conditions we don't expect from memory load of symbolic indexs for not stored value")
            new_var_name = self.gen.gen_mem_var(start, params.global_state["pc"]-1, self.gen.get_path_id())
            result = BitVec(new_var_name, 256)
            # add to graph
            s_node = addExpressionNode(self.graph, start, self.gen.get_path_id())
            node = MemoryNode(new_var_name, result, start)
            self.graph.addBranchEdge([(s_node, node)], "flowEdge", self.gen.get_path_id())
            self.graph.addVarNode(result, node)

            params.mem[start, convertResult(start + 31)] = result

        return convertResult(result)

    def load_returndata(self, start, pc, params, one_byte=False):  # size = 32 bytes,  start is in bytes, pc is real int
        if pc in params.returndata:
            returndata = params.returndata[pc]
        else:
            returndata = {}
            params.returndata[pc] = returndata

        value = None
        exist_flag = False
        # check if there is the same root symbolic values
        for key in returndata.keys():
            try:
                size = int(str(simplify(to_symbolic(start)-key)))  # explicitly include in old values
                if one_byte and size < 32 and size >= 0:
                    exist_flag = True
                    value = returndata[key]
                    break
                elif not one_byte and size == 0:
                    return returndata[key]
            except:
                continue

        if exist_flag and one_byte:
            offset = (size % 32)
            return Extract(255-8*offset, 255-(8*offset+7), value)
        else:
            new_var_name = self.gen.gen_return_data(pc, convertResult(start), convertResult(start + 31), self.gen.get_path_id())
            value = BitVec(new_var_name, 256)
            # add to graph
            s_node = addExpressionNode(self.graph, start, self.gen.get_path_id())
            node = ReturnDataNode(new_var_name, value)
            r_node = self.graph.getCallReturnNode(pc)
            self.graph.addBranchEdge([(s_node, node), (r_node, node)], "flow_edge", self.gen.get_path_id())
            self.graph.addVarNode(value, node)

            returndata[start] = value
            if one_byte:
                return Extract(255-start*8, 255-start*8-7, value)

        return value

    def load_extcode(self, start, address, params, one_byte=False):  # size = 32 bytes,  start is in bytes
        if address in self.ext:
            extcode = self.ext_code_dict[address]
        else:
            extcode = {}
            self.ext_code_dict[address] = extcode

        value = None
        exist_flag = False
        # check if there is the same root symbolic values
        for key in extcode.keys():
            try:
                size = int(str(simplify(key-start)))  # explicitly include in old values
                exist_flag = True
                break
            except:
                continue

        if exist_flag:
            offset = (size % 32)
            if offset:  # not in a slot, value should be a concat of bits extracted from both value1 and value
                start1 = start - offset
                value1 = None

                s = SSolver(mapping_var_expr=params.mapping_overflow_var_expr)
                s.set("timeout", global_params.TIMEOUT)
                for x in extcode:
                    s.push()
                    s.add(Not(x == start1))
                    if check_unsat(s):
                        value1 = extcode[x]
                        break
                    s.pop()
                if value1 is None:
                    new_var_name = self.gen.gen_ext_code_data(address, convertResult(start1), convertResult(start1+31))
                    value1 = BitVec(new_var_name, 256)
                    # add to graph
                    a_node = addAddressNode(self.graph, address, self.gen.get_path_id())
                    node = CodeNode(new_var_name, value1, address)
                    self.graph.addBranchEdge([(a_node, node)], "flowEdge", self.gen.get_path_id())
                    self.graph.addVarNode(value1, node)

                    extcode[start1] = value1

                if one_byte:  # return only a byte of inputdata indexed by start, so there is no need for value2
                    return Extract(8*offset+7, 8*offset, value1)

                start2 = start - offset + 32
                value2 = None


                for x in extcode:
                    s.push()
                    s.add(Not(x == start2))
                    if check_unsat(s):
                        value2 = extcode[x]
                        break
                    s.pop()
                if value2 is None:
                    new_var_name = self.gen.gen_ext_code_data(address, convertResult(start2), convertResult(start2 + 31))
                    value2 = BitVec(new_var_name, 256)
                    # add to graph
                    a_node = addAddressNode(self.graph, address, self.gen.get_path_id())
                    node = CodeNode(new_var_name, value2, address)
                    self.graph.addBranchEdge([(a_node, node)], "flowEdge", self.gen.get_path_id())
                    self.graph.addVarNode(value2, node)

                    extcode[start2] = value2

                value = Concat(Extract(offset-1, 0, value2), Extract(255, offset, value1))

            else:
                s = SSolver(mapping_var_expr=params.mapping_overflow_var_expr)
                s.set("timeout", global_params.TIMEOUT)

                for x in extcode:
                    s.push()
                    s.add(Not(x == start))
                    if check_unsat(s):
                        value = extcode[x]
                        break
                    s.pop()
                if value is None:
                    new_var_name = self.gen.gen_ext_code_data(address, convertResult(start), convertResult(start + 31))
                    value = BitVec(new_var_name, 256)
                    # add to graph
                    a_node = addAddressNode(self.graph, address, self.gen.get_path_id())
                    node = CodeNode(new_var_name, value, address)
                    self.graph.addBranchEdge([(a_node, node)], "flowEdge", self.gen.get_path_id())
                    self.graph.addVarNode(value, node)

                    extcode[start] = value
        else:
            new_var_name = self.gen.gen_ext_code_data(address, convertResult(start), convertResult(start + 31))
            value = BitVec(new_var_name, 256)
            # add to graph
            a_node = addAddressNode(self.graph, address, self.gen.get_path_id())
            node = CodeNode(new_var_name, value, address)
            self.graph.addBranchEdge([(a_node, node)], "flowEdge", self.gen.get_path_id())
            self.graph.addVarNode(value, node)

            extcode[start] = value
            if one_byte:
                return Extract(7, 0, value)

        return value

    # all symbolic values of InputData is BitVec(256), and load and read of InputData is of 256 bits or 8 bits
    # 1. all inputdata indexed with real address is separated with 256 bits, i.e. input_data_0_255, input_data_256_511...
    # 2. and inputdata indexed with symbolic address is separated with 256 bits too, i.e. inputdata_start_end, with
    #    end = start + 255
    #
    # usage: this is used to get input_data vars from start to end,
    #
    # start: symbolic or real
    #
    # return type : BitVec(256) if one = False, else BitVec(8)
    def load_inputdata(self, start, params, one_byte=False):  # size = 32 bytes,  start is in bytes
        # check if there is the same root symbolic values
        for key in self.input_dict.keys():
            try:
                size = int(str(simplify(key-start)))  # explicitly include in old values
                if size == 0 and one_byte:
                    return Extract(7, 0, self.input_dict[key])
                elif size == 0 and not one_byte:
                    return self.input_dict[key]
                break
            except:
                continue

        new_var_name = self.gen.gen_data_var(convertResult(start), convertResult(start + 31))
        value = BitVec(new_var_name, 256)
        # add to graph

        node = InputDataNode(new_var_name, value, start)
        self.graph.addVarNode(value, node)
        if is_expr(start):
            if is_const(start):
                s_node = self.graph.getVarNode(start)
            else:
                s_node = addExpressionNode(self.graph, start, self.gen.get_path_id())
            self.graph.addBranchEdge([(s_node, node)], "flow_edge", self.gen.get_path_id())

        self.input_dict[start] = value
        if one_byte:
            return Extract(7, 0, value)

        return value

    # start is in bytes, return a BitVec(8) as a byte of evm bytecode indexed by start if one_byte == True, otherwish
    # return a BitVec(256)
    def load_evm_data(self, start, params, one_byte=False):
        value = None
        exist_flag = False
        # check if there is the same root symbolic values
        for key in self.evm_dict.keys():
            try:
                size = int(str(simplify(key - start)))  # explicitly include in old values
                exist_flag = True
                break
            except:
                continue

        if exist_flag:
            offset = (size % 32)
            if offset:  # not in a slot, value should be a concat of bits extracted from both value1 and value
                start1 = start - offset
                value1 = None

                s = SSolver(mapping_var_expr=params.mapping_overflow_var_expr)
                s.set("timeout", global_params.TIMEOUT)
                for x in self.evm_dict:
                    s.push()
                    s.add(Not(x == start1))
                    if check_unsat(s):
                        value1 = self.evm_dict[x]
                        break
                    s.pop()
                if value1 is None:
                    new_var_name = self.gen.gen_evm_data(convertResult(start1), convertResult(start1 + 31))
                    value1 = BitVec(new_var_name, 256)
                    # add to graph
                    node = CodeNode(new_var_name, value1)
                    self.graph.addVarNode(value1, node)

                    self.evm_dict[start1] = value1

                if one_byte:  # return only a byte of inputdata indexed by start, so there is no need for value2
                    return Extract(8 * offset + 7, 8 * offset, value1)

                start2 = start - offset + 32
                value2 = None

                for x in self.evm_dict:
                    s.push()
                    s.add(Not(x == start2))
                    if check_unsat(s):
                        value2 = self.evm_dict[x]
                        break
                    s.pop()
                if value2 is None:
                    new_var_name = self.gen.gen_evm_data(convertResult(start2), convertResult(start2 + 31))
                    value2 = BitVec(new_var_name, 256)
                    # add to graph
                    node = CodeNode(new_var_name, value2)
                    self.graph.addVarNode(value2, node)
                    self.evm_dict[start2] = value2

                value = Concat(Extract(offset - 1, 0, value2), Extract(255, offset, value1))

            else:
                s = SSolver(mapping_var_expr=params.mapping_overflow_var_expr)
                s.set("timeout", global_params.TIMEOUT)

                for x in self.evm_dict:
                    s.push()
                    s.add(Not(x == start))
                    if check_unsat(s):
                        value = self.evm_dict[x]
                        break
                    s.pop()
                if value is None:
                    new_var_name = self.gen.gen_evm_data(convertResult(start), convertResult(start + 31))
                    value = BitVec(new_var_name, 256)
                    # add to graph
                    node = CodeNode(new_var_name, value)
                    self.graph.addVarNode(value, node)

                    self.evm_dict[start] = value
        else:
            new_var_name = self.gen.gen_evm_data(convertResult(start), convertResult(start + 31))
            value = BitVec(new_var_name, 256)
            # add to graph
            node = CodeNode(new_var_name, value)
            self.graph.addVarNode(value, node)

            self.evm_dict[start] = value
            if one_byte:
                return Extract(7, 0, value)

        return value


class Parameter:

    def __init__(self, **kwargs):
        attr_defaults = {
            # for all elem in stack, they should be either real unsigned int of python or BitVec(256) of z3,i.e without BitVecRef
            # or other types of data
            "stack": [],
            # all variables located with real type of address and size is stored and loaded by memory, and with one
            # symbolic var in address or size, the value is stored and loaded in mem
            "memory": [],
            "mem": {},

            # used to show all calls of current path, every element is the real int representing pc of call instruction
            "calls": [],

            # the returndata of every call instruction, {pc: {start: value}}
            "returndata": {},

            # mark all the visited edges of current_path, for detecting loops and control the loop_depth under limits
            # {Edge:num}
            "visited": {},

            # path conditions and vars form constrains of this path
            "path_conditions_and_vars": {},

            # all the state of blockchain for this path
            "global_state": {},

            # gas should be always kept real type
            "gas": 0,

        }
        for (attr, default) in six.iteritems(attr_defaults):
            setattr(self, attr, kwargs.get(attr, default))

    def copy(self):
        _kwargs = custom_deepcopy(self.__dict__)
        return Parameter(**_kwargs)

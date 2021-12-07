import logging
import traceback
import pickle
import psutil
import time
import re
import copy
import six

from collections import namedtuple
from z3 import is_expr, BitVec, BitVecVal, BoolVal, Not, And, UDiv, URem, If, ULT, UGT, LShR, Concat, Extract, \
    BitVecSort

import interpreter.params
import global_params

from graphBuilder.XGraph import *
from interpreter.symbolicVarGenerator import *
from uinttest.global_test_params import PICKLE_PATH
from interpreter.opcodes import opcode_by_name
from utils import custom_deepcopy, convert_result, to_symbolic, is_all_real, ceil32

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

MAX_MEMORY_SIZE = 1024 * 1024


class EVMInterpreter:
    def __init__(self, runtime, cname):
        self.cname = cname
        self.gen = Generator()

        self.runtime = runtime
        self.sig_to_func = runtime.source_map.sig_to_func

        self.graph = XGraph("all", self.runtime.source_map)
        self.graphs = {}
        self.tmp_graph = None

        self.path_conditions = []


        # number of paths, terminated by normal or exception
        self.total_no_of_paths = {"normal": 0, "exception": 0}
        self.paths = []

        self.current_path = []
        # impossible paths
        self.impossible_paths = []

        self.total_visited_pc = {}  # visited pc and its times
        self.total_visited_edges = {}  # visited edges and its times

        self.call_data_size = None
        self.evm = None

        self.call_conditions = []

        self.current_function = ""

    def in_function(self, block):
        if block in self.runtime.start_block_to_func_sig:
            func_sig = self.runtime.start_block_to_func_sig[block]
            if self.sig_to_func is not None:
                for key in self.sig_to_func:
                    if eval("0x"+key) == eval("0x"+func_sig):
                        current_func_name = self.sig_to_func[key]
                        break
                pattern = r'(\w[\w\d_]*)\((.*)\)$'
                match = re.match(pattern, current_func_name)
                if match:
                    current_func_name = list(match.groups())[0]
            else:
                current_func_name = func_sig
            return current_func_name
        else:
            return None

    def sym_exec(self):
        path_conditions_and_vars = {"path_condition": [], "path_condition_node": []}
        global_state = {"balance": {}, "pc": 0}
        self._init_global_state(path_conditions_and_vars, global_state)
        params = Parameter(path_conditions_and_vars=path_conditions_and_vars, global_state=global_state)
        return self._sym_exec_block(params, 0, 0)

    # Symbolically executing a block from the start address
    def _sym_exec_block(self, params, block, pre_block):
        start_time = time.time()

        self.current_path.append(block)


        function_name = self.in_function(block)
        if function_name is not None:
            log.info("in function %s", function_name)
            # self.tmp_graph = copy.deepcopy(self.graph)
            # self.graphs[function_name] = copy.deepcopy(self.graph)
            # self.graph = self.graphs[function_name]
            self.graph.reset_graph(function_name)
            self.graph.graph.add_node(self.graph.current_constraint_node)
            self.current_function = function_name
            if self.runtime.source_map is not None:
                XGraph.current_lines = self.runtime.source_map.get_lines_from_pc(block)

        visited = params.visited
        global_state = params.global_state

        assert str(self.graph.get_current_constraint_node().get_value()) == \
               str(params.path_conditions_and_vars["path_condition_node"][-1].get_value()), \
            "wrong constraint node\n" + "first: " + str(self.graph.get_current_constraint_node().get_value()) + "\n" + \
            str(params.path_conditions_and_vars["path_condition_node"][-1].get_value())

        if block < 0 or block not in self.runtime.vertices:
            self.total_no_of_paths["exception"] += 1
            log.info("Unknown jump address %d. Terminating this path ...", block)
            self.call_conditions = []

            if function_name is not None:
                # self.graph = self.tmp_graph
                self.graphs[function_name] = self.graph.get_graph()
                self.graph.reset_graph("")
                self.current_function = ""
                XGraph.current_lines = []

            self.paths.append(copy.deepcopy(self.current_path))
            self.current_path.pop()
            return

        log.debug("Reach block address %d \n", block)

        current_edge = (pre_block, block)

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

        # log.debug("visiting edge: "+str(current_edge[0]) + "->" + str(current_edge[1]) +
        #           " ;path times: " + str(visited[current_edge]) +
        #           " ;total times: " + str(self.total_visited_edges[current_edge]))

        # TODO: how to implement better loop dectection? This may cost too much time
        # or self.total_visited_edges[current_edge] > 5:
        # if self.current_path.count(block) > 2:
        if visited[current_edge] > interpreter.params.LOOP_LIMIT and self.runtime.jump_type[block] == "conditional" or self.total_visited_edges[current_edge] > 5:
            self.total_no_of_paths["normal"] += 1
            self.gen.gen_path_id()
            log.debug("Overcome a number of loop limit. Terminating this path ...")
            self.call_conditions = []

            if function_name is not None:
                # self.graph = self.tmp_graph
                self.graphs[function_name] = self.graph.get_graph()
                self.graph.reset_graph("")
                self.current_function = ""
                XGraph.current_lines = []

            self.paths.append(copy.deepcopy(self.current_path))
            self.current_path.pop()
            return

        # TODO: gas_used cannot be calculated accurately because of miu, now we keep the less used gas by instructions
        #  and less memory used, and there should be someone to learn about gas calculation of evm exactly
        if params.gas > interpreter.params.GAS_LIMIT:
            self.total_no_of_paths["normal"] += 1
            self.gen.gen_path_id()
            log.debug("Run out of gas. Terminating this path ... ")
            self.call_conditions = []

            if function_name is not None:
                # self.graph = self.tmp_graph
                self.graphs[function_name] = self.graph.get_graph()
                self.graph.reset_graph("")

            self.paths.append(copy.deepcopy(self.current_path))
            self.current_path.pop()
            self.current_function = ""
            XGraph.current_lines = []
            return

        block_ins = self.runtime.vertices[block].get_instructions()

        memory_inf = psutil.virtual_memory()
        log.debug("Before instructions free memory: %d M" % int(memory_inf.free / (1024 * 1024)))
        # Execute every instruction, one at a time
        # TODO： this exception should not be caught, because it may be a bug
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
            log.error("This path results in an exception: %s, Terminating this path ...", str(error))
            traceback.print_exc()
            self.call_conditions = []

            if function_name is not None:
                # self.graph = self.tmp_graph
                self.graphs[function_name] = self.graph.get_graph()
                self.graph.reset_graph("")
                self.current_function = ""
                XGraph.current_lines = []

            self.paths.append(copy.deepcopy(self.current_path))
            self.current_path.pop()
            return

        log.debug("After instructions free memory: %d M" % int(memory_inf.free / (1024 * 1024)))

        if self.is_testing_evm():
            self.compare_storage_and_gas_unit_test(global_state, global_params.UNIT_TEST)

        # Go to next Basic Block(s)
        if self.runtime.jump_type[block] == "terminal":
            self.total_no_of_paths["normal"] += 1
            self.gen.gen_path_id()
            log.debug("TERMINATING A PATH ...")
            self.paths.append(copy.deepcopy(self.current_path))
            self.current_path.pop()

            if function_name is not None:
                # self.graph = self.tmp_graph
                self.graphs[function_name] = self.graph.get_graph()
                self.graph.reset_graph("")
                self.current_function = ""
                XGraph.current_lines = []

            return

        elif self.runtime.jump_type[block] == "unconditional":  # executing "JUMP"
            # TODO: how to deal with symbolic jump targets and more than one jump targets for unconditional jump
            # now we only deal with unconditional jump with only one real target
            successor = self.runtime.vertices[block].get_jump_target()
            if successor is None:
                self.total_no_of_paths["exception"] += 1
                self.gen.gen_path_id()
            else:
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
            # if branch expression is none, it must be condition like symbolic target address
            if branch_expression is not None:
                # branch_expression_node = self.runtime.vertices[block].get_branch_expression_node()
                str_expr = str(branch_expression)
                # log.debug("Branch expression: " + str_expr)
                selector = None
                if str_expr != "False":
                    left_branch = self.runtime.vertices[block].get_jump_targets()[-1]
                    selector = self.in_function(left_branch)
                    if selector is not None:
                        branch_expression_node = self.graph.add_constraint_node(branch_expression,
                                                                                pc=self.runtime.vertices[block].end,
                                                                                name="*" + selector,
                                                                                flag=True)
                    else:
                        branch_expression_node = self.graph.add_constraint_node(branch_expression,
                                                                                pc=self.runtime.vertices[block].end,
                                                                                flag=True)
                    self.runtime.vertices[block].set_branch_node_expression(branch_expression_node)

                    new_params = params.copy()
                    new_params.global_state["pc"] = left_branch
                    new_params.path_conditions_and_vars["path_condition"].append(branch_expression)
                    new_params.path_conditions_and_vars["path_condition_node"].append(branch_expression_node)
                    self._sym_exec_block(new_params, left_branch, block)
                    self.graph.out_constraint()
                else:
                    self.impossible_paths.append((block, self.runtime.vertices[block].get_jump_targets()[-1]))

                negated_branch_expression = simplify(Not(branch_expression))
                # log.debug("Negated branch expression: " + str(negated_branch_expression))
                if str_expr != "True":
                    if selector is not None:
                        negated_branch_expression_node = self.graph.add_constraint_node(negated_branch_expression,
                                                                                        pc=self.runtime.vertices[block].end,
                                                                                        name=selector,
                                                                                        flag=False)
                    else:
                        negated_branch_expression_node = self.graph.add_constraint_node(negated_branch_expression,
                                                                                        pc=self.runtime.vertices[block].end,
                                                                                        flag=False)
                    self.runtime.vertices[block].set_negated_branch_node_expression(negated_branch_expression_node)
                    right_branch = self.runtime.vertices[block].get_falls_to()
                    params.global_state["pc"] = right_branch
                    params.path_conditions_and_vars["path_condition"].append(negated_branch_expression)
                    params.path_conditions_and_vars["path_condition_node"].append(negated_branch_expression_node)
                    self._sym_exec_block(params, right_branch, block)
                    self.graph.out_constraint()
                else:
                    self.impossible_paths.append((block, self.runtime.vertices[block].get_falls_to()))
        else:
            raise Exception('Unknown Jump-Type')
        end_time = time.time()
        execution_time = end_time - start_time
        log.debug("Block: " + str(block) + " symbolic execution time: %.8s s" % execution_time)

        self.call_conditions = []

        if function_name is not None:
            # self.graph = self.tmp_graph
            self.graphs[function_name] = self.graph.get_graph()
            self.graph.reset_graph("")
            self.current_function = ""
            XGraph.current_lines = []

        self.current_path.pop()
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
        mem = params.mem
        memory = params.memory
        global_state = params.global_state
        path_conditions_and_vars = params.path_conditions_and_vars
        calls = params.calls

        b_len = len(stack)

        instr_parts = str.split(instr, ' ')
        opcode = instr_parts[1]

        visited_pc = instr_parts[0]

        if visited_pc in self.total_visited_pc:
            self.total_visited_pc[visited_pc] += 1
        else:
            self.total_visited_pc[visited_pc] = 1

        log.debug("==============================")
        log.debug("EXECUTING: " + instr)
        # log.debug("LENG_MEM:" + str(len(memory)))
        # log.debug("STACK: " + str(stack))
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

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MUL":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first * second) & UNSIGNED_BOUND_NUMBER

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SUB":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first - second) & UNSIGNED_BOUND_NUMBER

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "DIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = UDiv(to_symbolic(first), second)

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SDIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first / second) & UNSIGNED_BOUND_NUMBER

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = URem(first, to_symbolic(second))

                stack.insert(0, convert_result(computed))
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

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "ADDMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                computed = URem(first + second, to_symbolic(third))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MULMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                computed = URem(first * second, to_symbolic(third))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EXP":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                base = stack.pop(0)
                exponent = stack.pop(0)
                # Type conversion is needed when they are mismatched
                if is_all_real(base, exponent):
                    computed = pow(base, exponent, 2 ** 256)
                else:
                    # The computed value is unknown, this is because power is
                    # not supported in bit-vector theory    
                    new_var_name = self.gen.gen_exp_var(base, exponent)
                    computed = BitVec(new_var_name, 256)
                    # add to graph
                    node = ExpNode(new_var_name, computed, base, exponent)
                    self.graph.cache_var_node(computed, node)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SIGNEXTEND":
            if len(stack) > 1:
                # todo: review this process
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if is_all_real(first, second):
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

                stack.insert(0, convert_result(computed))
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

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "GT":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(UGT(first, to_symbolic(second)), BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(first < second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SGT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(first > second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EQ":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = If(first == second, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "ISZERO":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)

                computed = If(first == 0, BitVecVal(1, 256), BitVecVal(0, 256))

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "AND":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first & second

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "OR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first | second

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "XOR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first ^ second

                stack.insert(0, convert_result(computed))
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

                stack.insert(0, convert_result(computed))
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
                if is_all_real(s0, s1) and s0+s1 < len(memory):
                    data = [x for x in memory[s0: s0 + s1]]
                    value = to_symbolic(data[0], 8)
                    for x in data[1:]:
                        value = Concat(value, to_symbolic(x, 8))

                    value = simplify(value)
                    new_var_name = self.gen.gen_sha3_var(value)
                    computed = BitVec(new_var_name, 256)
                    node = ShaNode(new_var_name, computed, global_state["pc"]-1, value)
                    self.graph.cache_var_node(computed, node)
                else:
                    # Todo:push into the stack a fresh symbolic variable, how to deal with symbolic address and size
                    new_var_name = self.gen.gen_sha3_var("unknown_" +
                                                         str(global_state["pc"] - 1) +
                                                         "_" +
                                                         self.gen.get_path_id())
                    new_var = BitVec(new_var_name, 256)
                    computed = new_var
                    # add to node
                    node = ShaNode(new_var_name, computed, global_state["pc"]-1)
                    self.graph.cache_var_node(computed, node)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        #
        # 30s: Environment Information
        #
        elif opcode == "ADDRESS":  # get address of currently executing account
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["receiverAddress"])
        elif opcode == "BALANCE" or opcode == "SELFBALANCE":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)
                # get balance of address
                new_var = None
                for x in global_state["balance"]:
                    try:
                        if int(str(simplify(to_symbolic(x - address)))) == 0:
                            new_var = global_state["balance"][x]
                            break
                    except:
                        pass

                if new_var is None:
                    new_var_name = self.gen.gen_balance_of(address)
                    new_var = BitVec(new_var_name, 256)
                    global_state["balance"][address] = new_var
                    b_node = BalanceNode(new_var_name, new_var, address)
                    self.graph.cache_var_node(new_var, b_node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLER":  # get caller address
            # that is directly responsible for this execution
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["senderAddress"])
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

                new_var_name = self.gen.gen_data_var(start, convert_result(start + 31), self.current_function)
                value = BitVec(new_var_name, 256)
                node = InputDataNode(new_var_name, value, start, convert_result(start+31))
                self.graph.cache_var_node(value, node)

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
                log.error("unhandled instruction CALLDATACOPY")
                # Todo: implement this instruction
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
                # Todo: implement this instruction
                log.error("unhandled instruction CODECOPY")
            else:
                raise ValueError('STACK underflow')
        elif opcode == "RETURNDATACOPY":
            if len(stack) > 2:
                global_state["pc"] += 1
                mem_start = stack.pop(0)
                return_start = stack.pop(0)
                size = stack.pop(0)  # in bytes
                # Todo: implement this instruction
                log.error("unhandled instruction RETURNDATACOPY")
            else:
                raise ValueError('STACK underflow')
        elif opcode == "RETURNDATASIZE":
            global_state["pc"] += 1
            new_var_name = self.gen.gen_return_data_size(calls[-1])
            new_var = BitVec(new_var_name, 256)
            node = ReturnDataSizeNode(new_var_name, new_var)
            self.graph.cache_var_node(new_var, node)

            stack.insert(0, new_var)
        elif opcode == "GASPRICE":
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["gas_price"])
        elif opcode == "EXTCODESIZE":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)

                new_var_name = self.gen.gen_code_size_var(address)
                new_var = BitVec(new_var_name, 256)
                node = ExtcodeSizeNode(new_var_name, new_var, address)
                self.graph.cache_var_node(new_var, node)

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
                # TODO: implement this instruction
                log.error("unhandled instruction EXTCODECOPY")
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EXTCODEHASH":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                address = stack.pop(0)

                new_var_name = self.gen.gen_code_size_var(address)
                new_var = BitVec(new_var_name, 256)
                node = ExtcodeHashNode(new_var_name, new_var, address)
                self.graph.cache_var_node(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        #
        #  40s: Block Information
        #
        elif opcode == "BLOCKHASH":  # information from block header
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                block_number = stack.pop(0)

                new_var_name = self.gen.gen_blockhash(block_number)
                value = BitVec(new_var_name, 256)
                node = BlockhashNode(new_var_name, value, block_number)

                self.graph.cache_var_node(value, node)

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
        elif opcode == "MSTORE":  # bigger end of stack value is stored in lower address of memory
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                self.write_memory(stored_address, stored_value, params)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MSTORE8":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                self.write_memory(stored_address, stored_value, params, size=0)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLOAD":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                position = stack.pop(0)

                value = None
                for key in global_state["storage"]:
                    try:
                        if int(str(simplify(to_symbolic(key-position)))) == 0:
                            value = global_state["storage"][key]
                            break
                    except:
                        pass

                if value is None:
                    new_var_name = self.gen.gen_storage_var(position)
                    value = BitVec(new_var_name, 256)
                    node = self.graph.get_state_node(position)
                    if node is None:
                        node = StateNode(new_var_name, value, position, global_state["pc"]-1)
                        node = self.graph.add_state_node(position, node)
                        self.graph.add_branch_edge([(self.graph.get_current_constraint_node(), node)],
                                                   "constraint_flow")

                    global_state["storage"][position] = value
                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')

        elif opcode == "SSTORE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                global_state["storage"][stored_address] = stored_value
                # add to graph
                node = SStoreNode(opcode, global_state["pc"] - 1, [[], []])
                self.graph.add_sstore_node(node, [stored_address, stored_value], self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode == "JUMP":
            if len(stack) > 0:
                target_address = stack.pop(0)

                if is_expr(target_address):
                    log.error("Target address of JUMP must be an integer: but it is %s", str(target_address))
                    self.runtime.vertices[block].set_jump_targets(None)
                else:
                    if target_address not in self.runtime.vertices:
                        raise Exception("Target address for jump is  illegal")
                    self.runtime.vertices[block].set_jump_targets(target_address)
                    if target_address not in self.runtime.edges[block]:
                        self.runtime.edges[block].append(target_address)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "JUMPI":
            # We need to prepare two branches
            if len(stack) > 1:
                target_address = stack.pop(0)
                if is_expr(target_address):
                    log.error("Target address of JUMPI must be an integer: but it is %s", str(target_address))
                    self.runtime.vertices[block].set_branch_expression(None)
                else:
                    if target_address not in self.runtime.vertices:
                        raise Exception("Target address for jumpi is illegal")
                    self.runtime.vertices[block].set_jump_targets(target_address)
                    if target_address not in self.runtime.edges[block]:
                        self.runtime.edges[block].append(target_address)

                    flag = stack.pop(0)
                    if not is_expr(flag):  # must be int
                        if flag == 0:
                            branch_expression = BoolVal(False)
                        else:
                            branch_expression = BoolVal(True)
                    else:
                        branch_expression = to_symbolic(flag != 0)
                        for x in self.call_conditions:
                            branch_expression = And(branch_expression, x)

                    branch_expression = simplify(branch_expression)

                    self.runtime.vertices[block].set_branch_expression(branch_expression)
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
            # Todo: we do not have this precisely. It depends on both the
            #  initial gas and the amount has been depleted
            #  we need to think about this in the future, in case precise gas
            #  can be tracked
            global_state["pc"] = global_state["pc"] + 1
            new_var_name = self.gen.gen_gas_var(global_state["pc"]-1)
            new_var = BitVec(new_var_name, 256)
            node = GasNode(new_var_name, new_var)
            self.graph.cache_var_node(new_var, node)

            stack.insert(0, new_var)
        elif opcode == "JUMPDEST":
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
            self.graph.cache_var_node(pushed_value, node)
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
        elif opcode == "CREATE" or opcode == "CREATE2":  # Todo: the different of create and create2
            if len(stack) > 2:
                global_state["pc"] += 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)

                new_var_name = self.gen.gen_contract_address(global_state["pc"]-1)
                new_var = BitVec(new_var_name, 256)
                node = AddressNode(new_var_name, new_var)
                self.graph.cache_var_node(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALL":
            if len(stack) > 6:
                calls.append(global_state["pc"])
                global_state["pc"] = global_state["pc"] + 1

                out_gas = stack.pop(0)
                recipient = stack.pop(0)
                transfer_amount = stack.pop(0)
                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_output = stack.pop(0)

                # update the balance of call's sender that's this contract's address
                balance_ia = global_state["balance"][global_state["receiverAddress"]]
                new_balance_ia = convert_result(balance_ia - transfer_amount)
                global_state["balance"][global_state["receiverAddress"]] = new_balance_ia
                # update the balance of recipient
                old_balance = None
                for key in global_state["balance"]:
                    try:
                        if int(str(simplify(to_symbolic(key - recipient)))):
                            old_balance = global_state["balance"].pop(key)
                            break
                    except:
                        pass
                if old_balance is None:
                    new_balance_name = self.gen.gen_balance_of(recipient)
                    old_balance = BitVec(new_balance_name, 256)
                global_state["balance"][recipient] = convert_result(old_balance + transfer_amount)
                # add balance change to graph
                self.graph.change_balance_node(global_state["receiverAddress"],
                                               BitVec("init_Is", 256),
                                               new_balance_ia,
                                               self.gen.get_path_id())
                self.graph.change_balance_node(recipient,
                                               BitVec(self.gen.gen_balance_of(recipient), 256),
                                               global_state["balance"][recipient],
                                               self.gen.get_path_id())

                # add enough_fund condition to path_conditions
                is_enough_fund = And((transfer_amount <= balance_ia), old_balance >= 0)
                self.call_conditions.append(is_enough_fund)

                # get return status
                new_var_name = self.gen.gen_return_status(calls[-1])
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                return_node = ReturnStatusNode(new_var_name, new_var_name)

                # add call instruction to graph
                self.graph.add_message_call_node(opcode,
                                                 global_state["pc"]-1,
                                                 [out_gas, recipient, transfer_amount,
                                                  start_data_input, size_data_input,
                                                  start_data_output, size_data_output],
                                                 return_node,
                                                 self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLCODE":
            if len(stack) > 6:
                calls.append(global_state["pc"])
                global_state["pc"] = global_state["pc"] + 1

                out_gas = stack.pop(0)
                recipient = stack.pop(0)
                transfer_amount = stack.pop(0)
                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_output = stack.pop(0)

                # update the balance of call's sender that's this contract's address
                balance_ia = global_state["balance"][global_state["receiverAddress"]]
                new_balance_ia = convert_result(balance_ia - transfer_amount)
                global_state["balance"][global_state["receiverAddress"]] = new_balance_ia
                # update the balance of recipient
                old_balance = None
                for key in global_state["balance"]:
                    try:
                        if int(str(simplify(to_symbolic(key - recipient)))):
                            old_balance = global_state["balance"].pop(key)
                            break
                    except:
                        pass
                if old_balance is None:
                    new_balance_name = self.gen.gen_balance_of(recipient)
                    old_balance = BitVec(new_balance_name, 256)
                global_state["balance"][recipient] = convert_result(old_balance + transfer_amount)
                # add balance change to graph
                self.graph.change_balance_node(global_state["receiverAddress"],
                                               BitVec("init_Is", 256),
                                               new_balance_ia,
                                               self.gen.get_path_id())
                self.graph.change_balance_node(recipient,
                                               BitVec(self.gen.gen_balance_of(recipient), 256),
                                               global_state["balance"][recipient],
                                               self.gen.get_path_id())

                # add enough_fund condition to path_conditions
                is_enough_fund = And((transfer_amount <= balance_ia), old_balance >= 0)
                self.call_conditions.append(is_enough_fund)

                # get return status
                new_var_name = self.gen.gen_return_status(calls[-1])
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                return_node = ReturnStatusNode(new_var_name, new_var_name)

                # add call instruction to graph
                self.graph.add_message_call_node(opcode,
                                                 global_state["pc"] - 1,
                                                 [out_gas, recipient, transfer_amount,
                                                  start_data_input, size_data_input,
                                                  start_data_output, size_data_output],
                                                 return_node,
                                                 self.gen.get_path_id())


            else:
                raise ValueError('STACK underflow')
        elif opcode in ("DELEGATECALL", "STATICCALL"):
            if len(stack) > 5:
                calls.append(global_state["pc"])
                global_state["pc"] = global_state["pc"] + 1
                out_gas = stack.pop(0)
                recipient = stack.pop(0)

                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_output = stack.pop(0)

                # the execution is possibly okay
                new_var_name = self.gen.gen_return_status(calls[-1])
                new_var = BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                return_node = ReturnStatusNode(new_var_name, new_var)

                # add call instruction to graph
                self.graph.add_message_call_node(opcode,
                                                 global_state["pc"] - 1,
                                                 [out_gas, recipient,
                                                  start_data_input, size_data_input,
                                                  start_data_output, size_data_output],
                                                 return_node,
                                                 self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode in ("RETURN", "REVERT"):
            if len(stack) > 1:
                stack.pop(0)
                stack.pop(0)
                if opcode == "REVERT":
                    node = TerminalNode(opcode, global_state["pc"])
                    self.graph.add_terminal_node(node)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SUICIDE":
            global_state["pc"] = global_state["pc"] + 1
            recipient = stack.pop(0)
            # get transfer_amount and update the new balance
            transfer_amount = None
            for key in global_state["balance"]:
                try:
                    if int(str(simplify(to_symbolic(key - global_state["receiverAddress"])))) == 0:
                        transfer_amount = global_state["balance"][key]
                        global_state["balance"][key] = 0
                        break
                except:
                    pass
            assert transfer_amount is not None, "transfer amount can not be None"
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
                balance_recipent = BitVec(new_address_value_name, 256)

            new_balance = balance_recipent + transfer_amount
            global_state["balance"][recipient] = new_balance
            # add to graph
            self.graph.change_balance_node(recipient,
                                           BitVec(self.gen.gen_balance_of(recipient), recipient),
                                           new_balance,
                                           self.gen.get_path_id())
            self.graph.change_balance_node(global_state["receiverAddress"],
                                           BitVec("init_Ia", 256),
                                           0,
                                           self.gen.get_path_id())

            return
        elif opcode == "SAR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (to_symbolic(first) >> second)

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SHR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = LShR(to_symbolic(first), second)

                stack.insert(0, convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SHL":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (to_symbolic(first) << second)

                stack.insert(0, convert_result(computed))
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
        s_node = SenderNode("Is", new_var)
        self.graph.cache_var_node(new_var, s_node)

        new_var = BitVec("Ia", 256)
        receiver_address = simplify(new_var & CONSTANT_ONES_159)
        r_node = ReceiverNode("Ia", new_var)
        self.graph.cache_var_node(new_var, r_node)

        deposited_value = BitVec("Iv", 256)  # value of transaction
        dv_node = DepositValueNode("Iv", deposited_value)
        self.graph.cache_var_node(deposited_value, dv_node)

        init_is = BitVec("init_Is", 256)  # balance of sender, balance variable name is "init_"+addressName
        isb_node = BalanceNode("init_Is", init_is, sender_address)
        self.graph.cache_var_node(init_is, isb_node)

        init_ia = BitVec("init_Ia", 256)  # balance of receiver
        irb_node = BalanceNode("init_Ia", init_is, receiver_address)
        self.graph.cache_var_node(init_ia, irb_node)

        new_var_name = self.gen.gen_data_size()
        new_var = BitVec(new_var_name, 256)
        ds_node = InputDataSizeNode(new_var_name, new_var)
        self.graph.cache_var_node(new_var, ds_node)
        self.call_data_size = new_var  # size of input data

        # the bytecode of evm bytecode
        self.evm = self.runtime.evm

        new_var_name = self.gen.gen_gas_price_var()
        gas_price = BitVec(new_var_name, 256)
        gp_node = GasPriceNode(new_var_name, gas_price)
        self.graph.cache_var_node(gas_price, gp_node)

        new_var_name = self.gen.gen_origin_var()
        origin = BitVec(new_var_name, 256)
        os_node = OriginNode(new_var_name, origin)
        self.graph.cache_var_node(origin, os_node)

        new_var_name = self.gen.gen_coin_base()
        current_coinbase = BitVec(new_var_name, 256)
        cb_node = CoinbaseNode(new_var_name, current_coinbase)
        self.graph.cache_var_node(current_coinbase, cb_node)

        new_var_name = self.gen.gen_number()
        current_number = BitVec(new_var_name, 256)
        bn_node = BlockNumberNode(new_var_name, current_number)
        self.graph.cache_var_node(current_number, bn_node)

        new_var_name = self.gen.gen_difficult()
        current_difficulty = BitVec(new_var_name, 256)
        d_node = DifficultyNode(new_var_name, current_difficulty)
        self.graph.cache_var_node(current_difficulty, d_node)

        new_var_name = self.gen.gen_gas_limit()
        current_gas_limit = BitVec(new_var_name, 256)
        gl_node = GasLimitNode(new_var_name, current_gas_limit)
        self.graph.cache_var_node(current_gas_limit, gl_node)

        new_var_name = self.gen.gen_timestamp()
        current_timestamp = BitVec(new_var_name, 256)
        ts_node = TimeStampNode(new_var_name, current_timestamp)
        self.graph.cache_var_node(current_timestamp, ts_node)

        # set all the world state before symbolic execution of tx
        global_state["storage"] = {}  # the state of the current current contract
        global_state["miu"] = 0  # the size of memory in use, 1 == 32 bytes == 256 bits
        global_state["value"] = deposited_value
        global_state["senderAddress"] = sender_address
        global_state["receiverAddress"] = receiver_address
        global_state["gasPrice"] = gas_price
        global_state["origin"] = origin
        global_state["currentCoinbase"] = current_coinbase
        global_state["currentTimestamp"] = current_timestamp
        global_state["currentNumber"] = current_number
        global_state["currentDifficulty"] = current_difficulty
        global_state["currentGasLimit"] = current_gas_limit

        constraint0 = (deposited_value >= BitVecVal(0, 256))
        path_conditions_and_vars["path_condition"].append(constraint0)
        constraint1 = (init_is >= deposited_value)
        path_conditions_and_vars["path_condition"].append(constraint1)
        constraint2 = (init_ia >= BitVecVal(0, 256))
        path_conditions_and_vars["path_condition"].append(constraint2)

        path_conditions_and_vars["path_condition_node"].append(self.graph.add_constraint_node(And(constraint0,
                                                                                                  constraint1,
                                                                                                  constraint2),
                                                                                              pc=0,
                                                                                              name="init",
                                                                                              flag=True))

        # update the balances of the "caller" and "callee", global_state["balance"] is {}, indexed by address(real or
        # symbolic
        global_state["balance"][global_state["senderAddress"]] = simplify(init_is - deposited_value)
        global_state["balance"][global_state["receiverAddress"]] = simplify(init_ia + deposited_value)

    def is_testing_evm(self):
        return global_params.UNIT_TEST != 0

    def compare_storage_and_gas_unit_test(self, global_state, UNIT_TEST):
        unit_test = pickle.load(open(PICKLE_PATH, 'rb'))
        test_status = unit_test.compare_with_symExec_result(global_state, UNIT_TEST)
        exit(test_status)

    # for MSTORE8 and MSTORE, [start, start+size], size = [31|0]
    @staticmethod
    def write_memory(start, value, params, size=31):
        if is_expr(size):
            raise Exception("write memory size should not be symbolic")
        if not is_expr(start):
            end = start + 31
            memory = params.memory
            old_size = len(memory) // 32
            new_size = ceil32(end) // 32
            mem_extend = (new_size - old_size) * 32
            if new_size >= MAX_MEMORY_SIZE:
                raise Exception("write memory error for overflow")
            memory.extend([0] * mem_extend)

            for i in range(size, -1, -1):
                value = to_symbolic(value)
                memory[start + i] = convert_result(Extract(8 * (size - i) + 7, 8 * (size - i), value))
        else:
            params.mem[start] = value
        return

    # load a value of 32 bytes size from memory indexed by "start"(in byte)
    # the sort of return value should be in {real int, BitVec(256)}
    def load_memory(self, start, params):
        if not is_expr(start):
            data = []  # [mem_0, mem_1, ..., mem_31]
            if start + 31 >= len(params.memory):
                new_var_name = self.gen.gen_mem_var(params.global_state["pc"] - 1)
                new_var = BitVec(new_var_name, 256)
                node = MemoryNode(new_var, new_var, start)
                self.graph.cache_var_node(new_var, node)
                log.error("unexpected memory index: index %d larger than memory size %d",
                          start + 31, len(params.memory))

                return new_var
            else:
                for i in range(0, 32):
                    value = to_symbolic(params.memory[start+i], 8)
                    data.append(value)

                result = to_symbolic(data[0])
                for i in range(1, 32):  # stack = Concat(mem_0, mem_1, ..., mem_31)
                    result = Concat(result, to_symbolic(data[i]))
        else:
            result = None

            for key in params.mem:
                try:
                    if int(str(simplify(to_symbolic(key - start)))) == 0:
                        result = params.mem[key]
                except:
                    pass
            if result is None:
                log.debug("symbolic index not in mem, create a new memory variable")
                new_var_name = self.gen.gen_mem_var(params.global_state["pc"]-1)
                result = BitVec(new_var_name, 256)
                node = MemoryNode(new_var_name, result, start)
                self.graph.cache_var_node(result, node)

                params.mem[start] = result
            else:
                if is_expr(result):
                    if result.sort() == BitVecSort(8):
                        result = simplify(Concat(Extract(255, 8, BitVecVal(0, 256)), result))
        if is_expr(result):
            assert result.sort() == BitVecSort(256), "load memory is not BitVecSort(256)"

        return convert_result(result)


class Parameter:
    def __init__(self, **kwargs):
        attr_defaults = {
            # for all elem in stack, they should be either 'python int' or z3 type BitVecRef(256)
            # or other types of data
            "stack": [],
            # all variables located with real type of address and size is stored and loaded by memory, and with one
            # symbolic var in address or size, the value is stored and loaded in mem
            "memory": [],
            "mem": {},

            # used to show all calls of current path, every element is the real int representing pc of call instruction
            "calls": [],

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

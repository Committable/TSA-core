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
from utils import *
import interpreter.opcodes as opcodes
from graphBuilder.evmGraph import *
import networkx as nx

log = logging.getLogger(__name__)
Edge = namedtuple("Edge", ["v1", "v2"])

UNSIGNED_BOUND_NUMBER = 2**256 - 1
CONSTANT_ONES_159 = BitVecVal((1 << 160) - 1, 256)


class EVMInterpreter:
    def __init__(self, runtime):
        self.gen = Generator()
        self.solver = Solver()
        self.graph = XGraph()
        self.visited_edges = {}
        self.path_conditions = []
        self.runtime = runtime

    def sym_exec(self):
        path_conditions_and_vars = {"path_condition": [], "path_condition_node": []}
        global_state = self._get_init_global_state(path_conditions_and_vars)
        params = Parameter(path_conditions_and_vars=path_conditions_and_vars, global_state=global_state)
        return self._sym_exec_block(params, 0, 0, 0, -1)

    # Symbolically executing a block from the start address
    def _sym_exec_block(self, params, block, pre_block, depth, func_call):
        visited = params.visited
        stack = params.stack
        node_stack = params.node_stack
        mem = params.mem
        node_mem = params.node_mem
        memory = params.memory
        node_memory = params.node_memory
        global_state = params.global_state
        sha3_list = params.sha3_list
        path_conditions_and_vars = params.path_conditions_and_vars
        calls = params.calls

        if block < 0:
            log.debug("UNKNOWN JUMP ADDRESS. TERMINATING THIS PATH")
            return 1

        log.debug("Reach block address %d \n", block)

        current_edge = Edge(pre_block, block)

        if current_edge in self.visited_edges:
            updated_count_number = self.visited_edges[current_edge] + 1
            self.visited_edges.update({current_edge: updated_count_number})
        else:
            self.visited_edges.update({current_edge: 1})

        if self.visited_edges[current_edge] > interpreter.params.LOOP_LIMIT:
            log.debug("Overcome a number of loop limit. Terminating this path ...")
            return 0

        current_gas_used = params.gas
        if current_gas_used > interpreter.params.GAS_LIMIT:
            log.debug("Run out of gas. Terminating this path ... ")
            return 0

        # Execute every instruction, one at a time
        try:
            block_ins = self.runtime.vertices[block].get_instructions()
        except KeyError:
            log.debug("This path results in an exception, possibly an invalid jump address")
            return 1

        for instr in block_ins:
            self._sym_exec_ins(params, block, instr, func_call)
        # Mark that this basic block in the visited blocks
        visited.append(block)
        depth += 1

        # Go to next Basic Block(s)
        if self.runtime.jump_type[block] == "terminal" or depth > interpreter.params.DEPTH_LIMIT:
            global total_no_of_paths
            total_no_of_paths += 1

            log.debug("TERMINATING A PATH ...")

        elif self.runtime.jump_type[block] == "unconditional":  # executing "JUMP"
            successor = self.runtime.vertices[block].get_jump_target()
            new_params = params.copy()
            new_params.global_state["pc"] = successor
            self._sym_exec_block(new_params, successor, block, depth, func_call)
        elif self.runtime.jump_type[block] == "falls_to":  # just follow to the next basic block
            successor = self.runtime.vertices[block].get_falls_to()
            new_params = params.copy()
            new_params.global_state["pc"] = successor
            self._sym_exec_block(new_params, successor, block, depth, func_call)
        elif self.runtime.jump_type[block] == "conditional":  # executing "JUMPI"

            # A choice point, we proceed with depth first search

            branch_expression = self.runtime.vertices[block].get_branch_expression()
            branch_expression_node = self.runtime.vertices[block].get_branch_expression_node()
            negated_branch_expression_node = self.runtime.vertices[block].get_negated_branch_expression_node()

            # log.debug("Branch expression: " + str(branch_expression))
            # log.debug("Branch Node Expression" + branch_expression_node)

            self.solver.push()  # SET A BOUNDARY FOR SOLVER
            self.solver.add(branch_expression)

            try:
                if self.solver.check() == unsat:
                    log.debug("INFEASIBLE PATH DETECTED")
                else:
                    left_branch = self.runtime.vertices[block].get_jump_target()
                    new_params = params.copy()
                    new_params.global_state["pc"] = left_branch
                    new_params.path_conditions_and_vars["path_condition"].append(branch_expression)
                    new_params.path_conditions_and_vars["path_condition_node"].append(branch_expression_node)
                    # last_idx = len(new_params.path_conditions_and_vars["path_condition"]) - 1
                    self._sym_exec_block(new_params, left_branch, block, depth, func_call)
            except TimeoutError:
                raise
            except Exception as e:
                if interpreter.params.DEBUG_MODE:
                    traceback.print_exc()

            self.solver.pop()  # POP SOLVER CONTEXT

            self.solver.push()  # SET A BOUNDARY FOR SOLVER
            negated_branch_expression = Not(branch_expression)
            self.solver.add(negated_branch_expression)

            log.debug("Negated branch expression: " + str(negated_branch_expression))

            try:
                if self.solver.check() == unsat:
                    # Note that this check can be optimized. I.e. if the previous check succeeds,
                    # no need to check for the negated condition, but we can immediately go into
                    # the else branch
                    log.debug("INFEASIBLE PATH DETECTED")
                else:
                    right_branch = self.runtime.vertices[block].get_falls_to()
                    new_params = params.copy()
                    new_params.global_state["pc"] = right_branch
                    new_params.path_conditions_and_vars["path_condition"].append(negated_branch_expression)
                    new_params.path_conditions_and_vars["path_condition_node"].append(negated_branch_expression_node)
                    # last_idx = len(new_params.path_conditions_and_vars["path_condition"]) - 1
                    # new_params.analysis["time_dependency_bug"][last_idx] = global_state["pc"]
                    self._sym_exec_block(new_params, right_branch, block, depth, func_call)
            except TimeoutError:
                raise
            except Exception as e:
                if interpreter.params.DEBUG_MODE:
                    traceback.print_exc()
            self.solver.pop()  # POP SOLVER CONTEXT
            # updated_count_number = visited_edges[current_edge] - 1
            # visited_edges.update({current_edge: updated_count_number})
        else:
            updated_count_number = self.visited_edges[current_edge] - 1
            self.visited_edges.update({current_edge: updated_count_number})
            raise Exception('Unknown Jump-Type')

    def _sym_exec_ins(self, params, block, instr, func_call):

        stack = params.stack
        node_stack = params.node_stack
        mem = params.mem
        node_mem = params.node_mem
        memory = params.memory
        node_memory = params.node_memory
        global_state = params.global_state
        sha3_list = params.sha3_list
        path_conditions_and_vars = params.path_conditions_and_vars
        calls = params.calls

        instr_parts = str.split(instr, ' ')
        opcode = instr_parts[0]
        # instr_opcode = opcodes.opcode_by_name(opcode)
        # print(opcode)
        # if global_state["pc"] == 144:
        #     print(...)
        if opcode == "INVALID":
            return
        elif opcode == "ASSERTFAIL":
            return

        log.debug("==============================")
        log.debug("EXECUTING: " + instr)

        #
        #  0s: Stop and Arithmetic Operations
        #
        if opcode == "STOP":
            global_state["pc"] = global_state["pc"] + 1
            return
        elif opcode == "ADD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                # Type conversion is needed when they are mismatched
                if isReal(first) and isSymbolic(second):
                    first = BitVecVal(first, 256)
                    computed = first + second
                elif isSymbolic(first) and isReal(second):
                    second = BitVecVal(second, 256)
                    computed = first + second
                else:
                    # both are real and we need to manually modulus with 2 ** 256
                    # if both are symbolic z3 takes care of modulus automatically
                    computed = (first + second) % (2 ** 256)
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)

            else:
                raise ValueError('STACK underflow')
        elif opcode == "MUL":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isReal(first) and isSymbolic(second):
                    first = BitVecVal(first, 256)
                elif isSymbolic(first) and isReal(second):
                    second = BitVecVal(second, 256)
                computed = first * second & UNSIGNED_BOUND_NUMBER
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SUB":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isReal(first) and isSymbolic(second):
                    first = BitVecVal(first, 256)
                    computed = first - second
                elif isSymbolic(first) and isReal(second):
                    second = BitVecVal(second, 256)
                    computed = first - second
                else:
                    computed = (first - second) % (2 ** 256)
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "DIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    if second == 0:
                        computed = 0
                    else:
                        first = to_unsigned(first)
                        second = to_unsigned(second)
                        computed = first / second
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)
                    self.solver.push()
                    self.solver.add(Not(second == 0))
                    if check_sat(self.solver) == unsat:
                        computed = 0
                    else:
                        computed = UDiv(first, second)
                    self.solver.pop()
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SDIV":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    first = to_signed(first)
                    second = to_signed(second)
                    if second == 0:
                        computed = 0
                    elif first == -2 ** 255 and second == -1:
                        computed = -2 ** 255
                    else:
                        sign = -1 if (first / second) < 0 else 1
                        computed = sign * (abs(first) / abs(second))
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)
                    self.solver.push()
                    self.solver.add(Not(second == 0))
                    if check_sat(self.solver) == unsat:
                        computed = 0
                    else:
                        self.solver.push()
                        self.solver.add(Not(And(first == -2 ** 255, second == -1)))
                        if check_sat(self.solver) == unsat:
                            computed = -2 ** 255
                        else:
                            self.solver.push()
                            self.solver.add(first / second < 0)
                            sign = -1 if check_sat(self.solver) == sat else 1
                            z3_abs = lambda x: If(x >= 0, x, -x)
                            first = z3_abs(first)
                            second = z3_abs(second)
                            computed = sign * (first / second)
                            self.solver.pop()
                        self.solver.pop()
                    self.solver.pop()
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    if second == 0:
                        computed = 0
                    else:
                        first = to_unsigned(first)
                        second = to_unsigned(second)
                        computed = first % second & UNSIGNED_BOUND_NUMBER

                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)

                    self.solver.push()
                    self.solver.add(Not(second == 0))
                    if check_sat(self.solver) == unsat:
                        # it is provable that second is indeed equal to zero
                        computed = 0
                    else:
                        computed = URem(first, second)
                    self.solver.pop()

                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SMOD":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    if second == 0:
                        computed = 0
                    else:
                        first = to_signed(first)
                        second = to_signed(second)
                        sign = -1 if first < 0 else 1
                        computed = sign * (abs(first) % abs(second))
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)

                    self.solver.push()
                    self.solver.add(Not(second == 0))
                    if check_sat(self.solver) == unsat:
                        # it is provable that second is indeed equal to zero
                        computed = 0
                    else:
                        self.solver.push()
                        self.solver.add(first < 0)  # check sign of first element
                        sign = BitVecVal(-1, 256) if check_sat(self.solver) == sat \
                            else BitVecVal(1, 256)
                        self.solver.pop()
                        z3_abs = lambda x: If(x >= 0, x, -x)
                        first = z3_abs(first)
                        second = z3_abs(second)

                        computed = sign * (first % second)
                    self.solver.pop()

                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)

            else:
                raise ValueError('STACK underflow')
        elif opcode == "ADDMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)
                if isAllReal(first, second, third):
                    if third == 0:
                        computed = 0
                    else:
                        computed = (first + second) % third
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)
                    self.solver.push()
                    self.solver.add(Not(third == 0))
                    if check_sat(self.solver) == unsat:
                        computed = 0
                    else:
                        first = ZeroExt(256, first)
                        second = ZeroExt(256, second)
                        third = ZeroExt(256, third)
                        computed = (first + second) % third
                        computed = Extract(255, 0, computed)
                    self.solver.pop()
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "MULMOD":
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)
                if isAllReal(first, second, third):
                    if third == 0:
                        computed = 0
                    else:
                        computed = (first * second) % third
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)
                    self.solver.push()
                    self.solver.add(Not(third == 0))
                    if check_sat(self.solver) == unsat:
                        computed = 0
                    else:
                        first = ZeroExt(256, first)
                        second = ZeroExt(256, second)
                        third = ZeroExt(256, third)
                        computed = URem(first * second, third)
                        computed = Extract(255, 0, computed)
                    self.solver.pop()
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
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
                    new_var_name = self.gen.gen_arbitrary_var()
                    computed = BitVec(new_var_name, 256)
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SIGNEXTEND":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    if first >= 32 or first < 0:
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
                    self.solver.add(Not(Or(first >= 32, first < 0)))
                    if check_sat(self.solver) == unsat:
                        computed = second
                    else:
                        signbit_index_from_right = 8 * first + 7
                        self.solver.push()
                        self.solver.add(second & (1 << signbit_index_from_right) == 0)
                        if check_sat(self.solver) == unsat:
                            computed = second | (2 ** 256 - (1 << signbit_index_from_right))
                        else:
                            computed = second & ((1 << signbit_index_from_right) - 1)
                        self.solver.pop()
                    self.solver.pop()
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
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
                if isAllReal(first, second):
                    first = to_unsigned(first)
                    second = to_unsigned(second)
                    if first < second:
                        computed = 1
                    else:
                        computed = 0
                else:
                    computed = If(ULT(first, second), BitVecVal(1, 256), BitVecVal(0, 256))
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "GT":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    first = to_unsigned(first)
                    second = to_unsigned(second)
                    if first > second:
                        computed = 1
                    else:
                        computed = 0
                else:
                    computed = If(UGT(first, second), BitVecVal(1, 256), BitVecVal(0, 256))
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SLT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    first = to_signed(first)
                    second = to_signed(second)
                    if first < second:
                        computed = 1
                    else:
                        computed = 0
                else:
                    computed = If(first < second, BitVecVal(1, 256), BitVecVal(0, 256))
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "SGT":  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    first = to_signed(first)
                    second = to_signed(second)
                    if first > second:
                        computed = 1
                    else:
                        computed = 0
                else:
                    computed = If(first > second, BitVecVal(1, 256), BitVecVal(0, 256))
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "EQ":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if isAllReal(first, second):
                    if first == second:
                        computed = 1
                    else:
                        computed = 0
                else:
                    computed = If(first == second, BitVecVal(1, 256), BitVecVal(0, 256))
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "ISZERO":
            # Tricky: this instruction works on both boolean and integer,
            # when we have a symbolic expression, type error might occur
            # Currently handled by try and catch
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                if isReal(first):
                    if first == 0:
                        computed = 1
                    else:
                        computed = 0
                else:
                    computed = If(first == 0, BitVecVal(1, 256), BitVecVal(0, 256))
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "AND":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                computed = first & second
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "OR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                computed = first | second
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "XOR":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                computed = first ^ second
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "NOT":
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                computed = (~first) & UNSIGNED_BOUND_NUMBER
                computed = simplify(computed) if is_expr(computed) else computed
                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "BYTE":
            if len(stack) > 1:
                global_state["pc"] = global_state["pc"] + 1
                first = stack.pop(0)
                byte_index = 32 - first - 1
                second = stack.pop(0)
                if isAllReal(first, second):
                    if first >= 32 or first < 0:
                        computed = 0
                    else:
                        computed = second & (255 << (8 * byte_index))
                        computed = computed >> (8 * byte_index)
                else:
                    first = to_symbolic(first)
                    second = to_symbolic(second)
                    self.solver.push()
                    self.solver.add(Not(Or(first >= 32, first < 0)))
                    if check_sat(self.solver) == unsat:
                        computed = 0
                    else:
                        computed = second & (255 << (8 * byte_index))
                        computed = computed >> (8 * byte_index)
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
                    data = [str(x) for x in memory[s0: s0 + s1]]
                    position = ''.join(data)
                    position = re.sub('[\s+]', '', position)
                    position = zlib.compress(six.b(position), 9)
                    position = base64.b64encode(position)
                    position = position.decode('utf-8', 'strict')
                    if position in sha3_list:
                        stack.insert(0, sha3_list[position])
                        computed = sha3_list[position]
                    else:
                        new_var_name = self.gen.gen_arbitrary_var()
                        new_var = BitVec(new_var_name, 256)
                        sha3_list[position] = new_var
                        stack.insert(0, new_var)
                        computed = new_var
                else:
                    # push into the execution a fresh symbolic variable
                    new_var_name = self.gen.gen_arbitrary_var()
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var
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
                address = stack.pop(0)
                new_var_name = self.gen.gen_balance_var()
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var
                if isReal(address):
                    hashed_address = "concrete_address_" + str(address)
                else:
                    hashed_address = str(address)
                global_state["balance"][hashed_address] = new_var
                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLER":  # get caller address
            # that is directly responsible for this execution
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["sender_address"])
            # callerNode = MsgDataNode("sender_address", global_state["sender_address"], False)
            # node_stack.insert(0, callerNode)
        elif opcode == "ORIGIN":  # get execution origination address
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["origin"])
            # node_stack.insert(0, global_state["origin"])
        elif opcode == "CALLVALUE":  # get value of this transaction
            global_state["pc"] = global_state["pc"] + 1
            stack.insert(0, global_state["value"])
            # callvalueNode = MsgDataNode("CALLVALUE", global_state["value"], False)
            # node_stack.insert(0, callvalueNode)
        elif opcode == "CALLDATALOAD":  # from input data from environment
            if len(stack) > 0:
                global_state["pc"] = global_state["pc"] + 1
                position = stack.pop(0)
                # node_position = node_stack.pop(0)
                new_var_name = self.gen.gen_data_var(position)
                if new_var_name in path_conditions_and_vars:
                    new_var = path_conditions_and_vars[new_var_name]
                else:
                    new_var = BitVec(new_var_name, 256)
                    path_conditions_and_vars[new_var_name] = new_var
                stack.insert(0, new_var)
                update_graph_inputdata(self.graph, node_stack, new_var, new_var_name)
            else:
                raise ValueError('STACK underflow')
        elif opcode == "CALLDATASIZE":
            global_state["pc"] = global_state["pc"] + 1
            new_var_name = self.gen.gen_data_size()
            if new_var_name in path_conditions_and_vars:
                new_var = path_conditions_and_vars[new_var_name]
            else:
                new_var = BitVec(new_var_name, 256)
                path_conditions_and_vars[new_var_name] = new_var
            stack.insert(0, new_var)
            # node_stack.insert(0, 0)
        elif opcode == "CALLDATACOPY":  # Copy input data to memory
            #  TODO: Don't know how to simulate this yet
            if len(stack) > 2:
                global_state["pc"] = global_state["pc"] + 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)
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
                update_graph_mload(self.graph, address, current_miu_i, mem, node_stack, new_var, node_mem)
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
                update_graph_sload(self.graph, path_conditions_and_vars, node_stack, global_state, position, new_var_name, new_var)
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
                update_graph_sstore(self.graph, node_stack, stored_address, global_state, path_conditions_and_vars)
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
                update_jumpi(self.graph, node_stack, self.runtime.vertices[block], flag, branch_expression)
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
            update_graph_const(self.graph, node_stack, pushed_value)
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
                update_call(self.graph, node_stack, global_state, path_conditions_and_vars)
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
                update_callcode(self.graph, node_stack, global_state, path_conditions_and_vars)

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
                update_delegatecall(self.graph, node_stack, global_state, path_conditions_and_vars)

            else:
                raise ValueError('STACK underflow')
        elif opcode in ("RETURN", "REVERT"):
            # TODO: Need to handle miu_i
            if len(stack) > 1:
                stack.pop(0)
                stack.pop(0)
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

            update_suicide(self.graph, node_stack, global_state, path_conditions_and_vars)
            return
        else:
            log.debug("UNKNOWN INSTRUCTION: " + opcode)
            raise Exception('UNKNOWN INSTRUCTION: ' + opcode)
        if (opcode in two_operand_opcode) or (opcode in three_operand_opcode) or (opcode in one_operand_opcode):
            # print(opcode)
            update_graph_computed(self.graph, node_stack, opcode, computed, path_conditions_and_vars)
        elif opcode in pass_opcode:
            update_pass(node_stack, opcode)
        elif opcode in block_opcode:
            update_graph_block(self.graph, node_stack, block_related_value, global_state["currentNumber"], False)
        elif opcode in msg_opcode:
            update_graph_msg(self.graph, node_stack, opcode, global_state)
        # print("stack: ")
        # print(stack)
        # print("node_stack: ")
        # print(node_stack)
        # if len(stack) != len(node_stack):
        #     print("node_stack is wrong" + str(opcode) + str(global_state["pc"]))

    def _get_init_global_state(self,path_conditions_and_vars):
        global_state = {"balance": {}, "pc": 0}
        init_is = init_ia = deposited_value = sender_address = receiver_address = gas_price = origin = currentCoinbase = currentNumber = currentDifficulty = currentGasLimit = callData = None


        sender_address = BitVec("Is", 256)
        receiver_address = BitVec("Ia", 256)
        deposited_value = BitVec("Iv", 256)
        init_is = BitVec("init_Is", 256)
        init_ia = BitVec("init_Ia", 256)

        path_conditions_and_vars["Is"] = sender_address
        path_conditions_and_vars["Ia"] = receiver_address
        path_conditions_and_vars["Iv"] = deposited_value

        constraint = (deposited_value >= BitVecVal(0, 256))
        path_conditions_and_vars["path_condition"].append(constraint)
        constraint = (init_is >= deposited_value)
        path_conditions_and_vars["path_condition"].append(constraint)
        constraint = (init_ia >= BitVecVal(0, 256))
        path_conditions_and_vars["path_condition"].append(constraint)

        # update the balances of the "caller" and "callee"

        global_state["balance"]["Is"] = (init_is - deposited_value)
        global_state["balance"]["Ia"] = (init_ia + deposited_value)

        if not gas_price:
            new_var_name = self.gen.gen_gas_price_var()
            gas_price = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = gas_price

        if not origin:
            new_var_name = self.gen.gen_origin_var()
            origin = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = origin

        if not currentCoinbase:
            new_var_name = "IH_c"
            currentCoinbase = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = currentCoinbase

        if not currentNumber:
            new_var_name = "IH_i"
            currentNumber = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = currentNumber

        if not currentDifficulty:
            new_var_name = "IH_d"
            currentDifficulty = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = currentDifficulty

        if not currentGasLimit:
            new_var_name = "IH_l"
            currentGasLimit = BitVec(new_var_name, 256)
            path_conditions_and_vars[new_var_name] = currentGasLimit

        new_var_name = "IH_s"
        currentTimestamp = BitVec(new_var_name, 256)
        path_conditions_and_vars[new_var_name] = currentTimestamp

        # the state of the current current contract
        global_state["Ia"] = {}
        global_state["pos_to_node"] = {}
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

        return global_state

class Parameter:
    def __init__(self, **kwargs):
        attr_defaults = {
            "stack": [],
            "node_stack": [],
            "calls": [],
            "memory": [],
            "node_memory": [],
            "visited": [],
            "mem": {},
            "node_mem": {},
            "analysis": {},
            "sha3_list": {},
            "global_state": {},
            "state_to_node": {},
            "path_conditions_and_vars": {},
            "gas": 0,
            "func_block": None
        }
        for (attr, default) in six.iteritems(attr_defaults):
            setattr(self, attr, kwargs.get(attr, default))

    def copy(self):
        _kwargs = custom_deepcopy(self.__dict__)
        return Parameter(**_kwargs)
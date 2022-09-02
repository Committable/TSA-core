import copy
import re
import time
import traceback

import six
import z3

import errors
import global_params
from graph_builder import x_graph
from interpreter import evm_params
from interpreter import opcodes
from interpreter import symbolic_var_generator
import log
import utils


class EVMInterpreter:

    def __init__(self, runtime, cname, context):
        self.cname = cname
        self.context = context
        self.runtime = runtime

        self.gen = symbolic_var_generator.Generator()

        # XGraph for the contract, a function -> a XGraph,
        # if no function detected, the all contract -> a XGraph
        self.x_graph = x_graph.XGraph(cname, self.runtime.source_map)

        # global coverage info for the contract
        # number of paths, terminated by normal or exception
        self.total_no_of_paths = {
            'normal': 0,
            'exception': 0,
            'loopLimit': 0,
            'gasLimit': 0
        }
        self.paths = [
        ]  # all paths, e.g. [[block1, block2, ...], [block1, block3, ...]]
        # impossible paths
        self.impossible_paths = []
        # total visited pc and its times
        self.total_visited_pc = {}
        # total visited edges and its times
        self.total_visited_edges = {}
        # function visited edges and its times,
        # None for not in function,
        # else in a function
        self.function_visited_edges = None

        # TODO(Yang): should add evm bytecode Node in XGraph?
        # the evm runtime bytecode of the contract.
        self.evm_bytecode = utils.turn_hex_str_to_decimal_arr(
            self.runtime.binary)  # contract's bytecode in bytes
        # function name on current visiting, null str for not in a function
        self.current_function = ''
        # the path we're visiting
        self.current_path = []
        # TODO(Yang): solvers for solver z3 constraints,
        #  but it's not used now for efficiency
        self.single_solver = z3.Solver()
        self.global_solver = z3.Solver()
        self.single_solver.set('timeout', evm_params.Z3_TIMEOUT)
        self.global_solver.set('timeout', evm_params.Z3_TIMEOUT)

    def get_function_from_start_block(self, block):
        if block in self.runtime.start_block_to_func_sig:
            func_sig = self.runtime.start_block_to_func_sig[block]
            if self.runtime.source_map.sig_to_func is not None:
                current_func_name = None
                for key in self.runtime.source_map.sig_to_func:
                    # TODO(Chao): Remove eval?
                    if eval('0x' + key) == eval('0x' + func_sig):
                        current_func_name = self.runtime.source_map.sig_to_func[
                            key]
                        break
                if current_func_name is not None:
                    pattern = r'(\w[\w\d_]*)\((.*)\)$'
                    match = re.match(pattern, current_func_name)
                    if match:
                        current_func_name = list(match.groups())[0]
                else:
                    current_func_name = func_sig
            else:
                current_func_name = func_sig
            return current_func_name
        else:
            return None

    def sym_exec(self):
        path_conditions_and_vars = {
            'path_condition': [],
            'path_condition_node': [],
            'branch_flag': []
        }
        global_state = {'balance': {}, 'pc': 0}
        self._init_global_state(path_conditions_and_vars, global_state)
        params = Parameter(path_conditions_and_vars=path_conditions_and_vars,
                           global_state=global_state)
        try:
            self._sym_exec_block(params, 0, 0)
        except TimeoutError:
            log.mylogger.error('system timeout for %s', self.cname)
            self.context.set_timeout()
            self.context.set_err()
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            self.context.set_err()
            log.mylogger.error(
                'cause error when symbolic execute for %s, err: %s', self.cname,
                str(err))

    def _enter_block(self, function_name, block):
        self.current_path.append(block)

        if function_name is not None:
            log.mylogger.debug('enter function %s', function_name)
            self.x_graph.add_func_graph(function_name)
            self.x_graph.current_function = function_name
            self.function_visited_edges = {}

    def _exit_block(self, function_name):
        self.current_path.pop()

        if function_name is not None:
            log.mylogger.debug('exit function %s', function_name)
            self.x_graph.current_function = '@global'
            self.current_function = '@global'
            self.function_visited_edges = None

    def _terminate_path(self, kind, function_name, params, start_time, block):
        del params  # Unused, reserve for name hint
        self.total_no_of_paths[kind] += 1
        self.gen.gen_path_id()
        if global_params.DEBUG_MOD:
            self.paths.append(copy.deepcopy(self.current_path))

        self._exit_block(function_name)

        end_time = time.time()
        execution_time = end_time - start_time
        log.mylogger.debug('block: %s symbolic execution time: %.6f s',
                           str(block), execution_time)
        log.mylogger.debug('*********************************')

    # Symbolically executing a block from the start address
    def _sym_exec_block(self, params, block, pre_block):
        start_time = time.time()

        log.mylogger.debug('*********************************')
        log.mylogger.debug('reach block address %d', block)

        # find if we're into a function
        function_name = self.get_function_from_start_block(block)
        self._enter_block(function_name, block)

        visited = params.visited
        current_edge = (pre_block, block)

        # check unexpected block address
        if block < 0 or block not in self.runtime.vertices:
            log.mylogger.error(
                'unknown block address %d. Terminating this path ...', block)
            self._terminate_path('exception', function_name, params, start_time,
                                 block)
            return

        # TODO(Yang): how to implement better loop detection?
        #  It's a pay-off between time consuming and coverage
        if (current_edge in visited and
                visited[current_edge] > evm_params.LOOP_LIMIT and
                self.runtime.jump_type[block] == 'conditional'):
            log.mylogger.debug(
                'overcome a number of loop limit. Terminating this path ...')
            self._terminate_path('loopLimit', function_name, params, start_time,
                                 block)
            return
        else:
            if self.function_visited_edges is None:  # not in a function
                if current_edge in self.total_visited_edges and \
                        self.total_visited_edges[
                            current_edge] > 10:
                    log.mylogger.debug('overcome a number of loop limit. '
                                       'Terminating this path ...')
                    self._terminate_path('loopLimit', function_name, params,
                                         start_time, block)
                    return
            else:  # in a function
                if current_edge in self.function_visited_edges and \
                        self.function_visited_edges[
                            current_edge] > 10:
                    log.mylogger.debug('overcome a number of loop limit. '
                                       'Terminating this path ...')
                    self._terminate_path('loopLimit', function_name, params,
                                         start_time, block)
                    return

        # TODO(Yang): gas_used cannot be calculated accurately because of miu,
        #  now we keep the less used gas by instructions and less memory used,
        #  and there should be someone to learn about gas calculation of evm
        #  exactly
        if params.gas > evm_params.GAS_LIMIT:
            log.mylogger.debug('run out of gas. Terminating this path ... ')
            self._terminate_path('gasLimit', function_name, params, start_time,
                                 block)
            return

        # Execute every instruction, one at a time
        # TODO(Yang): Exception is caught, it may be a bug, but it should not
        #  influence other path
        block_ins = self.runtime.vertices[block].get_instructions()
        try:
            for instr in block_ins:
                self._sym_exec_ins(params, block, instr)
        except errors.JumpTargetError as err:
            log.mylogger.error(
                'jump Target Error: %s, Terminating this path ...', str(err))
            self._terminate_path('exception', function_name, params, start_time,
                                 block)
            return
        except TimeoutError as err:
            # global timeout means the analysis should be ended
            # globally, so we raise up
            log.mylogger.error('global timeout: %s, Terminating this path ...',
                               str(err))
            self._terminate_path('exception', function_name, params, start_time,
                                 block)
            raise err

        # update visited edges for current path
        if current_edge in visited:
            updated_count_number = visited[current_edge] + 1
            visited.update({current_edge: updated_count_number})
        else:
            visited.update({current_edge: 1})
        # update visited edges for global symbolic execution
        if current_edge in self.total_visited_edges:
            updated_count_number = self.total_visited_edges[current_edge] + 1
            self.total_visited_edges.update(
                {current_edge: updated_count_number})
        else:
            self.total_visited_edges.update({current_edge: 1})
        # update functions visited edges for function's symbolic execution
        if self.function_visited_edges is not None:
            if current_edge in self.function_visited_edges:
                updated_count_number = self.function_visited_edges[
                    current_edge] + 1
                self.function_visited_edges.update(
                    {current_edge: updated_count_number})
            else:
                self.function_visited_edges.update({current_edge: 1})

        # go to next basic block or terminate according to jump type
        if self.runtime.jump_type[block] == 'terminal':
            log.mylogger.debug('normally terminating this path ...')
            self._terminate_path('normal', function_name, params, start_time,
                                 block)
            return

        elif self.runtime.jump_type[
                block] == 'unconditional':  # executing 'JUMP'
            # TODO(Yang): how to deal with symbolic jump targets,
            #  now we only deal with unconditional jump with only
            #  one real target
            successor = self.runtime.vertices[block].get_jump_target()
            # This is an unexpected condition, which means no jump
            # target for 'JUMP'
            if successor is None:
                log.mylogger.error('successor of unconditional jump is None')
                self._terminate_path('exception', function_name, params,
                                     start_time, block)
                return
            else:
                params.global_state['pc'] = successor
                self._sym_exec_block(params, successor, block)

        elif self.runtime.jump_type[
                block] == 'falls_to':  # just follow to the next basic block
            successor = self.runtime.vertices[block].get_falls_to()
            #  it's an unexpected condition, which means falls to target is none
            if successor is None:
                log.mylogger.error('Successor of falls to is None')
                self._terminate_path('exception', function_name, params,
                                     start_time, block)
                return
            else:
                params.global_state['pc'] = successor
                self._sym_exec_block(params, successor, block)

        elif self.runtime.jump_type[block] == 'conditional':
            # A choice point, we proceed with depth first search
            branch_expression = self.runtime.vertices[
                block].get_branch_expression()

            # if branch expression is none, it must be condition like
            # symbolic target address
            if branch_expression is not None:
                # TODO(Yang): we don't check all conditions of the path or
                #  even the branch constraint for time consuming, instead
                #  we get string format of branch condition for simple
                #  judgement of impossible path
                str_expr = str(branch_expression)

                left_branch = self.runtime.vertices[block].get_jump_target()
                # find if left_branch is the start block of a new function
                selector = self.get_function_from_start_block(left_branch)

                if str_expr != 'False':
                    # we copy params for one branch of conditional jump
                    new_params = params.copy()
                    new_params.global_state['pc'] = left_branch
                    new_params.path_conditions_and_vars[
                        'path_condition'].append(branch_expression)
                    new_params.path_conditions_and_vars['branch_flag'].append(
                        True)

                    if selector is not None:
                        self.x_graph.add_constraint_node(
                            new_params.path_conditions_and_vars,
                            self.runtime.vertices[block].end,
                            self.gen.get_path_id(),
                            f'{selector}()',
                        )
                    else:
                        self.x_graph.add_constraint_node(
                            new_params.path_conditions_and_vars,
                            self.runtime.vertices[block].end,
                            self.gen.get_path_id(),
                        )
                    self._sym_exec_block(new_params, left_branch, block)
                else:
                    self.impossible_paths.append(
                        copy.deepcopy(self.current_path).append(left_branch))

                negated_branch_expression = z3.Not(branch_expression)
                right_branch = self.runtime.vertices[block].get_falls_to()

                if str_expr != 'True':
                    params.global_state['pc'] = right_branch
                    params.path_conditions_and_vars['path_condition'].append(
                        negated_branch_expression)
                    params.path_conditions_and_vars['branch_flag'].append(False)

                    self.x_graph.add_constraint_node(
                        params.path_conditions_and_vars,
                        self.runtime.vertices[block].end,
                        self.gen.get_path_id(),
                    )
                    self._sym_exec_block(params, right_branch, block)
                else:
                    self.impossible_paths.append(
                        copy.deepcopy(self.current_path).append(left_branch))
            else:
                log.mylogger.error(
                    'branch expression of conditional jump is None')
                self._terminate_path('exception', function_name, params,
                                     start_time, block)
                return
        else:
            raise NotImplementedError('unknown Jump-Type')

        end_time = time.time()
        execution_time = end_time - start_time
        log.mylogger.debug('block: %s symbolic execution time: %.6f s',
                           str(block), execution_time)
        log.mylogger.debug('*********************************')

        self._exit_block(function_name)
        return

    # TODO(Yang): 1.slot precision; 2.memory model; 3.sha3;
    #  4.system contracts call; 5.evm instructions expansion;

    #  memory model: model versioned memory as mem{(start, end):value}
    #  and memory[byte], and every write of memory will result in a new
    #  version of memory, but now we only treat memory when there address
    #  can be exactly the same by transforming to string when they are
    #  symbolic, and real address only locate memory[]

    #  slot precision: slot precision should be treated by checker

    #  sha3: if sha3 a0, a1 => memory{(a0, a0+a1): (concat(a,b,c)} , we
    #  maintain a dict sha3_list{concat(a, b, c): sha3_sym)}, and every
    #  time 'sha3' instruction is executed, if str(key) is exactly the same,
    #  we get the same sha3_sym, otherwise, we will construct a new
    #  (key2, sha3_sym2); and every time a constraint include both sha3_sym1,
    #  sha3_sym2, the sha3_sym2 is substituted by sha2_sym1, with constrain
    #  key1 == key2, because we only cares about the equality of two sha3_sym

    #  scc:
    #  instructions:
    def _sym_exec_ins(self, params, block, instr):
        start_time = time.time()
        # we detect global timeout for symbolic execution for every instruction
        if (start_time - self.context.start) >= global_params.SYM_TIMEOUT:
            raise TimeoutError('global timeout')

        stack = params.stack
        # mem = params.mem
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

        log.mylogger.debug('==============================')
        log.mylogger.debug('Start executing: %s', instr)
        # log.mylogger.debug('Memory: ' + str(used_mem))
        # log.mylogger.debug('Stack: %s', str(stack))
        #
        #  0s: Stop and Arithmetic Operations
        #
        if opcode == 'STOP':
            return
        elif opcode == 'INVALID':
            return
        elif opcode == 'ADD':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first + second) & evm_params.UNSIGNED_BOUND_NUMBER

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'MUL':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first * second) & evm_params.UNSIGNED_BOUND_NUMBER

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SUB':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (first - second) & evm_params.UNSIGNED_BOUND_NUMBER

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'DIV':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                if z3.is_expr(second):
                    path_conditions_and_vars['path_condition'].append(
                        second != 0)
                    path_conditions_and_vars['branch_flag'].append(True)
                    self.x_graph.add_constraint_node(
                        path_conditions_and_vars, global_state['pc'] - 1,
                        self.gen.get_path_id(), f'DIV_{global_state["pc"] - 1}')
                else:
                    if second == 0:
                        raise ValueError('divided by zero')
                computed = z3.UDiv(utils.to_symbolic(first), second)

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SDIV':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                if z3.is_expr(second):
                    path_conditions_and_vars['path_condition'].append(
                        second != 0)
                    path_conditions_and_vars['branch_flag'].append(True)
                    self.x_graph.add_constraint_node(
                        path_conditions_and_vars, global_state['pc'] - 1,
                        self.gen.get_path_id(),
                        f'SDIV_{global_state["pc"] - 1}')
                else:
                    if second == 0:
                        raise ValueError('divided by zero')

                computed = (first / second) & evm_params.UNSIGNED_BOUND_NUMBER

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'MOD':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                if z3.is_expr(second):
                    path_conditions_and_vars['path_condition'].append(
                        second != 0)
                    path_conditions_and_vars['branch_flag'].append(True)
                    self.x_graph.add_constraint_node(
                        path_conditions_and_vars, global_state['pc'] - 1,
                        self.gen.get_path_id(), f'MOD_{global_state["pc"] - 1}')
                else:
                    if second == 0:
                        raise ValueError('modified by zero')

                computed = z3.URem(first, utils.to_symbolic(second))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SMOD':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                if z3.is_expr(second):
                    path_conditions_and_vars['path_condition'].append(
                        second != 0)
                    path_conditions_and_vars['branch_flag'].append(True)
                    self.x_graph.add_constraint_node(
                        path_conditions_and_vars, global_state['pc'] - 1,
                        self.gen.get_path_id(),
                        f'SMOD_{global_state["pc"] - 1}')
                else:
                    if second == 0:
                        raise ValueError('modified by zero')

                sign = z3.If(first < 0, -1, 1)
                first = z3.If(first >= 0, first, -first)
                second = z3.If(second >= 0, second, -second)
                computed = sign * (first % second)

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'ADDMOD':
            if len(stack) > 2:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                if z3.is_expr(third):
                    path_conditions_and_vars['path_condition'].append(
                        third != 0)
                    path_conditions_and_vars['branch_flag'].append(True)
                    self.x_graph.add_constraint_node(
                        path_conditions_and_vars, global_state['pc'] - 1,
                        self.gen.get_path_id(),
                        f'ADDMOD_{global_state["pc"] - 1}')
                else:
                    if third == 0:
                        raise ValueError('modified by zero')

                computed = z3.URem(first + second, utils.to_symbolic(third))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'MULMOD':
            if len(stack) > 2:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                third = stack.pop(0)

                if z3.is_expr(third):
                    path_conditions_and_vars['path_condition'].append(
                        third != 0)
                    path_conditions_and_vars['branch_flag'].append(True)
                    self.x_graph.add_constraint_node(
                        path_conditions_and_vars, global_state['pc'] - 1,
                        self.gen.get_path_id(),
                        f'MULMOD_{global_state["pc"] - 1}')
                else:
                    if third == 0:
                        raise ValueError('modified by zero')

                computed = z3.URem(first * second, utils.to_symbolic(third))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'EXP':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                base = stack.pop(0)
                exponent = stack.pop(0)
                # Type conversion is needed when they are mismatched
                if utils.is_all_real(base, exponent):
                    computed = pow(base, exponent, 2**256)
                else:
                    # The computed value is unknown, this is because power is
                    # not supported in bit-vector theory
                    new_var_name = self.gen.gen_exp_var(base, exponent)
                    computed = z3.BitVec(new_var_name, 256)
                    # add to graph
                    node = x_graph.ExpNode(new_var_name, computed, base,
                                           exponent)
                    self.x_graph.cache_var_node(computed, node)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SIGNEXTEND':
            if len(stack) > 1:
                # todo: review this process
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)
                if utils.is_all_real(first, second):
                    if first >= 32:
                        computed = second
                    else:
                        signbit_index_from_right = 8 * first + 7
                        if second & (1 << signbit_index_from_right):
                            computed = second | (
                                2**256 - (1 << signbit_index_from_right))
                        else:
                            computed = second & (
                                (1 << signbit_index_from_right) - 1)
                else:
                    signbit_index_from_right = 8 * first + 7
                    computed = second & ((1 << signbit_index_from_right) - 1)

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        #
        #  10s: Comparison and Bitwise Logic Operations
        #
        elif opcode == 'LT':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = z3.If(z3.ULT(first, utils.to_symbolic(second)),
                                 z3.BitVecVal(1, 256), z3.BitVecVal(0, 256))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'GT':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = z3.If(z3.UGT(first, utils.to_symbolic(second)),
                                 z3.BitVecVal(1, 256), z3.BitVecVal(0, 256))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SLT':  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = z3.If(first < second, z3.BitVecVal(1, 256),
                                 z3.BitVecVal(0, 256))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SGT':  # Not fully faithful to signed comparison
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = z3.If(first > second, z3.BitVecVal(1, 256),
                                 z3.BitVecVal(0, 256))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'EQ':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = z3.If(first == second, z3.BitVecVal(1, 256),
                                 z3.BitVecVal(0, 256))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'ISZERO':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)

                computed = z3.If(first == 0, z3.BitVecVal(1, 256),
                                 z3.BitVecVal(0, 256))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'AND':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first & second

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'OR':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first | second

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'XOR':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = first ^ second

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'NOT':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)

                # TODO(Yang): should there be like: (~first) &
                #  UNSIGNED_BOUND_NUMBER
                computed = (~first)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'BYTE':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                byte_index = 31 - first
                second = stack.pop(0)

                computed = z3.LShR(utils.to_symbolic(second), (8 * byte_index))

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        #
        # 20s: SHA3
        # todo: review this process
        elif opcode in ('SHA3', 'KECCAK256'):
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                s0 = stack.pop(0)
                s1 = stack.pop(0)
                if utils.is_all_real(s0, s1) and s0 + s1 <= len(memory):
                    data = list(memory[s0:s0 + s1])
                    value = utils.to_symbolic(data[0], 8)
                    for x in data[1:]:
                        value = z3.Concat(value, utils.to_symbolic(x, 8))

                    new_var_name = self.gen.gen_sha3_var(
                        str(global_state['pc'] - 1))
                    computed = z3.BitVec(new_var_name, 256)
                    node = x_graph.ShaNode(new_var_name, computed,
                                           global_state['pc'] - 1, value)
                    self.x_graph.cache_var_node(computed, node)
                else:
                    # TODO(Yang): push into the stack a fresh symbolic variable,
                    #  how to deal with symbolic address and size
                    new_var_name = self.gen.gen_sha3_var(
                        str(global_state['pc'] - 1))
                    new_var = z3.BitVec(new_var_name, 256)
                    computed = new_var
                    # add to node
                    node = x_graph.ShaNode(new_var_name, computed,
                                           global_state['pc'] - 1)
                    self.x_graph.cache_var_node(computed, node)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        #
        # 30s: Environment Information
        #
        elif opcode == 'ADDRESS':  # get address of currently executing account
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['receiverAddress'])
        elif opcode == 'BALANCE':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                address = stack.pop(0)
                # get balance of address
                new_var = None

                # TODO(Yang): we do not consider balance that
                #  dealed twice in a path
                for x in global_state['balance']:
                    try:
                        if int(str(z3.simplify(
                                utils.to_symbolic(x - address)))) == 0:
                            new_var = global_state['balance'][x]
                            break
                    except:  # pylint: disable=bare-except
                        pass

                if new_var is None:
                    new_var_name = self.gen.gen_balance_of(address)
                    new_var = z3.BitVec(new_var_name, 256)
                    global_state['balance'][address] = new_var
                    b_node = x_graph.BalanceNode(new_var_name, new_var, address)
                    self.x_graph.cache_var_node(new_var, b_node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'CALLER':  # get caller address
            # that is directly responsible for this execution
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['senderAddress'])
        elif opcode == 'ORIGIN':  # get execution origination address
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['origin'])
        elif opcode == 'CALLVALUE':  # get value of this transaction
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['value'])
        elif opcode == 'CALLDATALOAD':  # from input data from environment
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                start = stack.pop(0)

                new_var_name = self.gen.gen_data_var(
                    start, utils.to_symbolic(start + 31), self.current_function)
                value = z3.BitVec(new_var_name, 256)
                node = x_graph.InputDataNode(new_var_name, value, start,
                                             utils.convert_result(start + 31))
                self.x_graph.cache_var_node(value, node)

                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'CALLDATASIZE':
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['callDataSize'])
        elif opcode == 'CALLDATACOPY':  # Copy input data to memory
            if len(stack) > 2:
                global_state['pc'] = global_state['pc'] + 1
                memory_start = stack.pop(0)
                input_start = stack.pop(0)
                size = stack.pop(0)
                # Unused, reserve for name hint
                del memory_start, input_start, size
                # Todo: implement this instruction
                params.memory = {}
                log.mylogger.debug('unhandled instruction CALLDATACOPY')
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'CODESIZE':
            # length of the executing contract's code in bytes
            code_size = len(self.evm_bytecode)
            stack.insert(0, code_size)
        elif opcode == 'CODECOPY':
            # copy executing contract's bytecode
            if len(stack) > 2:
                global_state['pc'] = global_state['pc'] + 1
                mem_start = stack.pop(0)
                code_start = stack.pop(0)
                size = stack.pop(0)  # in bytes
                # Unused, reserve for name hint
                del mem_start, code_start, size
                # Todo: implement this instruction
                params.memory = {}
                log.mylogger.debug('unhandled instruction CODECOPY')
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'RETURNDATACOPY':
            if len(stack) > 2:
                global_state['pc'] += 1
                mem_start = stack.pop(0)
                return_start = stack.pop(0)
                size = stack.pop(0)  # in bytes
                # Unused, reserve for name hint
                del mem_start, return_start, size
                # Todo: implement this instruction
                params.memory = {}
                log.mylogger.debug('unhandled instruction RETURNDATACOPY')
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'RETURNDATASIZE':
            global_state['pc'] += 1
            new_var_name = self.gen.gen_return_data_size(calls[-1])
            new_var = z3.BitVec(new_var_name, 256)
            node = x_graph.ReturnDataSizeNode(new_var_name, new_var)
            self.x_graph.cache_var_node(new_var, node)

            stack.insert(0, new_var)
        elif opcode == 'GASPRICE':
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['gas_price'])
        elif opcode == 'EXTCODESIZE':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                address = stack.pop(0)

                new_var_name = self.gen.gen_code_size_var(address)
                new_var = z3.BitVec(new_var_name, 256)
                node = x_graph.ExtcodeSizeNode(new_var_name, new_var, address)
                self.x_graph.cache_var_node(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'EXTCODECOPY':
            if len(stack) > 3:
                global_state['pc'] = global_state['pc'] + 1
                address = stack.pop(0)
                mem_location = stack.pop(0)
                code_from = stack.pop(0)
                no_bytes = stack.pop(0)
                # Unused, reserve for name hint
                del address, mem_location, code_from, no_bytes
                # TODO: implement this instruction
                params.memory = {}
                log.mylogger.debug('unhandled instruction EXTCODECOPY')
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'EXTCODEHASH':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                address = stack.pop(0)

                new_var_name = self.gen.gen_code_size_var(address)
                new_var = z3.BitVec(new_var_name, 256)
                node = x_graph.ExtcodeHashNode(new_var_name, new_var, address)
                self.x_graph.cache_var_node(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        #
        #  40s: Block Information
        #
        elif opcode == 'BLOCKHASH':  # information from block header
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                block_number = stack.pop(0)

                new_var_name = self.gen.gen_blockhash(block_number)
                value = z3.BitVec(new_var_name, 256)
                node = x_graph.BlockhashNode(new_var_name, value, block_number)

                self.x_graph.cache_var_node(value, node)

                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'COINBASE':  # information from block header
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['currentCoinbase'])
        elif opcode == 'TIMESTAMP':  # information from block header
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['currentTimestamp'])
        elif opcode == 'NUMBER':  # information from block header
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['currentNumber'])
        elif opcode == 'DIFFICULTY':  # information from block header
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['currentDifficulty'])
        elif opcode == 'GASLIMIT':  # information from block header
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['currentGasLimit'])
        elif opcode == 'CHAINID':  # information from block header
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['chainId'])
        elif opcode == 'SELFBALANCE':
            global_state['pc'] = global_state['pc'] + 1
            # get balance of address
            new_var = None
            address = global_state['receiverAddress']
            for x in global_state['balance']:
                try:
                    if int(str(z3.simplify(utils.to_symbolic(x -
                                                             address)))) == 0:
                        new_var = global_state['balance'][x]
                        break
                except:  # pylint: disable=bare-except
                    pass

            if new_var is None:
                new_var_name = self.gen.gen_balance_of(address)
                new_var = z3.BitVec(new_var_name, 256)
                global_state['balance'][address] = new_var
                b_node = x_graph.BalanceNode(new_var_name, new_var, address)
                self.x_graph.cache_var_node(new_var, b_node)

            stack.insert(0, new_var)
        elif opcode == 'BASEFEE':
            global_state['pc'] = global_state['pc'] + 1
            stack.insert(0, global_state['baseFee'])
        #
        #  50s: Stack, Memory, Storage, and Flow Information
        #
        elif opcode == 'POP':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                stack.pop(0)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'MLOAD':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                address = stack.pop(0)

                value = self.load_memory(address, params, 32)

                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'MSTORE':
            # bigger end of stack value is stored in lower address of memory
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                self.write_memory(stored_address, stored_value, params, 32)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'MSTORE8':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                self.write_memory(stored_address, stored_value, params, 1)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SLOAD':
            if len(stack) > 0:
                global_state['pc'] = global_state['pc'] + 1
                position = stack.pop(0)

                value = None
                for key in global_state['storage']:
                    if utils.convert_result_to_int(key - position) == 0:
                        value = global_state['storage'][key]
                        break

                if value is None:
                    new_var_name = self.gen.gen_storage_var(position)
                    value = z3.BitVec(new_var_name, 256)
                    node = x_graph.StateNode(new_var_name, value, position,
                                             global_state['pc'] - 1)
                    self.x_graph.add_var_node(value, node)

                    global_state['storage'][position] = value
                stack.insert(0, value)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SSTORE':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                stored_address = stack.pop(0)
                stored_value = stack.pop(0)

                global_state['storage'][stored_address] = stored_value
                # add to graph
                self.x_graph.add_sstore_node(opcode, global_state['pc'] - 1,
                                             [stored_address, stored_value],
                                             self.gen.get_path_id(),
                                             path_conditions_and_vars)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'JUMP':
            if len(stack) > 0:
                target_address = utils.convert_result(stack.pop(0))

                if z3.is_expr(target_address):
                    log.mylogger.error(
                        'Target address of JUMP must be an integer: '
                        'but it is %s', str(target_address))
                    raise errors.JumpTargetError(
                        'Target address for jump is symbolic')
                else:
                    if target_address not in self.runtime.vertices:
                        raise errors.JumpTargetError(
                            f'Target address {target_address} '
                            f'for jump is not in vertices')
                    self.runtime.vertices[block].set_jump_targets(
                        target_address)
                    if target_address not in self.runtime.edges[block]:
                        self.runtime.edges[block].append(target_address)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'JUMPI':
            # We need to prepare two branches
            if len(stack) > 1:
                target_address = utils.convert_result(stack.pop(0))
                if z3.is_expr(target_address):
                    log.mylogger.error(
                        'Target address of JUMPI must be an integer: '
                        'but it is %s', str(target_address))
                    raise errors.JumpTargetError(
                        'Target address for jumpi is symbolic')
                else:
                    if target_address not in self.runtime.vertices:
                        raise errors.JumpTargetError(
                            f'Target address {target_address} '
                            f'for jumpi is not in vertices')
                    self.runtime.vertices[block].set_jump_targets(
                        target_address)
                    if target_address not in self.runtime.edges[block]:
                        self.runtime.edges[block].append(target_address)

                    flag = stack.pop(0)
                    if not z3.is_expr(flag):  # must be int
                        if flag == 0:
                            branch_expression = z3.BoolVal(False)
                        else:
                            branch_expression = z3.BoolVal(True)
                    else:
                        branch_expression = utils.to_symbolic(flag != 0)

                    self.runtime.vertices[block].set_branch_expression(
                        z3.simplify(branch_expression))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'PC':
            stack.insert(0, global_state['pc'])
            global_state['pc'] = global_state['pc'] + 1
        elif opcode == 'MSIZE':
            global_state['pc'] = global_state['pc'] + 1
            msize = 32 * global_state['miu_i']
            stack.insert(0, msize)
        elif opcode == 'GAS':
            # Todo: we do not have this precisely. It depends on both the
            #  initial gas and the amount has been depleted
            #  we need to think about this in the future, in case precise gas
            #  can be tracked
            global_state['pc'] = global_state['pc'] + 1
            new_var_name = self.gen.gen_gas_var(global_state['pc'] - 1)
            new_var = z3.BitVec(new_var_name, 256)
            node = x_graph.GasNode(new_var_name, new_var)
            self.x_graph.cache_var_node(new_var, node)

            stack.insert(0, new_var)
        elif opcode == 'JUMPDEST':
            global_state['pc'] = global_state['pc'] + 1
        #
        #  60s & 70s: Push Operations
        #
        elif opcode.startswith('PUSH', 0):  # this is a push instruction
            position = int(opcode[4:], 10)
            global_state['pc'] = global_state['pc'] + 1 + position
            pushed_value = int(instr_parts[2], 16)
            stack.insert(0, pushed_value)
            # add to graph
            node = x_graph.ConstNode(str(pushed_value), pushed_value)
            self.x_graph.cache_var_node(pushed_value, node)
        #
        #  80s: Duplication Operations
        #
        elif opcode.startswith('DUP', 0):
            global_state['pc'] = global_state['pc'] + 1
            position = int(opcode[3:], 10) - 1
            if len(stack) > position:
                duplicate = stack[position]
                stack.insert(0, duplicate)
            else:
                raise ValueError('STACK underflow')
        #
        #  90s: Swap Operations
        #
        elif opcode.startswith('SWAP', 0):
            global_state['pc'] = global_state['pc'] + 1
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
        elif opcode in ('LOG0', 'LOG1', 'LOG2', 'LOG3', 'LOG4'):
            global_state['pc'] = global_state['pc'] + 1
            # We do not simulate these log operations
            num_of_pops = 2 + int(opcode[3:])
            while num_of_pops > 0:
                stack.pop(0)
                num_of_pops -= 1
        #
        #  f0s: System Operations
        #
        elif opcode == 'CREATE':  # Todo: the different of create and create2
            if len(stack) > 2:
                global_state['pc'] += 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)

                new_var_name = self.gen.gen_contract_address(
                    global_state['pc'] - 1)
                new_var = z3.BitVec(new_var_name, 256)
                node = x_graph.AddressNode(new_var_name, new_var)
                self.x_graph.cache_var_node(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'CALL':
            if len(stack) > 6:
                calls.append(global_state['pc'])
                global_state['pc'] = global_state['pc'] + 1

                out_gas = stack.pop(0)
                recipient = stack.pop(0)
                transfer_amount = stack.pop(0)
                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_output = stack.pop(0)

                # update balance of call's sender that's this contract's address
                balance_ia = global_state['balance'][
                    global_state['receiverAddress']]
                new_balance_ia = utils.convert_result(balance_ia -
                                                      transfer_amount)
                global_state['balance'][
                    global_state['receiverAddress']] = new_balance_ia
                # update the balance of recipient
                old_balance = None
                for key in global_state['balance']:
                    if utils.convert_result_to_int(key - recipient) == 0:
                        old_balance = global_state['balance'].pop(key)
                        break

                if old_balance is None:
                    new_balance_name = self.gen.gen_balance_of(recipient)
                    old_balance = z3.BitVec(new_balance_name, 256)
                global_state['balance'][recipient] = utils.convert_result(
                    old_balance + transfer_amount)

                # add enough_fund condition to path_conditions
                is_enough_fund = z3.And((transfer_amount <= balance_ia),
                                        old_balance >= 0)
                params.path_conditions_and_vars['path_condition'].append(
                    is_enough_fund)
                params.path_conditions_and_vars['branch_flag'].append(True)
                self.x_graph.add_constraint_node(
                    params.path_conditions_and_vars, global_state['pc'] - 1,
                    self.gen.get_path_id(),
                    f'fund_call_{global_state["pc"] - 1}')
                # get return status
                new_var_name = self.gen.gen_return_status(calls[-1])
                new_var = z3.BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                return_node = x_graph.ReturnStatusNode(new_var_name,
                                                       new_var_name, calls[-1])

                # add call instruction to graph
                self.x_graph.add_message_call_node(
                    opcode, global_state['pc'] - 1, [
                        out_gas, recipient, transfer_amount, start_data_input,
                        size_data_input, start_data_output, size_data_output
                    ], return_node, self.gen.get_path_id(),
                    path_conditions_and_vars)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'CALLCODE':
            if len(stack) > 6:
                calls.append(global_state['pc'])
                global_state['pc'] = global_state['pc'] + 1

                out_gas = stack.pop(0)
                recipient = stack.pop(0)
                transfer_amount = stack.pop(0)
                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_output = stack.pop(0)

                # update balance of call's sender that's this contract's address
                balance_ia = global_state['balance'][
                    global_state['receiverAddress']]
                new_balance_ia = utils.convert_result(balance_ia -
                                                      transfer_amount)
                global_state['balance'][
                    global_state['receiverAddress']] = new_balance_ia
                # update the balance of recipient
                old_balance = None
                for key in global_state['balance']:
                    if utils.convert_result_to_int(key - recipient):
                        old_balance = global_state['balance'].pop(key)
                        break

                if old_balance is None:
                    new_balance_name = self.gen.gen_balance_of(recipient)
                    old_balance = z3.BitVec(new_balance_name, 256)
                global_state['balance'][recipient] = utils.convert_result(
                    old_balance + transfer_amount)

                # add enough_fund condition to path_conditions
                is_enough_fund = z3.And((transfer_amount <= balance_ia),
                                        old_balance >= 0)
                params.path_conditions_and_vars['path_condition'].append(
                    is_enough_fund)
                params.path_conditions_and_vars['branch_flag'].append(True)
                self.x_graph.add_constraint_node(
                    params.path_conditions_and_vars, global_state['pc'] - 1,
                    self.gen.get_path_id(),
                    f'fund_callcode_{global_state["pc"] - 1}')

                # get return status
                new_var_name = self.gen.gen_return_status(calls[-1])
                new_var = z3.BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                return_node = x_graph.ReturnStatusNode(new_var_name,
                                                       new_var_name, calls[-1])

                # add call instruction to graph
                self.x_graph.add_message_call_node(
                    opcode, global_state['pc'] - 1, [
                        out_gas, recipient, transfer_amount, start_data_input,
                        size_data_input, start_data_output, size_data_output
                    ], return_node, self.gen.get_path_id(),
                    path_conditions_and_vars)
            else:
                raise ValueError('STACK underflow')
        elif opcode in ('DELEGATECALL', 'STATICCALL'):
            if len(stack) > 5:
                calls.append(global_state['pc'])
                global_state['pc'] = global_state['pc'] + 1
                out_gas = stack.pop(0)
                recipient = stack.pop(0)

                start_data_input = stack.pop(0)
                size_data_input = stack.pop(0)
                start_data_output = stack.pop(0)
                size_data_output = stack.pop(0)

                # the execution is possibly okay
                new_var_name = self.gen.gen_return_status(calls[-1])
                new_var = z3.BitVec(new_var_name, 256)
                stack.insert(0, new_var)
                return_node = x_graph.ReturnStatusNode(new_var_name, new_var,
                                                       calls[-1])

                # add call instruction to graph
                self.x_graph.add_message_call_node(
                    opcode, global_state['pc'] - 1, [
                        out_gas, recipient, start_data_input, size_data_input,
                        start_data_output, size_data_output
                    ], return_node, self.gen.get_path_id(),
                    path_conditions_and_vars)
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'CREATE2':
            if len(stack) > 3:
                global_state['pc'] += 1
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)
                stack.pop(0)

                new_var_name = self.gen.gen_contract_address(
                    global_state['pc'] - 1)
                new_var = z3.BitVec(new_var_name, 256)
                node = x_graph.AddressNode(new_var_name, new_var)
                self.x_graph.cache_var_node(new_var, node)

                stack.insert(0, new_var)
            else:
                raise ValueError('STACK underflow')
        elif opcode in ('RETURN', 'REVERT'):
            if len(stack) > 1:
                # TODO(Yang): deal with offset and length, and
                #  add return value to graph
                offset = stack.pop(0)
                length = stack.pop(0)
                # Unused, reserve for name hint
                del offset, length
                if opcode == 'REVERT':
                    node = x_graph.TerminalNode(opcode, global_state['pc'])
                    self.x_graph.add_terminal_node(node,
                                                   path_conditions_and_vars,
                                                   self.gen.get_path_id())
            else:
                raise ValueError('STACK underflow')
        elif opcode in ('SELFDESTRUCT', 'SUICIDE'):
            # TODO(Yang): add selfdestruct and suicide instruction to graph
            global_state['pc'] = global_state['pc'] + 1
            recipient = stack.pop(0)
            # get transfer_amount and update the new balance
            transfer_amount = None
            for key in global_state['balance']:
                if utils.convert_result_to_int(
                        key - global_state['receiverAddress']) == 0:
                    transfer_amount = global_state['balance'][key]
                    global_state['balance'][key] = 0
                    break

            assert transfer_amount is not None, 'transfer amount is None'
            # get the balance of recipient and update recipient's balance
            balance_recipient = None
            for key in global_state['balance']:
                if utils.convert_result_to_int(key == recipient) == 0:
                    balance_recipient = global_state['balance'].pop(key)
                    break
            if balance_recipient is None:
                new_address_value_name = self.gen.gen_balance_of(recipient)
                balance_recipient = z3.BitVec(new_address_value_name, 256)

            new_balance = balance_recipient + transfer_amount
            global_state['balance'][recipient] = new_balance

            return
        elif opcode == 'SAR':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (second >> first)

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SHR':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = z3.LShR(second, first)

                stack.insert(0, utils.convert_result(computed))
            else:
                raise ValueError('STACK underflow')
        elif opcode == 'SHL':
            if len(stack) > 1:
                global_state['pc'] = global_state['pc'] + 1
                first = stack.pop(0)
                second = stack.pop(0)

                computed = (second << first)

                stack.insert(0, computed)
            else:
                raise ValueError('STACK underflow')
        else:
            raise NotImplementedError('UNKNOWN INSTRUCTION: ' + opcode)
        a_len = len(stack)
        if (a_len - b_len) != (opcodes.opcode_by_name(opcode).push -
                               opcodes.opcode_by_name(opcode).pop):
            raise AssertionError('Stack push and pop un-match')
        end_time = time.time()
        execution_time = end_time - start_time
        log.mylogger.debug('End executing: %s symbolic execution time: %.6f s',
                           instr, execution_time)
        log.mylogger.debug('==============================')

    def _init_global_state(self, path_conditions_and_vars, global_state):
        new_var = z3.BitVec('Is', 256)
        sender_address = new_var & evm_params.CONSTANT_ONES_159
        s_node = x_graph.SenderNode('Is', new_var)
        self.x_graph.cache_var_node(new_var, s_node)

        new_var = z3.BitVec('Ia', 256)
        receiver_address = new_var & evm_params.CONSTANT_ONES_159
        r_node = x_graph.ReceiverNode('Ia', new_var)
        self.x_graph.cache_var_node(new_var, r_node)

        deposited_value = z3.BitVec('Iv', 256)  # value of transaction
        dv_node = x_graph.DepositValueNode('Iv', deposited_value)
        self.x_graph.cache_var_node(deposited_value, dv_node)

        init_is = z3.BitVec(
            'init_Is', 256
        )  # balance of sender, balance variable name is 'init_'+addressName
        isb_node = x_graph.BalanceNode('init_Is', init_is, sender_address)
        self.x_graph.cache_var_node(init_is, isb_node)

        init_ia = z3.BitVec('init_Ia', 256)  # balance of receiver
        irb_node = x_graph.BalanceNode('init_Ia', init_is, receiver_address)
        self.x_graph.cache_var_node(init_ia, irb_node)

        call_data_size_name = self.gen.gen_data_size()
        call_data_size = z3.BitVec(call_data_size_name, 256)
        ds_node = x_graph.InputDataSizeNode(call_data_size_name, call_data_size)
        self.x_graph.cache_var_node(call_data_size, ds_node)

        new_var_name = self.gen.gen_gas_price_var()
        gas_price = z3.BitVec(new_var_name, 256)
        gp_node = x_graph.GasPriceNode(new_var_name, gas_price)
        self.x_graph.cache_var_node(gas_price, gp_node)

        new_var_name = self.gen.gen_origin_var()
        origin = z3.BitVec(new_var_name, 256)
        os_node = x_graph.OriginNode(new_var_name, origin)
        self.x_graph.cache_var_node(origin, os_node)

        new_var_name = self.gen.gen_coin_base()
        current_coinbase = z3.BitVec(new_var_name, 256)
        cb_node = x_graph.CoinbaseNode(new_var_name, current_coinbase)
        self.x_graph.cache_var_node(current_coinbase, cb_node)

        new_var_name = self.gen.gen_number()
        current_number = z3.BitVec(new_var_name, 256)
        bn_node = x_graph.BlockNumberNode(new_var_name, current_number)
        self.x_graph.cache_var_node(current_number, bn_node)

        new_var_name = self.gen.gen_difficult()
        current_difficulty = z3.BitVec(new_var_name, 256)
        d_node = x_graph.DifficultyNode(new_var_name, current_difficulty)
        self.x_graph.cache_var_node(current_difficulty, d_node)

        new_var_name = self.gen.gen_gas_limit()
        current_gas_limit = z3.BitVec(new_var_name, 256)
        gl_node = x_graph.GasLimitNode(new_var_name, current_gas_limit)
        self.x_graph.cache_var_node(current_gas_limit, gl_node)

        new_var_name = self.gen.gen_chain_id()
        current_chain_id = z3.BitVec(new_var_name, 256)
        ci_node = x_graph.ChainIdNode(new_var_name, current_chain_id)
        self.x_graph.cache_var_node(current_chain_id, ci_node)

        new_var_name = self.gen.gen_base_fee()
        current_base_fee = z3.BitVec(new_var_name, 256)
        bf_node = x_graph.BaseFeeNode(new_var_name, current_base_fee)
        self.x_graph.cache_var_node(current_base_fee, bf_node)

        new_var_name = self.gen.gen_timestamp()
        current_timestamp = z3.BitVec(new_var_name, 256)
        ts_node = x_graph.TimeStampNode(new_var_name, current_timestamp)
        self.x_graph.cache_var_node(current_timestamp, ts_node)

        # set all the world state before symbolic execution of tx
        global_state['storage'] = {}  # the state of the current contract
        global_state[
            'miu'] = 0  # the size of memory in use, 1 == 32 bytes == 256 bits
        global_state['value'] = deposited_value
        global_state['senderAddress'] = sender_address
        global_state['receiverAddress'] = receiver_address
        global_state['gasPrice'] = gas_price
        global_state['origin'] = origin
        global_state['currentCoinbase'] = current_coinbase
        global_state['currentTimestamp'] = current_timestamp
        global_state['currentNumber'] = current_number
        global_state['currentDifficulty'] = current_difficulty
        global_state['currentGasLimit'] = current_gas_limit
        global_state['chainId'] = current_chain_id
        global_state['baseFee'] = current_base_fee
        global_state['callDataSize'] = call_data_size

        constraint0 = (deposited_value >= z3.BitVecVal(0, 256))
        constraint1 = (init_is >= deposited_value)
        constraint2 = (init_ia >= z3.BitVecVal(0, 256))
        path_conditions_and_vars['path_condition'].append(
            z3.And(constraint0, constraint1, constraint2))
        path_conditions_and_vars['branch_flag'].append(True)
        self.x_graph.add_constraint_node(path_conditions_and_vars, 0, -1,
                                         'init')

        # update the balances of the 'caller' and 'callee',
        # global_state['balance'] is {}, indexed by address
        # (real or symbolic)
        global_state['balance'][global_state['senderAddress']] = (
            init_is - deposited_value)
        global_state['balance'][global_state['receiverAddress']] = (
            init_ia + deposited_value)

    # [start, start+size-1], e.g. [0, 31]
    # memory for real indexes, map key is start, map value is (end, value)
    # mem for symbolic indexes, map key is start, map value is (end, value)
    @staticmethod
    def write_memory(start, value, params, size=32):
        if utils.is_all_real(start, size):
            # [start, end] is filled with new value
            end = start + size - 1
            memory = params.memory
            old_keys = list(memory.keys())
            for old_start in old_keys:
                old_end = memory[old_start][0]
                old_value = memory[old_start][1]
                old_size = old_end - old_start + 1

                if end < old_start:
                    continue
                elif start <= old_start <= end:
                    if end >= old_end:
                        memory.pop(old_start)
                    else:  # old_end > end
                        memory[end +
                               1] = (old_end,
                                     utils.convert_result(
                                         z3.Extract(
                                             8 * (old_end - old_start + 1) - 1,
                                             8 * (end + 1 - old_start),
                                             utils.to_symbolic(old_value,
                                                               bits=old_size *
                                                               8))))
                        memory.pop(old_start)
                elif old_start < start:
                    if old_end < start:
                        continue
                    elif end >= old_end >= start:
                        memory[old_start] = (start - 1,
                                             utils.convert_result(
                                                 z3.Extract(
                                                     8 * (start - old_start) -
                                                     1, 0,
                                                     utils.to_symbolic(
                                                         old_value,
                                                         bits=old_size * 8))))
                    else:  # old_end > end
                        memory[old_start] = (start - 1,
                                             utils.convert_result(
                                                 z3.Extract(
                                                     8 * (start - old_start) -
                                                     1, 0,
                                                     utils.to_symbolic(
                                                         old_value,
                                                         bits=old_size * 8))))
                        memory[end +
                               1] = (old_end,
                                     utils.convert_result(
                                         z3.Extract(
                                             8 * (old_end - old_start + 1) - 1,
                                             8 * (end + 1 - old_start),
                                             utils.to_symbolic(old_value,
                                                               bits=old_size *
                                                               8))))
            memory[start] = (end, value)
        else:
            params.mem = {start: (start + size - 1, value)}

    # load a value of 32 bytes size from memory indexed by 'start'(in byte)
    # the sort of return value should be in {real int, BitVec(256)}
    # we assume that real index should load value from memory and symbol
    # index should load memory from mem
    # TODO(Yang): debug this function at runtime and implement the unit test,
    #  and simplify for z3 expression of contract and extra
    def load_memory(self, start, params,
                    size):  # size = start - end + 1, e.g. 32
        if utils.is_all_real(start):
            memory = params.memory
            if start in memory:  # memory := (start, (end, value))
                end = memory[start][0]
                value = memory[start][1]
                if end - start == size - 1:
                    result = value
                elif end - start > size - 1:
                    result = z3.Extract(
                        8 * size - 1, 0,
                        utils.to_symbolic(value, bits=8 * (end - start + 1)))
                else:
                    result = z3.Concat(
                        utils.to_symbolic(self.load_memory(
                            end + 1, params, size - (end - start + 1)),
                                          bits=(size - (end - start + 1)) * 8),
                        utils.to_symbolic(value, bits=8 * (end - start + 1)))
            else:
                for x in memory:
                    end = memory[x][0]
                    value = memory[x][1]
                    if x < start <= end:
                        if end - start == size - 1:
                            result = z3.Extract(
                                8 * (end - x + 1) - 1, 8 * (start - x),
                                utils.to_symbolic(value,
                                                  bits=8 * (end - x + 1)))
                        elif end - start > size - 1:
                            result = z3.Extract(
                                8 * (start + size - x) - 1, 8 * (start - x),
                                utils.to_symbolic(value,
                                                  bits=8 * (end - x + 1)))
                        else:
                            result = z3.Concat(
                                utils.to_symbolic(
                                    self.load_memory(end + 1, params,
                                                     size - (end - start + 1)),
                                    bits=(size - (end - start + 1)) * 8),
                                z3.Extract(
                                    8 * (end - x + 1) - 1, 8 * (start - x),
                                    utils.to_symbolic(value,
                                                      bits=8 * (end - x + 1))))
                        if z3.is_expr(result):
                            assert result.sort() == z3.BitVecSort(
                                8 * size), 'load memory is not BitVecSort(256)'

                        return utils.convert_result(result)
                result = z3.BitVecVal(0, 8 * size)
        else:
            mem = params.mem
            for x in mem:
                if (utils.convert_result_to_int(start - x) == 0 and
                        utils.convert_result_to_int(mem[x][0] - start)
                        == size - 1):
                    return mem[x][1]
            else:
                log.mylogger.debug(
                    'symbolic index not in mem, create a new memory variable')
                new_var_name = self.gen.gen_mem_var(params.global_state['pc'] -
                                                    1)
                result = z3.BitVec(new_var_name, 256)
                node = x_graph.MemoryNode(new_var_name, result, start)
                self.x_graph.cache_var_node(result, node)

        if z3.is_expr(result):
            assert result.sort() == z3.BitVecSort(
                8 * size), 'load memory is not BitVecSort(256)'

        return utils.convert_result(result)


class Parameter:

    def __init__(self, **kwargs):
        attr_defaults = {
            # for all elem in stack, they should be either 'python int' or
            # z3 type BitVecRef(256) or other types of data
            'stack': [],
            # all variables located with real type of address and size is
            # stored and loaded by memory, and with one symbolic var in address
            # or size, the value is stored and loaded in mem
            'memory': {},
            'mem': {},

            # used to show all calls of current path, every element is the
            # real int representing pc of call instruction
            'calls': [],

            # mark all the visited edges of current_path, for detecting loops
            # and control the loop_depth under limits
            # {Edge:num}
            'visited': {},

            # path conditions and vars form constrains of this path
            'path_conditions_and_vars': {},

            # all the state of blockchain for this path
            'global_state': {},

            # gas should be always kept real type
            'gas': 0,
        }
        for (attr, default) in six.iteritems(attr_defaults):
            setattr(self, attr, kwargs.get(attr, default))

    def copy(self):
        kwargs = utils.custom_deepcopy(self.__dict__)
        return Parameter(**kwargs)

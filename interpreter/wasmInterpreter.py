# from collections import namedtuple
#
# import six
# import math
# from z3 import Solver
#
# import interpreter.params
# import log
# import num
# from disassembler import wasmConvention
# from disassembler.wasmConvention import EDGE_UNCONDITIONAL, EDGE_TERMINAL, EDGE_FALLTHROUGH, EDGE_CONDITIONAL_IF
# from disassembler.wasmModule import Instruction
# from interpreter.symbolicVarGenerator import Generator
# from runtime.wasmRuntime import ModuleInstance, Stack, WasmFunc, HostFunc, Value, Frame, Label, FunctionInstance, \
#     GlobalInstance
# from solver.symbolicVar import *
# from utils import custom_deepcopy, isSymbolic, check_sat, isDecisiable, isAllReal
#
# Edge = namedtuple("Edge", ["v1", "v2"])
#
# class WASMInterpreter:
#     def __init__(self, runtime):
#         self.gen = Generator()
#         self.solver = Solver()
#         self.visited_edges = {}
#         self.path_conditions = []
#         self.runtime = runtime
#
#
#     def exec(self, func_name):
#         for export in self.runtime.module.exports:
#             if export.kind == wasmConvention.extern_func and export.name == func_name:
#                 func_addr = export.desc
#                 func = self.runtime.store.funcs[self.runtime.module_instance.funcaddrs[func_addr]]
#                 # Mapping check for Python valtype to WebAssembly valtype
#                 params = []
#                 for i, e in enumerate(func.functype.args):
#                     params = Value(e, produce_symbolic_var(self.gen.gen_input_var(i),e))
#                 log.debugln(f'Running function {func_name}({", ".join([str(e) for e in params])}):')
#                 stack = Stack()
#                 stack.ext(params)
#                 tables = []
#                 for i in self.runtime.store.tables:
#                     tables.append(i.copy())
#                 mems = []
#                 for i in self.runtime.store.mems:
#                     mems.append(i.copy())
#                 globals = []
#                 for i in self.runtime.store.globals:
#                     globals.append(i.copy())
#                 context = Context(stack=stack, tables=tables, mems = mems, globals = globals)
#                 r = self.call(self.runtime.module_instance, func_addr, self.runtime.store, context)
#                 if r:
#                     return r[0].n
#                 return None
#         log.panicln(f'No function Named {func_name}')
#
#     def call(self,
#             module: ModuleInstance,
#             address: int,
#             store: Store,
#             ctx: Context,
#     ):
#         f = store.funcs[address]
#         assert len(f.functype.rets) <= 1
#         for i, t in enumerate(f.functype.args[::-1]):
#             ia = t
#             ib = ctx.stack.data[-1 - i]
#             if ia != ib.valtype:
#                 raise Exception('Signature mismatch in call')
#         if isinstance(f, WasmFunc):
#             return self._wasmfunc_call(module, address, store, ctx)
#         if isinstance(f, HostFunc):
#             return self._hostfunc_call(module, address, store, ctx)
#         raise KeyError
#
#     def _wasmfunc_call(
#             self,
#             module: ModuleInstance,
#             address: int,
#             store: Store,
#             ctx: Context,
#     ):
#         f: WasmFunc = store.funcs[address]
#         code = f.code.expr.data
#         valn = [ctx.stack.pop() for _ in f.functype.args][::-1]
#         val0 = []
#         for e in f.code.locals:
#             if e == wasmConvention.i32:
#                 val0.append(Value.from_i32(0))
#             elif e == wasmConvention.i64:
#                 val0.append(Value.from_i64(0))
#             elif e == wasmConvention.f32:
#                 val0.append(Value.from_f32(0))
#             else:
#                 val0.append(Value.from_f64(0))
#         frame = Frame(module, valn + val0, len(f.functype.rets), len(code))
#         ctx.stack.add(frame)
#         # ctx.stack.add(Label(len(f.functype.rets), len(code)))
#         ctx.global_state['pc'] = 0
#         # An expression is evaluated relative to a current frame pointing to its containing module instance.
#         r = self._sym_exec_block(ctx, 0, 0, 0, f, frame)
#         # Exit
#         if not isinstance(ctx.stack.pop(), Frame):
#             raise Exception('signature mismatch in call')
#         return r
#
#     def _sym_exec_block(self, ctx, block, pre_block, depth, func, frame):
#         visited = ctx.visited
#         stack = ctx.stack
#         mems = ctx.mems
#         globals = ctx.globals
#         path_conditions_and_vars = ctx.path_conditions_and_vars
#
#         if block < 0:
#             log.debugln("UNKNOWN JUMP ADDRESS. TERMINATING THIS PATH")
#             return ["ERROR"]
#
#         log.debugln(f"Reach block address {block} \n")
#
#         current_edge = Edge(pre_block, block)
#
#         if current_edge in visited:
#             updated_count_number = visited[current_edge] + 1
#             visited.update({current_edge: updated_count_number})
#         else:
#             visited.update({current_edge: 1})
#
#         if visited[current_edge] > interpreter.params.LOOP_LIMIT:
#             log.debugln("Overcome a number of loop limit. Terminating this path ...")
#             return stack
#
#         current_gas_used = ctx.gas
#         if current_gas_used > interpreter.params.GAS_LIMIT:
#             log.debugln("Run out of gas. Terminating this path ... ")
#             return stack
#
#         # Execute every instruction, one at a time
#         try:
#             block_ins = func.blocks[block].get_instructions()
#         except KeyError:
#             log.debugln("This path results in an exception, possibly an invalid jump address")
#             return ["ERROR"]
#
#         for instr in block_ins:
#             self._sym_exec_ins(ctx, block, instr, func, frame)
#
#         depth += 1
#
#         # Go to next Basic Block(s)
#         if func.blocks[block].type == EDGE_UNCONDITIONAL:  # executing "JUMP"
#             successor = func.blocks[block].get_jump_target()
#             new_ctx = ctx.copy()
#             new_ctx.global_state["pc"] = successor
#             self._sym_exec_block(new_ctx, successor, block, depth, func, frame)
#
#         elif func.blocks[block].type == EDGE_TERMINAL or depth > interpreter.params.DEPTH_LIMIT:
#             log.debugln("TERMINATING A PATH ...")
#
#         elif func.blocks[block].type == EDGE_FALLTHROUGH:  # just follow to the next basic block
#             successor = func.blocks[block].get_falls_to()
#             new_ctx = ctx.copy()
#             new_ctx.global_state["pc"] = successor
#             self._sym_exec_block(new_ctx, successor, block, depth, func, frame)
#
#         elif func.blocks[block].type == EDGE_CONDITIONAL_IF:  # executing "JUMPI"
#
#             # A choice point, we proceed with depth first search
#
#             branch_expression = func.blocks[block].get_branch_expression()
#
#             log.debugln("Branch expression: " + str(branch_expression))
#
#             # self.solver.push()  # SET A BOUNDARY FOR SOLVER
#             # self.solver.add(branch_expression)
#
#             # try:
#                 # if self.solver.check() == unsat:
#                 #     log.debug("INFEASIBLE PATH DETECTED")
#                 # else:
#             left_branch = func.blocks[block].get_jump_target()
#             new_ctx = ctx.copy()
#             new_ctx.global_state["pc"] = left_branch
#             new_ctx.path_conditions_and_vars["path_condition"].append(branch_expression)
#             self._sym_exec_block(new_ctx, left_branch, block, depth, func, frame)
#             # except TimeoutError:
#             #     raise
#             # except Exception as e:
#             #     if interpreter.params.DEBUG_MODE:
#             #         traceback.print_exc()
#
#             # self.solver.pop()  # POP SOLVER CONTEXT
#             #
#             # self.solver.push()  # SET A BOUNDARY FOR SOLVER
#             negated_branch_expression = Not(branch_expression)
#             # self.solver.add(negated_branch_expression)
#
#             log.debug("Negated branch expression: " + str(negated_branch_expression))
#
#             # try:
#             #     if self.solver.check() == unsat:
#             #         # Note that this check can be optimized. I.e. if the previous check succeeds,
#             #         # no need to check for the negated condition, but we can immediately go into
#             #         # the else branch
#             #         log.debug("INFEASIBLE PATH DETECTED")
#             #     else:
#             right_branch = func.blocks[block].get_falls_to()
#             new_ctx = ctx.copy()
#             new_ctx.global_state["pc"] = right_branch
#             new_ctx.path_conditions_and_vars["path_condition"].append(negated_branch_expression)
#             self._sym_exec_block(new_ctx, right_branch, block, depth, func, frame)
#             # except TimeoutError:
#             #     raise
#             # except Exception as e:
#             #     if interpreter.params.DEBUG_MODE:
#             #         traceback.print_exc()
#             # self.solver.pop()  # POP SOLVER CONTEXT
#             # updated_count_number = visited_edges[current_edge] - 1
#             # visited_edges.update({current_edge: updated_count_number})
#         else:
#             updated_count_number = self.visited_edges[current_edge] - 1
#             self.visited_edges.update({current_edge: updated_count_number})
#             raise Exception('Unknown Jump-Type')
#
#     def _sym_exec_ins(
#             self,
#             ctx: Context,
#             block: int,
#             instr: Instruction,
#             func: WasmFunc,
#             frame: Frame
#     ):
#         # An expression is evaluated relative to a current frame pointing to its containing module instance.
#         # 1. Jump to the start of the instruction sequence instr∗ of the expression.
#         # 2. Execute the instruction sequence.
#         # 3. Assert: due to validation, the top of the stack contains a value.
#         # 4. Pop the value val from the stack.
#         module = frame.module
#         if not instr:
#             raise Exception('empty init expr')
#
#         ctx.global_state['pc'] += 1
#
#         log.debugln(f'{str(instr):<18} {ctx.stack}')
#
#         if log.lvl >= 2:
#             ls = [f'{instr}: {wasmConvention.valtype[l.valtype][0]} {l.n}' for i, l in enumerate(frame.locals)]
#             gs = [f'{instr}: {"mut " if g.mut else ""}{wasmConvention.valtype[g.value.valtype][0]} {g.value.n}' for i,g in enumerate(ctx.globals)]
#             for n, e in (('locals', ls), ('globals', gs)):
#                 log.verboseln(f'{" " * 18} {str(n) + ":":<8} [{", ".join(e)}]')
#
#         opcode = instr.code
#         if opcode >= wasmConvention.unreachable and opcode <= wasmConvention.call_indirect:
#             if opcode == wasmConvention.unreachable:
#                 raise Exception('reached unreachable')
#             if opcode == wasmConvention.nop:
#                 return
#             if opcode == wasmConvention.block:
#                 return
#             if opcode == wasmConvention.loop:
#                 return
#             if opcode == wasmConvention.if_:
#                 c = ctx.stack.pop().n
#                 func.blocks[block].set_branch_expression(c)
#                 return
#             if opcode == wasmConvention.else_:
#                 return
#             if opcode == wasmConvention.end:
#                 return
#             if opcode == wasmConvention.br:
#                 return
#             if opcode == wasmConvention.br_if:
#                 c = ctx.stack.pop().n
#                 func.blocks[block].set_branch_expression(c)
#                 return
#             if opcode == wasmConvention.br_table:
#                 c = ctx.stack.pop().n
#                 func.blocks[block].set_branch_expression(c)
#                 return
#             if opcode == wasmConvention.return_:
#                 v = [ctx.stack.pop() for _ in range(frame.arity)][::-1]
#                 while True:
#                     e = ctx.stack.pop()
#                     if isinstance(e, Frame):
#                         ctx.stack.add(e)
#                         break
#                 ctx.stack.ext(v)
#                 return
#             if opcode == wasmConvention.call:
#                 r = self.call(module, module.funcaddrs[instr.immediate_arguments], self.runtime.store, ctx)
#                 ctx.stack.ext(r)
#                 return
#             if opcode == wasmConvention.call_indirect:
#                 if instr.immediate_arguments[1] != 0x00:
#                     raise Exception("zero byte malformed in call_indirect")
#                 idx = ctx.stack.pop().n
#                 tab = ctx.tables[module.tableaddrs[0]]
#                 # if not 0 <= idx < len(tab.elements):
#                 #     raise Exception('undefined element index')
#                 #TODO:how to deal call_indirect efficently
#                 if not isDecisiable(idx):
#                     for i, e in enumerate(tab.elements):
#                         maybe = True
#                         for i, t in enumerate(self.runtime.store.funcs[self.runtime.module_instance.funcaddrs[e]].functype.args):
#                             ia = t
#                             ib = ctx.stack.data[-1 - i]
#                             if ia != ib.valtype:
#                                 maybe = False
#                         if maybe:
#                             new_ctx = ctx.copy()
#                             new_ctx.path_conditions_and_vars["path_condition"].append(idx == e)
#                             r = self.call(module, tab.elem[idx], self.runtime.store, new_ctx)
#                             new_ctx.stack.ext(r)
#                             return
#                 else:
#                     if isSymbolic():
#                         idx = idx.as_long()
#                     maybe = True
#                     for i, t in enumerate(self.runtime.store.funcs[self.runtime.module_instance.funcaddrs[idx]].functype.args):
#                         ia = t
#                         ib = ctx.stack.data[-1 - i]
#                         if ia != ib.valtype:
#                             maybe = False
#                     if maybe:
#                         new_ctx = ctx.copy()
#                         r = self.call(module, tab.elem[idx], self.runtime.store, new_ctx)
#                         new_ctx.stack.ext(r)
#                         return
#                     else:
#                         log.panicln("call_inderect wrong type function")
#
#             return
#         if opcode == wasmConvention.drop:
#             ctx.stack.pop()
#             return
#         if opcode == wasmConvention.select:
#             cond = ctx.stack.pop().n
#             a = ctx.stack.pop()
#             b = ctx.stack.pop()
#             ctx.stack.add(Value(a.valtype, simplify(If(cond != 0, b, a ))))
#             return
#         if opcode == wasmConvention.get_local:
#             ctx.stack.add(frame.locals[instr.immediate_arguments])
#             return
#         if opcode == wasmConvention.set_local:
#             if instr.immediate_arguments >= len(frame.locals):
#                 frame.locals.extend(
#                     [Value.from_i32(0) for _ in range(instr.immediate_arguments - len(frame.locals) + 1)]
#                 )
#             frame.locals[instr.immediate_arguments] = ctx.stack.pop()
#             return
#         if opcode == wasmConvention.tee_local:
#             if instr.immediate_arguments >= len(frame.locals):
#                 frame.locals.extend(
#                     [Value.from_i32(0) for _ in range(instr.immediate_arguments - len(frame.locals) + 1)]
#                 )
#             frame.locals[instr.immediate_arguments] = ctx.stack.top()
#             return
#         if opcode == wasmConvention.get_global:
#             ctx.stack.add(ctx.globals[module.globaladdrs[instr.immediate_arguments]].value)
#             return
#         if opcode == wasmConvention.set_global:
#             ctx.globals[module.globaladdrs[instr.immediate_arguments]] = GlobalInstance(ctx.stack.pop(), True)
#             return
#         if opcode >= wasmConvention.i32_load and opcode <= wasmConvention.grow_memory:
#             m = ctx.mems[module.memaddrs[0]]
#             if opcode >= wasmConvention.i32_load and opcode <= wasmConvention.i64_load32_u:
#                 root = ctx.stack.pop().n
#                 # a = root + instr.immediate_arguments[1]
#                 if not root in ctx.mems:
#                     log.debugln("Not expected memory model: 0")
#                     return
#                 #TODo:check if out of bounds
#                 # if a + wasmConvention.opcodes[opcode][2] > len(m.data):
#                 #     raise Exception('pywasm: out of bounds memory access')
#                 if opcode == wasmConvention.i32_load:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 32, 32, instr.immediate_arguments[1]), 1, 0)
#                     # ctx.stack.add(Value.from_i32(num.LittleEndian.i32(m.data[a:a + 4])))
#                     return
#                 if opcode == wasmConvention.i64_load:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 64, 64, instr.immediate_arguments[1]), 1, 0)
#                     # ctx.stack.add(Value.from_i64(num.LittleEndian.i64(m.data[a:a + 8])))
#                     return
#                 if opcode == wasmConvention.f32_load:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 32, 32, instr.immediate_arguments[1]), 0, 0)
#                     # ctx.stack.add(Value.from_f32(num.LittleEndian.f32(m.data[a:a + 4])))
#                     return
#                 if opcode == wasmConvention.f64_load:
#                     # stack.add(Value.from_f64(num.LittleEndian.f64(m.data[a:a + 8])))
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 64, 64, instr.immediate_arguments[1]), 0, 0)
#                     return
#                 if opcode == wasmConvention.i32_load8_s:
#                     # stack.add(Value.from_i32(num.LittleEndian.i8(m.data[a:a + 1])))
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 8, 32, instr.immediate_arguments[1]), 1, 1)
#                     return
#                 if opcode == wasmConvention.i32_load8_u:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 8, 32, instr.immediate_arguments[1]), 1, 0)
#                     # stack.add(Value.from_i32(num.LittleEndian.u8(m.data[a:a + 1])))
#                     return
#                 if opcode == wasmConvention.i32_load16_s:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 16, 32, instr.immediate_arguments[1]), 1, 1)
#                     # stack.add(Value.from_i32(num.LittleEndian.i16(m.data[a:a + 2])))
#                     return
#                 if opcode == wasmConvention.i32_load16_u:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 16, 32, instr.immediate_arguments[1]), 1, 0)
#                     # stack.add(Value.from_i32(num.LittleEndian.u16(m.data[a:a + 2])))
#                     return
#                 if opcode == wasmConvention.i64_load8_s:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 8, 64, instr.immediate_arguments[1]), 1, 1)
#                     # stack.add(Value.from_i64(num.LittleEndian.i8(m.data[a:a + 1])))
#                     return
#                 if opcode == wasmConvention.i64_load8_u:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 8, 64, instr.immediate_arguments[1]), 1, 0)
#                     # stack.add(Value.from_i64(num.LittleEndian.u8(m.data[a:a + 1])))
#                     return
#                 if opcode == wasmConvention.i64_load16_s:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 16, 32, instr.immediate_arguments[1]), 1, 1)
#                     # stack.add(Value.from_i64(num.LittleEndian.i16(m.data[a:a + 2])))
#                     return
#                 if opcode == wasmConvention.i64_load16_u:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 16, 64, instr.immediate_arguments[1]), 1, 0)
#                     # stack.add(Value.from_i64(num.LittleEndian.u16(m.data[a:a + 2])))
#                     return
#                 if opcode == wasmConvention.i64_load32_s:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 32, 64, instr.immediate_arguments[1]), 1, 1)
#                     # stack.add(Value.from_i64(num.LittleEndian.i32(m.data[a:a + 4])))
#                     return
#                 if opcode == wasmConvention.i64_load32_u:
#                     ctx.stack.add(self._load_memory(ctx.mems[root], 32, 64, instr.immediate_arguments[1]), 1, 0)
#                     # stack.add(Value.from_i64(num.LittleEndian.u32(m.data[a:a + 4])))
#                     return
#                 return
#             if opcode >= wasmConvention.i32_store and opcode <= wasmConvention.i64_store32:
#                 v = ctx.stack.pop().n
#                 root = ctx.stack.pop().n
#                 offset = instr.immediate_arguments[1]
#                 #TODO:what if out of bounds
#                 # if a + wasmConvention.opcodes[opcode][2] > len(m.data):
#                 #     raise Exception('pywasm: out of bounds memory access')
#                 if opcode == wasmConvention.i32_store:
#                     self._store_memory(root, ctx, offset, 32, wasmConvention.i32, v)
#                     # m.data[a:a + 4] = num.LittleEndian.pack_i32(v)
#                     return
#                 if opcode == wasmConvention.i64_store:
#                     self._store_memory(root, ctx, offset, 64, wasmConvention.i64, v)
#                     # m.data[a:a + 8] = num.LittleEndian.pack_i64(v)
#                     return
#                 if opcode == wasmConvention.f32_store:
#                     self._store_memory(root, ctx, offset, 32, wasmConvention.f32, v)
#                     # m.data[a:a + 4] = num.LittleEndian.pack_f32(v)
#                     return
#                 if opcode == wasmConvention.f64_store:
#                     self._store_memory(root, ctx, offset, 64, wasmConvention.f64, v)
#                     # m.data[a:a + 8] = num.LittleEndian.pack_f64(v)
#                     return
#                 if opcode == wasmConvention.i32_store8:
#                     self._store_memory(root, ctx, offset, 8, wasmConvention.i32, v)
#                     # m.data[a:a + 1] = num.LittleEndian.pack_i8(num.int2i8(v))
#                     return
#                 if opcode == wasmConvention.i32_store16:
#                     self._store_memory(root, ctx, offset, 16, wasmConvention.i32, v)
#                     # m.data[a:a + 2] = num.LittleEndian.pack_i16(num.int2i16(v))
#                     return
#                 if opcode == wasmConvention.i64_store8:
#                     self._store_memory(root, ctx, offset, 8, wasmConvention.i64, v)
#                     # m.data[a:a + 1] = num.LittleEndian.pack_i8(num.int2i8(v))
#                     return
#                 if opcode == wasmConvention.i64_store16:
#                     self._store_memory(root, ctx, offset, 16, wasmConvention.i32, v)
#                     # m.data[a:a + 2] = num.LittleEndian.pack_i16(num.int2i16(v))
#                     return
#                 if opcode == wasmConvention.i64_store32:
#                     self._store_memory(root, ctx, offset, 32, wasmConvention.i64, v)
#                     # m.data[a:a + 4] = num.LittleEndian.pack_i32(num.int2i32(v))
#                     return
#                 return
#             if opcode == wasmConvention.current_memory:
#                 #TODO:
#                 ctx.stack.add(Value.from_i32(ctx.mem.size))
#                 return
#             if opcode == wasmConvention.grow_memory:
#                 cursize = m.size
#                 grow_n = ctx.stack.pop().n
#                 m.grow(grow_n)
#                 ctx.stack.add(Value.from_i32(cursize))
#                 return
#             return
#         if opcode >= wasmConvention.i32_const and opcode <= wasmConvention.f64_const:
#             if opcode == wasmConvention.i32_const:
#                 ctx.stack.add(Value.from_i32(instr.immediate_arguments))
#                 return
#             if opcode == wasmConvention.i64_const:
#                 ctx.stack.add(Value.from_i64(instr.immediate_arguments))
#                 return
#             if opcode == wasmConvention.f32_const:
#                 ctx.stack.add(Value.from_f32(instr.immediate_arguments))
#                 return
#             if opcode == wasmConvention.f64_const:
#                 ctx.stack.add(Value.from_f64(instr.immediate_arguments))
#                 return
#             return
#         if opcode == wasmConvention.i32_eqz:
#             ctx.stack.add(Value.from_i32(ctx.stack.pop().n == 0))
#             return
#         if opcode >= wasmConvention.i32_eq and opcode <= wasmConvention.i32_geu:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.i32_eq:
#                 ctx.stack.add(Value.from_i32(a == b))
#                 return
#             if opcode == wasmConvention.i32_ne:
#                 ctx.stack.add(Value.from_i32(a != b))
#                 return
#             if opcode == wasmConvention.i32_lts:
#                 ctx.stack.add(Value.from_i32(a < b))
#                 return
#             if opcode == wasmConvention.i32_ltu:
#                 ctx.stack.add(Value.from_i32(ULT(a, b)))
#                 return
#             if opcode == wasmConvention.i32_gts:
#                 ctx.stack.add(Value.from_i32(a > b))
#                 return
#             if opcode == wasmConvention.i32_gtu:
#                 ctx.stack.add(Value.from_i32(UGT(a > b)))
#                 return
#             if opcode == wasmConvention.i32_les:
#                 ctx.stack.add(Value.from_i32(a <= b))
#                 return
#             if opcode == wasmConvention.i32_leu:
#                 ctx.stack.add(Value.from_i32(ULE( a, b)))
#                 return
#             if opcode == wasmConvention.i32_ges:
#                 ctx.stack.add(Value.from_i32(a >= b))
#                 return
#             if opcode == wasmConvention.i32_geu:
#                 ctx.stack.add(Value.from_i32(UGE(a, b)))
#                 return
#             return
#         if opcode == wasmConvention.i64_eqz:
#             ctx.stack.add(Value(wasmConvention.i32, simplify(If(ctx.stack.pop().n == 0, BitVecVal(1, 32), BitVecVal(0, 32)))))
#             return
#         if opcode >= wasmConvention.i64_eq and opcode <= wasmConvention.i64_geu:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.i64_eq:
#                 ctx.stack.add(Value.from_i32(a == b))
#                 return
#             if opcode == wasmConvention.i64_ne:
#                 ctx.stack.add(Value.from_i32(a != b))
#                 return
#             if opcode == wasmConvention.i64_lts:
#                 ctx.stack.add(Value.from_i32(a < b))
#                 return
#             if opcode == wasmConvention.i64_ltu:
#                 ctx.stack.add(Value.from_i32(ULT(a, b)))
#                 return
#             if opcode == wasmConvention.i64_gts:
#                 ctx.stack.add(Value.from_i32(a > b))
#                 return
#             if opcode == wasmConvention.i64_gtu:
#                 ctx.stack.add(Value.from_i32(UGT(a, b)))
#                 return
#             if opcode == wasmConvention.i64_les:
#                 ctx.stack.add(Value.from_i32(a <= b))
#                 return
#             if opcode == wasmConvention.i64_leu:
#                 ctx.stack.add(Value.from_i32(ULE(a, b)))
#                 return
#             if opcode == wasmConvention.i64_ges:
#                 ctx.stack.add(Value.from_i32(a >= b))
#                 return
#             if opcode == wasmConvention.i64_geu:
#                 ctx.stack.add(Value.from_i32(UGE(a, b)))
#                 return
#             return
#         if opcode >= wasmConvention.f32_eq and opcode <= wasmConvention.f64_ge:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.f32_eq:
#                 ctx.stack.add(Value.from_i32(fpEQ(a, b)))
#                 return
#             if opcode == wasmConvention.f32_ne:
#                 ctx.stack.add(Value.from_i32(fpNEQ(a != b)))
#                 return
#             if opcode == wasmConvention.f32_lt:
#                 ctx.stack.add(Value.from_i32(fpLT(a < b)))
#                 return
#             if opcode == wasmConvention.f32_gt:
#                 ctx.stack.add(Value.from_i32(fpGT(a > b)))
#                 return
#             if opcode == wasmConvention.f32_le:
#                 ctx.stack.add(Value.from_i32(fpLEQ(a <= b)))
#                 return
#             if opcode == wasmConvention.f32_ge:
#                 ctx.stack.add(Value.from_i32(fpGEQ(a >= b)))
#                 return
#             if opcode == wasmConvention.f64_eq:
#                 ctx.stack.add(Value.from_i32(fpEQ(a == b)))
#                 return
#             if opcode == wasmConvention.f64_ne:
#                 ctx.stack.add(Value.from_i32(fpNEQ(a != b)))
#                 return
#             if opcode == wasmConvention.f64_lt:
#                 ctx.stack.add(Value.from_i32(fpLT(a < b)))
#                 return
#             if opcode == wasmConvention.f64_gt:
#                 ctx.stack.add(Value.from_i32(fpGT(a > b)))
#                 return
#             if opcode == wasmConvention.f64_le:
#                 ctx.stack.add(Value.from_i32(fpLEQ(a <= b)))
#                 return
#             if opcode == wasmConvention.f64_ge:
#                 ctx.stack.add(Value.from_i32(fpGEQ(a >= b)))
#                 return
#             return
#         if opcode >= wasmConvention.i32_clz and opcode <= wasmConvention.i32_popcnt:
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.i32_clz:
#                 c = 0
#                 flag = True
#                 for i in range(32):
#                     c = If(And((a & 0x80000000) == 0, flag), c+1, c)
#                     flag = If(And((a & 0x80000000) == 0,  flag), True, False)
#                     a = a*2
#                 ctx.stack.add(Value.from_i32(c))
#                 return
#             if opcode == wasmConvention.i32_ctz:
#                 c = 0
#                 flag = True
#                 for i in range(32):
#                     c = If(And((a % 2) == 0, flag), c + 1, c)
#                     flag = If(And((a %2) == 0, flag), True, False)
#                     a = a / 2
#
#                 ctx.stack.add(Value.from_i32(c))
#                 return
#             if opcode == wasmConvention.i32_popcnt:
#                 c = 0
#                 for i in range(32):
#                     c = If(a & 0x1, c+1, c)
#                     a /= 2
#                 ctx.stack.add(Value.from_i32(c))
#                 return
#             return
#         if opcode >= wasmConvention.i32_add and opcode <= wasmConvention.i32_rotr:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if isAllReal(a, b):
#                 a = BitVecVal(a, 32)
#             if opcode in [
#                 wasmConvention.i32_divs,
#                 wasmConvention.i32_divu,
#                 wasmConvention.i32_rems,
#                 wasmConvention.i32_remu,
#             ]:
#                 self.solver.push()
#                 self.solver.add(b == 0)
#                 ret = check_sat(self.solver, True)
#                 if ret == sat:
#                     raise Exception('integer divide by zero')
#                 elif ret == unsat:
#                     pass
#                 else:
#                     log.println("integer maybe divided by zero")
#             if opcode == wasmConvention.i32_add:
#                 ctx.stack.add(Value.from_i32(a+b))
#                 return
#             if opcode == wasmConvention.i32_sub:
#                 ctx.stack.add(Value.from_i32(a-b))
#                 return
#             if opcode == wasmConvention.i32_mul:
#                 ctx.stack.add(Value.from_i32(a * b))
#                 return
#             if opcode == wasmConvention.i32_divs:
#                 # if a == 0x80000000 and b == -1:
#                 #     raise Exception('integer overflow')
#                 ctx.stack.add(Value.from_i32(a/b))
#                 return
#             if opcode == wasmConvention.i32_divu:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(UDiv(a, b))))
#                 return
#             if opcode == wasmConvention.i32_rems:
#                 ctx.stack.add(Value.from_i32(SRem(a, b)))
#                 return
#             if opcode == wasmConvention.i32_remu:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(URem(a, b))))
#                 return
#             if opcode == wasmConvention.i32_and:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(a & b)))
#                 return
#             if opcode == wasmConvention.i32_or:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(a | b)))
#                 return
#             if opcode == wasmConvention.i32_xor:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(a ^ b)))
#                 return
#             if opcode == wasmConvention.i32_shl:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(a << (b % 0x20))))
#                 return
#             if opcode == wasmConvention.i32_shrs:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(a >> (b % 0x20))))
#                 return
#             if opcode == wasmConvention.i32_shru:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(LShR(a, b % 0x20))))
#                 return
#             if opcode == wasmConvention.i32_rotl:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(RotateLeft(a, b))))
#                 return
#             if opcode == wasmConvention.i32_rotr:
#                 ctx.stack.add(Value(wasmConvention.i32, simplify(RotateRight(a, b))))
#                 return
#             return
#         if opcode >= wasmConvention.i64_clz and opcode <= wasmConvention.i64_popcnt:
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.i64_clz:
#                 c = 0
#                 flag = True
#                 for i in range(64):
#                     c = If(And((a & 0x8000000000000000) == 0, flag), c+1, c)
#                     flag = If(And((a & 0x8000000000000000) == 0,  flag), True, False)
#                     a = a*2
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(c)))
#                 return
#             if opcode == wasmConvention.i64_ctz:
#                 c = 0
#                 flag = True
#                 for i in range(64):
#                     c = If(And((a % 2) == 0, flag), c + 1, c)
#                     flag = If(And((a % 2) == 0, flag), True, False)
#                     a = a / 2
#
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(c)))
#                 return
#             if opcode == wasmConvention.i64_popcnt:
#                 c = 0
#                 for i in range(64):
#                     c = If(a & 0x1, c + 1, c)
#                     a /= 2
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(c)))
#                 return
#             return
#         if opcode >= wasmConvention.i64_add and opcode <= wasmConvention.i64_rotr:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if isAllReal(a, b):
#                 a = BitVecVal(a, 32)
#             if opcode in [
#                 wasmConvention.i64_divs,
#                 wasmConvention.i64_divu,
#                 wasmConvention.i64_rems,
#                 wasmConvention.i64_remu,
#             ]:
#                 self.solver.push()
#                 self.solver.add(b == 0)
#                 ret = check_sat(self.solver, True)
#                 if ret == sat:
#                     raise Exception('integer divide by zero')
#                 elif ret == unsat:
#                     pass
#                 else:
#                     log.println("integer maybe divided by zero")
#             if opcode == wasmConvention.i64_add:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a + b)))
#                 return
#             if opcode == wasmConvention.i64_sub:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a - b)))
#                 return
#             if opcode == wasmConvention.i64_mul:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a * b)))
#                 return
#             if opcode == wasmConvention.i64_divs:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a/ b)))
#                 return
#             if opcode == wasmConvention.i64_divu:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(UDiv(a, b))))
#                 return
#             if opcode == wasmConvention.i64_rems:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(SRem(a, b))))
#                 return
#             if opcode == wasmConvention.i64_remu:
#                 ctx.stack.add(Value(wasmConvention.i64, URem(a, b)))
#                 return
#             if opcode == wasmConvention.i64_and:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a & b)))
#                 return
#             if opcode == wasmConvention.i64_or:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a | b)))
#                 return
#             if opcode == wasmConvention.i64_xor:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a ^ b)))
#                 return
#             if opcode == wasmConvention.i64_shl:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a << (b % 0x40))))
#                 return
#             if opcode == wasmConvention.i64_shrs:
#                 ctx.stack.add(Value(wasmConvention.i64, simplify(a >> (b % 0x40))))
#                 return
#             if opcode == wasmConvention.i64_shru:
#                 ctx.stack.add(Value(wasmConvention.i64,LShR(a, b % 0x40)))
#                 return
#             if opcode == wasmConvention.i64_rotl:
#                 ctx.stack.add(Value(wasmConvention.i64, RotateLeft(a, b)))
#                 return
#             if opcode == wasmConvention.i64_rotr:
#                 ctx.stack.add(Value(wasmConvention.i64, RotateRight(a, b)))
#                 return
#             return
#         if opcode >= wasmConvention.f32_abs and opcode <= wasmConvention.f32_sqrt:
#             a = ctx.stack.pop().n
#
#             if opcode == wasmConvention.f32_abs:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, simplify(fpAbs(a))))
#                 else:
#                     ctx.stack.add((Value(wasmConvention.f32, abs(a))))
#                 return
#             if opcode == wasmConvention.f32_neg:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, fpNeg(a)))
#                 else:
#                     ctx.stack.add(Value(wasmConvention.f32, -a))
#                 return
#             if opcode == wasmConvention.f32_ceil:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, simplify(fpSignedToFP(RNE(), fpToSBV(RTP(), a, BitVecSort(32)), Float32()))))
#                 else:
#                     ctx.stack.add(Value(wasmConvention.f32, math.ceil(a))
#                 return
#             if opcode == wasmConvention.f32_floor:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, simplify(fpSignedToFP(RNE(), fpToSBV(RTN(), a, BitVecSort(32)), Float32()))))
#                 else:
#                     ctx.stack.add(Value(wasmConvention.f32, math.floor(a)))
#                 return
#             if opcode == wasmConvention.f32_trunc:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, simplify(fpToSBV(RTZ(), a, BitVecSort(32)))))
#                 else:
#                     ctx.stack.add(Value(wasmConvention.f32, math.trunc(a)))
#                 return
#             if opcode == wasmConvention.f32_nearest:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, simplify(fpToSBV(RNE(), a, BitVecSort(32)))))
#                 else:
#                     ctx.stack.add(Value(wasmConvention.f32, round(a)))
#                 return
#             if opcode == wasmConvention.f32_sqrt:
#                 if isSymbolic(a):
#                     ctx.stack.add(Value(wasmConvention.f32, fpSqrt(a)))
#                 else:
#                     ctx.stack.add(Value(wasmConvention.f32, math.sqrt(a)))
#                 return
#             return
#         if opcode >= wasmConvention.f32_add and opcode <= wasmConvention.f32_copysign:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.f32_add:
#                 ctx.stack.add(Value(wasmConvention.f32, fpAdd(a + b)))
#                 return
#             if opcode == wasmConvention.f32_sub:
#                 ctx.stack.add(Value(wasmConvention.f32, fpSub(a - b)))
#                 return
#             if opcode == wasmConvention.f32_mul:
#                 ctx.stack.add(Value(wasmConvention.f32, fpMul(a * b)))
#                 return
#             if opcode == wasmConvention.f32_div:
#                 ctx.stack.add(Value(wasmConvention.f32, fpDiv(a / b)))
#                 return
#             if opcode == wasmConvention.f32_min:
#                 ctx.stack.add(Value(wasmConvention.f32, fpMin((a, b))))
#                 return
#             if opcode == wasmConvention.f32_max:
#                 ctx.stack.add(Value(wasmConvention.f32, fpMax((a, b))))
#                 return
#             if opcode == wasmConvention.f32_copysign:
#                 ctx.stack.add(Value(wasmConvention.f32, If(b>0, fpAbs(a), -fpAbs(a))))
#                 return
#             return
#         if opcode >= wasmConvention.f64_abs and opcode <= wasmConvention.f64_sqrt:
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.f64_abs:
#                 ctx.stack.add(Value(wasmConvention.f64, fpAbs(a)))
#                 return
#             if opcode == wasmConvention.f64_neg:
#                 ctx.stack.add(Value(wasmConvention.f64, fpNeg(-a)))
#                 return
#             if opcode == wasmConvention.f64_ceil:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpToFP(RNE(), fpToSBV(RTP(), a, BitVecSort(64)), Float64()))))
#                 return
#             if opcode == wasmConvention.f64_floor:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpToFP(RNE(), fpToSBV(RTN(), a, BitVecSort(64)), Float64()))))
#                 return
#             if opcode == wasmConvention.f64_trunc:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpToSBV(RTZ(), a, BitVecSort(64)))))
#                 return
#             if opcode == wasmConvention.f64_nearest:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpToSBV(RTZ(), a, BitVecSort(64)))))
#                 return
#             if opcode == wasmConvention.f64_sqrt:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpSqrt(a))))
#                 return
#             return
#         if opcode >= wasmConvention.f64_add and opcode <= wasmConvention.f64_copysign:
#             b = ctx.stack.pop().n
#             a = ctx.stack.pop().n
#             if opcode == wasmConvention.f64_add:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpAdd(a + b))))
#                 return
#             if opcode == wasmConvention.f64_sub:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpSub(a - b))))
#                 return
#             if opcode == wasmConvention.f64_mul:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpMul(a * b))))
#                 return
#             if opcode == wasmConvention.f64_div:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpDiv(a / b))))
#                 return
#             if opcode == wasmConvention.f64_min:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpMin((a, b)))))
#                 return
#             if opcode == wasmConvention.f64_max:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(fpMax((a, b)))))
#                 return
#             if opcode == wasmConvention.f64_copysign:
#                 ctx.stack.add(Value(wasmConvention.f64, simplify(If(b > 0, fpAbs(a), -fpAbs(a)))))
#                 return
#             return
#         if opcode >= wasmConvention.i32_wrap_i64 and opcode <= wasmConvention.f64_promote_f32:
#             a = ctx.stack.pop().n
#             if opcode in [
#                 wasmConvention.i32_trunc_sf32,
#                 wasmConvention.i32_trunc_uf32,
#                 wasmConvention.i32_trunc_sf64,
#                 wasmConvention.i32_trunc_uf64,
#                 wasmConvention.i64_trunc_sf32,
#                 wasmConvention.i64_trunc_uf32,
#                 wasmConvention.i64_trunc_sf64,
#                 wasmConvention.i64_trunc_uf64,
#             ]:
#                 # todo:check NaN
#                 # if math.isnan(a):
#                 #     raise Exception('invalid conversion to integer')
#                 pass
#             if opcode == wasmConvention.i32_wrap_i64:
#                 ctx.stack.add(Value(wasmConvention.i32, Int2BV(BV2Int(a%294967295), 32)))
#                 return
#             if opcode == wasmConvention.i32_trunc_sf32:
#                 #todo:overflow detect
#                 # if a > 2 ** 31 - 1 or a < -2 ** 32:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i32, fpToSBV(RTZ(), a, BitVecSort(32))))
#                 return
#             if opcode == wasmConvention.i32_trunc_uf32:
#                 #todo:overflow detect
#                 # if a > 2 ** 32 - 1 or a < -1:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i32, fpToUBV(RTZ(), a, BitVecSort(32))))
#                 return
#             if opcode == wasmConvention.i32_trunc_sf64:
#                 # if a > 2 ** 31 - 1 or a < -2 ** 32:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i32, fpToSBV(RTZ(), a, BitVecSort(32))))
#                 return
#             if opcode == wasmConvention.i32_trunc_uf64:
#                 # if a > 2 ** 32 - 1 or a < -1:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i32, fpToUBV(RTZ(), a, BitVecSort(32))))
#                 return
#             if opcode == wasmConvention.i64_extend_si32:
#                 ctx.stack.add(Value(wasmConvention.i64, SignExt(32, a)))
#                 return
#             if opcode == wasmConvention.i64_extend_ui32:
#                 ctx.stack.add(Value(wasmConvention.i64,ZeroExt(32, a)))
#                 return
#             if opcode == wasmConvention.i64_trunc_sf32:
#                 # if a > 2 ** 63 - 1 or a < -2 ** 63:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i64, fpToUBV(RTZ(), a, BitVecSort(64))))
#                 return
#             if opcode == wasmConvention.i64_trunc_uf32:
#                 # if a > 2 ** 63 - 1 or a < -1:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i64, fpToUBV(RTZ(), a, BitVecSort(64))))
#                 return
#             if opcode == wasmConvention.i64_trunc_sf64:
#                 ctx.stack.add(Value(wasmConvention.i64, fpToSBV(RTZ(), a, BitVecSort(64))))
#                 return
#             if opcode == wasmConvention.i64_trunc_uf64:
#                 # if a < -1:
#                 #     raise Exception('pywasm: integer overflow')
#                 ctx.stack.add(Value(wasmConvention.i64, fpToUBV(RNE(), a, BitVecSort(64))))
#                 return
#             if opcode == wasmConvention.f32_convert_si32:
#                 ctx.stack.add(Value(wasmConvention.f32, fpSignedToFP(RNE(), a, Float32())))
#                 return
#             if opcode == wasmConvention.f32_convert_ui32:
#                 ctx.stack.add(Value(wasmConvention.f32, fpBVToFP(RNE(), a, Float32())))
#                 return
#             if opcode == wasmConvention.f32_convert_si64:
#                 ctx.stack.add(Value(wasmConvention.f32, fpSignedToFP(RNE(), a, Float32())))
#                 return
#             if opcode == wasmConvention.f32_convert_ui64:
#                 ctx.stack.add(Value(wasmConvention.f32, fpBVToFP(RNE(), a, Float32())))
#                 return
#             if opcode == wasmConvention.f32_demote_f64:
#                 ctx.stack.add(Value(wasmConvention.f32, fpFPToFP(RNE(), a, Float32())))
#                 return
#             if opcode == wasmConvention.f64_convert_si32:
#                 ctx.stack.add(Value(wasmConvention.f32, fpSignedToFP(RNE(), a, Float64())))
#                 return
#             if opcode == wasmConvention.f64_convert_ui32:
#                 ctx.stack.add(Value(wasmConvention.f64, fpBVToFP(RNE(), a, Float64())))
#                 return
#             if opcode == wasmConvention.f64_convert_si64:
#                 ctx.stack.add(Value(wasmConvention.f64, fpSignedToFP(RNE(), a, Float64())))
#                 return
#             if opcode == wasmConvention.f64_convert_ui64:
#                 ctx.stack.add(Value(wasmConvention.f64,fpBVToFP(RNE(), a, Float64())))
#                 return
#             if opcode == wasmConvention.f64_promote_f32:
#                 ctx.stack.add(Value(wasmConvention.f64, fpFPToFP(RNE(), a, Float32())))
#                 return
#             return
#         if opcode >= wasmConvention.i32_reinterpret_f32 and opcode <= wasmConvention.f64_reinterpret_i64:
#             a = ctx.stack.pop().n
#             #todo: wasm's format for float encoding
#             if opcode == wasmConvention.i32_reinterpret_f32:
#                 ctx.stack.add(Value(wasmConvention.i32, fpToIEEEBV(a)))
#                 return
#             if opcode == wasmConvention.i64_reinterpret_f64:
#                 ctx.stack.add(Value(wasmConvention.i64, fpToIEEEBV(a)))
#                 return
#             if opcode == wasmConvention.f32_reinterpret_i32:
#                 ctx.stack.add(Value(wasmConvention.f32, fpBVToFP(a, Float32())))
#                 return
#             if opcode == wasmConvention.f64_reinterpret_i64:
#                 ctx.stack.add(Value(wasmConvention.f64, fpBVToFP(a, Float64())))
#                 return
#             return
#
#         return
#
#     def _load_memory(self, mems, from_size, to_size, offset, is_int=True, is_signed=False):
#         result = None
#         for e in mems.keys():
#             if offset == e and from_size <= mems[e][0]:
#                 result = mems[e][1]
#             else:
#                 log.debugln("Not expect memory model: 1")
#
#         assert(isinstance(result, Value))
#
#         if is_int:
#             assert(result.valtype == wasmConvention.BVS and isSymbolic(result.n))
#             if from_size == 8 and to_size == 32:
#                 return Value(wasmConvention.i32, Int2BV(BV2Int(result & 0xff, is_signed),32))
#             elif from_size == 8 and to_size == 64:
#                 return Value(wasmConvention.i64, Int2BV(BV2Int(result & 0xff, is_signed),64))
#             elif from_size == 16 and to_size == 32:
#                 return Value(wasmConvention.i32, Int2BV(BV2Int(result & 0xffff, is_signed),32))
#             elif from_size == 16 and to_size == 64:
#                 return Value(wasmConvention.i64, Int2BV(BV2Int(result & 0xffff, is_signed),64))
#             elif from_size == 32 and to_size == 32:
#                 return Value(wasmConvention.i32, result & 0xffffffff)
#             elif from_size == 32 and to_size == 64:
#                 return Value(wasmConvention.i64, Int2BV(BV2Int(result & 0xffffffff, is_signed),64))
#             elif from_size == 64 and to_size == 64:
#                 return Value(wasmConvention.i32, result & 0xffffffffffffffff)
#             else:
#                 log.debugln("unknown load type")
#         else:
#             if from_size == 32:
#                 assert(result.valtype == wasmConvention.f32)
#                 return result
#             elif from_size == 64:
#                 assert (result.valtype == wasmConvention.f64)
#                 return result
#             else:
#                 log.debugln("unknown load type")
#
#     def _store_memory(self, root, ctx, offset, size, valtype, value):
#         if root in ctx.mems:
#             mems = ctx.mems[root]
#         else:
#             mems = {}
#             ctx.mems[root] = mems
#         for key in mems:
#             if not (key + mems[key][0] < offset or key >= offset + size):
#                 mems.pop(key)
#         mems[offset] = (size, Value(valtype, value))
#
#
#
#
#
#
#
# class Context:
#     def __init__(self, **kwargs):
#         attr_defaults = {
#             "stack": Stack(),
#             "mems": [],
#             "visited": {},
#             "tables": [],
#             "globals":[],
#             "global_state": {},
#             "path_conditions_and_vars": {},
#             "gas": 0,
#         }
#         for (attr, default) in six.iteritems(attr_defaults):
#             setattr(self, attr, kwargs.get(attr, default))
#
#     def copy(self):
#         _kwargs = custom_deepcopy(self.__dict__)
#         o = Context(**_kwargs)
#         o.stack = self.stack.copy()
#         return o
#
#
#
#
#
#
#

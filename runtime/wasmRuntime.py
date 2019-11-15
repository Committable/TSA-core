import typing

from z3 import simplify

from disassembler import wasmModule, wasmConvention
import log
from disassembler.wasmConvention import valtype, opcodes, EDGE_UNCONDITIONAL, EDGE_CONDITIONAL_IF, EDGE_CONDITIONAL_BR, \
    EDGE_FALLTHROUGH, EDGE_TERMINAL
from interpreter import symbolicVarGenerator
from runtime.basicBlock import BasicBlock
from solver import symbolicVar
from utils import custom_deepcopy, isSymbolic


class WASMRuntime:
    # A webassembly runtime manages Store, stack, and other runtime structure. They forming the WebAssembly abstract.

    def __init__(self, module: wasmModule.Module, imps: typing.Dict = None):
        self.module = module
        self.module_instance = ModuleInstance()
        self.store = Store()
        self.gen = symbolicVarGenerator.Generator()

        imps = imps if imps else {}
        externvals = []
        for e in self.module.imports:
            # if e.module not in imps or e.name not in imps[e.module]:
            #     raise Exception(f'pywasm: global import {e.module}.{e.name} not found')
            if e.kind == wasmConvention.extern_func:
                a = HostFunc(self.module.types[e.desc])
                self.store.funcs.append(a)
                externvals.append(ExternValue(e.kind, len(self.store.funcs) - 1))
                continue
            if e.kind == wasmConvention.extern_table:
                a = TableInstance(e.module,e.name,e.desc.elemtype,e.desc.limits)
                self.store.tables.append(a)
                externvals.append(ExternValue(e.kind, len(self.store.tables) - 1))
                continue
            if e.kind == wasmConvention.extern_mem:
                a = MemoryInstance(e.module,e.name,e.desc)
                self.store.mems.append(a)
                externvals.append(ExternValue(e.kind, len(self.store.mems) - 1))
                continue
            if e.kind == wasmConvention.extern_global:
                v = symbolicVar.produce_symbolic_var(self.gen.gen_import_global_var(e.module, e.name), valtype[e.desc.valtype][0])
                a = GlobalInstance(Value(e.desc.valtype, v), e.desc.mut)
                self.store.globals.append(a)
                externvals.append(ExternValue(e.kind, len(self.store.globals) - 1))
                continue
        self.module_instance.instantiate(self.module, self.store, externvals)
        self.construct_cfg()

    def func_addr(self, name: str):
        # Get a function address denoted by the function name
        for e in self.module_instance.exports:
            if e.name == name and e.value.extern_type == wasmConvention.extern_func:
                return e.value.addr
        raise Exception('pywasm: function not found')

    def exec(self, name: str, args: typing.List):
        # Invoke a function denoted by the function address with the provided arguments.
        func_addr = self.func_addr(name)
        func = self.store.funcs[self.module_instance.funcaddrs[func_addr]]
        # Mapping check for Python valtype to WebAssembly valtype
        for i, e in enumerate(func.functype.args):
            if e in [wasmConvention.i32, wasmConvention.i64]:
                assert isinstance(args[i], int)
            if e in [wasmConvention.f32, wasmConvention.f64]:
                assert isinstance(args[i], float)
            args[i] = Value(e, args[i])
        stack = Stack()
        stack.ext(args)
        log.debugln(f'Running function {name}({", ".join([str(e) for e in args])}):')
        # r = execution.call(self.module_instance, func_addr, self.store, stack)
        # if r:
        #     return r[0].n
        return None

    def construct_cfg(self):
        for addr in self.module_instance.funcaddrs:
            func = self.store.funcs[addr]
            if not isinstance(func, WasmFunc):
                continue
            block, edge = self._construct_blocks_edges(addr, func.code.expr.data)
            func.set_block(block)
            func.set_edges(edge)

    def _construct_blocks_edges(self, function_id, instructions):

        """
        Return a list of basicblock after
        statically parsing given instructions
        """

        basicblocks = list()
        vertices = {}
        edges = {}

        branches = []
        xrefs = []

        intent = 0
        blocks_tmp = []
        blocks_list = []

        # we need to do that because jump label are relative to the current block index
        for index, inst in enumerate(instructions[:-1]):

            if inst.is_block_terminator: #[else, end]
                start, name = blocks_tmp.pop()
                if opcodes[inst.code][0] == 'else':
                    end = inst.offset - 1
                else:
                    end = inst.offset
                blocks_list.append((intent, start, end, name))
                intent -= 1
            if inst.is_block_starter:  # in ['block', 'loop', 'if', 'else']:
                blocks_tmp.append((inst.offset, opcodes[inst.code][0]))
                intent += 1
            if inst.is_branch: #[br, br_if, br_table, if]
                branches.append((intent, inst))

        # add function body end
        blocks_list.append((0, 0, instructions[-1].offset, 'func'))
        blocks_list = sorted(blocks_list, key=lambda tup: (tup[1], tup[0]))

        for depth, inst in branches:
            labl = list()
            if opcodes[inst.code][0] == 'br_table':
                labl = inst.immediate_arguments[0]
            else:
                labl.append(inst.immediate_arguments)

            for d2 in labl:
                rep = next(((i, s, e, n) for i, s, e, n in blocks_list if
                            (i == (depth - d2) and s < inst.offset and e > inst.offset)), None)

                if rep:
                    i, start, end, name = rep
                    # if we branch to a 'loop' label
                    # we go at the entry of the 'loop' block
                    if name == 'loop':
                        value = start
                    # if we branch to a 'block' label
                    # we go at the end of the "block" block
                    elif name == 'block' or name == 'func':
                        value = end
                    # we don't know
                    else:
                        value = None
                    inst.xref.append(value)
                    xrefs.append(value)

        # assign xref for "if" branch
        # needed because 'if' don't used label
        for index, inst in enumerate(instructions[:-1]):
            if opcodes[inst.code][0] == 'if':
                g_block = next(iter([b for b in blocks_list if b[1] == inst.offset]), None)
                jump_target = g_block[2] + 1
                inst.xref.append(jump_target)
                xrefs.append(jump_target)
            elif opcodes[inst.code][0] == 'else':
                g_block = next(iter([b for b in blocks_list if b[1] == inst.offset]), None)
                jump_target = g_block[2] + 1
                inst.xref.append(jump_target)
                xrefs.append(jump_target)

        # enumerate blocks
        new_block = True

        for index, inst in enumerate(instructions):

            # creation of a block
            if new_block:
                block = BasicBlock(inst.offset,
                                   start_inst=inst,
                                   )
                new_block = False
            # add current instruction to the basicblock
            block.instructions.append(inst)

            # next instruction is a jump target
            if index < (len(instructions) - 1) and \
                    instructions[index + 1].offset in xrefs:
                new_block = True
            # absolute jump - br
            elif inst.is_branch_unconditional:
                new_block = True
            # conditionnal jump - br_if
            elif inst.is_branch_conditional:
                new_block = True
            # is_block_terminator
            # GRAPHICAL OPTIMIZATION: merge end together
            elif index < (len(instructions) - 1) and \
                    opcodes[instructions[index + 1].code][0] in ['else', 'loop']:  # is_block_terminator
                new_block = True
            # last instruction of the bytecode
            elif inst.offset == instructions[-1].offset:
                new_block = True

            if new_block:
                block.end = inst.offset
                block.end_instr = inst
                basicblocks.append(block)
                vertices[block.start] = block
                new_block = True

        # enumerate edges
        for index, block in enumerate(basicblocks):
            # get the last instruction
            inst = block.end_instr
            # unconditional jump - br
            if inst.is_branch_unconditional:
                for ref in inst.xref:
                    block.set_block_type(EDGE_UNCONDITIONAL)
                    block.set_jump_target(ref)
                    block.set_jump_to(ref)
                    vertices[ref].set_jump_from(block.start)
                    WASMRuntime._addEdge(edges, block.start, ref)
            # conditionnal jump - br_if, if
            elif inst.is_branch_conditional:
                if opcodes[inst.code][0] == 'if':
                    #TODO:make sure false and true branch
                    block.set_block_type(EDGE_CONDITIONAL_IF)
                    block.set_jump_target(inst.offset+1)
                    block.set_jump_to(inst.offset+1)
                    vertices[inst.offset+1].set_jump_from(block.start)
                    WASMRuntime._addEdge(edges, block.start, inst.offset+1)
                    if_b = next(iter([b for b in blocks_list if b[1] == inst.offset]), None)
                    # else_block = blocks_list[blocks_list.index(if_block) + 1]
                    jump_target = if_b[2] + 1
                    block.set_falls_to(jump_target)
                    block.set_jump_to(jump_target)
                    vertices[jump_target].set_jump_from(block.start)
                    WASMRuntime._addEdge(edges, block.start, jump_target)
                else:
                    for ref in inst.xref:
                        if ref and ref != inst.offset + 1:
                            # create conditionnal true edges
                            block.set_block_type(EDGE_CONDITIONAL_BR)
                            block.set_jump_targets(ref)
                            block.set_jump_to(ref)
                            vertices[ref].set_jump_from(block.start)
                            WASMRuntime._addEdge(edges, block.start, ref)
                    # create conditionnal false edge
                    block.set_block_type(EDGE_CONDITIONAL_IF)
                    block.set_falls_to(inst.offset + 1)
                    block.set_jump_to(inst.offset + 1)
                    vertices[inst.offset + 1].set_jump_from(block.start)
                    WASMRuntime._addEdge(edges, block.start, inst.offset + 1)
            # instruction that end the flow
            elif [opcodes[i.code][0] for i in block.instructions if i.is_halt]:
                block.set_block_type(EDGE_TERMINAL)
            elif inst.is_halt:
                block.set_block_type(EDGE_TERMINAL)

            # handle the case when you have if and else following
            elif inst.offset != instructions[-1].offset and \
                    opcodes[block.start_inst.code][0] != 'else' and \
                    opcodes[instructions[instructions.index(inst) + 1].code][0] == 'else':

                else_ins = instructions[instructions.index(inst) + 1]
                else_b = next(iter([b for b in blocks_list if b[1] == else_ins.offset]), None)

                block.set_block_type(EDGE_FALLTHROUGH)
                block.set_falls_to(else_b[2] + 1)
                block.set_jump_to(else_b[2] + 1)
                vertices[else_b[2] + 1].set_jump_from(block.start)
                WASMRuntime._addEdge(edges, block.start, else_b[2] + 1)
            # add the last intruction "end" in the last block
            elif inst.offset != instructions[-1].offset:
                # EDGE_FALLTHROUGH
                block.set_block_type(EDGE_FALLTHROUGH)
                block.set_falls_to(inst.offset + 1)
                block.set_jump_to(inst.offset + 1)
                vertices[inst.offset + 1].set_jump_from(block.start)
                WASMRuntime._addEdge(edges, block.start, inst.offset + 1)

        # prevent duplicate edges
        return vertices, edges

    def __repr__(self):
        runtime = self
        inp = {"module":self.module}
        print("########################## functions ##########################\n")
        for i in runtime.module_instance.funcaddrs:
            name = "$func" + str(i)
            if i in inp["module"].functions_name:
                name = inp["module"].functions_name[i]
            func = runtime.store.funcs[i]
            if isinstance(func, WasmFunc):
                print("WasmFunc:\n")
                print(name + " " + func.functype.__repr__() + "\n")
            elif isinstance(func, HostFunc):
                print("HostFunc:\n")
                print(name + " " + func.functype.__repr__() + "\n")
            else:
                raise ("unknown func\n")

        print("########################## table ##########################")
        for i in runtime.module_instance.tableaddrs:
            name = "$table" + str(i)
            print(name + "\n")
            table = runtime.store.tables[i]
            print(str(table.module) + "." + str(table.name) + "\n")
            # for i in range(len(table.elem)):
            #     if table.elem[i] != None:
            #         print(str(i) + ":" + str(table.elem[i]) + "\n")
            if len(table.elements) > 0:
                print(str(table.elements) + "\n")

        print("########################## memory ##########################")
        for i in runtime.module_instance.memaddrs:
            name = "$memory" + str(i)
            print(name)
            memory = runtime.store.mems[i]
            print(str(memory.module) + "." + str(memory.name))
            # for i in range(len(memory.data)):
            #     if memory.data[i] != 0x00:
            #         print(str(i) + ":" + str(memory.data[i]))
            if len(memory.datas) > 0:
                print(str(memory.datas) + "\n")

    @classmethod
    def _addEdge(cls, edges, from_node, to_node):
        if not (from_node in edges):
            edges[from_node] = set()
        edges[from_node].add(to_node)








class ExternValue:
    # An external value is the runtime representation of an entity that can be imported or exported. It is an address
    # denoting either a function instance, table instance, memory instance, or global instances in the shared store.
    #
    # externval ::= func funcaddr
    #             | table tableaddr
    #             | mem memaddr
    #             | global globaladdr
    def __init__(self, extern_type: int, addr: int):
        self.extern_type = extern_type
        self.addr = addr

class Value:
    # Values are represented by themselves.
    def __init__(self, valtype: int, n):
        self.valtype = valtype
        self.n = n

    def __repr__(self):
        return str(self.n)

    @classmethod
    def from_i32(cls, n):
        if isSymbolic(n):
            n = simplify(n)
        return Value(wasmConvention.i32, n)

    @classmethod
    def from_i64(cls, n):
        if isSymbolic(n):
            n = simplify(n)
        return Value(wasmConvention.i64, n)

    @classmethod
    def from_f32(cls, n):
        if isSymbolic(n):
            n = simplify(n)
        return Value(wasmConvention.f32, n)

    @classmethod
    def from_f64(cls, n):
        if isSymbolic(n):
            n = simplify(n)
        return Value(wasmConvention.f64, n)

class Label:
    # Labels carry an argument arity n and their associated branch target, which is expressed syntactically as an
    # instruction sequence:
    #
    # label ::= labeln{instr∗}
    #
    # Intuitively, instr∗ is the continuation to execute when the branch is taken, in place of the original control
    # construct.
    def __init__(self, arity: int, continuation: int):
        self.arity = arity
        self.continuation = continuation

    def __repr__(self):
        return '|'

class FunctionInstance:
    # A function instance is the runtime representation of a function. It effectively is a closure of the original
    # function over the runtime module instance of its originating module. The module instance is used to resolve
    # references to other definitions during execution of the function.
    #
    # funcinst ::= {type functype,module moduleinst,code func}
    #            | {type functype,hostcode hostfunc}
    # hostfunc ::= ...
    pass


class WasmFunc(FunctionInstance):
    def __init__(self,
                 functype: wasmModule.FunctionType,
                 module: 'ModuleInstance',
                 code: wasmModule.Function
                 ):
        self.functype = functype
        self.module = module
        self.code = code

    def set_block(self, blocks):
        self.blocks = blocks

    def set_edges(self, edges):
        self.edges = edges


class HostFunc(FunctionInstance):
    # A host function is a function expressed outside WebAssembly but passed to a module as an import. The definition
    # and behavior of host functions are outside the scope of this specification. For the purpose of this
    # specification, it is assumed that when invoked, a host function behaves non-deterministically, but within certain
    # constraints that ensure the integrity of the runtime.
    def __init__(self, functype: wasmModule.FunctionType):
        self.functype = functype
        # self.hostcode = hostcode


class TableInstance:
    # A table instance is the runtime representation of a table. It holds a vector of function elements and an optional
    # maximum size, if one was specified in the table type at the table’s definition site.
    #
    # Each function element is either empty, representing an uninitialized table entry, or a function address. Function
    # elements can be mutated through the execution of an element segment or by external means provided by the embedder.
    #
    # tableinst ::= {elem vec(funcelem), max u32?}
    # funcelem ::= funcaddr?
    #
    # It is an invariant of the semantics that the length of the element vector never exceeds the maximum size, if
    # present.
    def __init__(self, module, name, elemtype: int, limits: wasmModule.Limits):
        self.module = module
        self.name = name
        self.elemtype = elemtype
        self.limits = limits
        self.elem = [None for _ in range(limits.minimum)]
        self.elements = {}

    def copy(self):
        o = TableInstance(self.module, self.name, self.elemtype, self.limits)
        o.elem = list(self.elem)
        o.elements = custom_deepcopy(self.elements)
        return o


class MemoryInstance:
    # A memory instance is the runtime representation of a linear memory. It holds a vector of bytes and an optional
    # maximum size, if one was specified at the definition site of the memory.
    #
    # meminst ::= {data vec(byte), max u32?}
    #
    # The length of the vector always is a multiple of the WebAssembly page size, which is defined to be the constant
    # 65536 – abbreviated 64Ki. Like in a memory type, the maximum size in a memory instance is given in units of this
    # page size.
    #
    # The bytes can be mutated through memory instructions, the execution of a data segment, or by external means
    # provided by the embedder.
    #
    # It is an invariant of the semantics that the length of the byte vector, divided by page size, never exceeds the
    # maximum size, if present.
    def __init__(self, module, name, limits: wasmModule.Limits):
        self.module = module
        self.name = name
        self.limits = limits
        self.size = limits.minimum
        # self.data = {} #for int index {offset:(size, value)}
        self.datas = {} #{root_address:{offset:(size,value)}:

    def grow(self, n: int):
        #todo: check if out of bound
        # if self.limits.maximum and self.size + n > self.limits.maximum:
            #raise Exception('pywasm: out of memory limit')
        # self.data.extend([0 for _ in range(n * 64 * 1024)])
        self.size += n

    def copy(self):
        o = MemoryInstance(self.module, self.name, self.limits)
        #o.data = list(self.data)
        o.datas = custom_deepcopy(self.datas)
        return o


class GlobalInstance:
    # A global instance is the runtime representation of a global variable. It holds an individual value and a flag
    # indicating whether it is mutable.
    #
    # globalinst ::= {value val, mut mut}
    #
    # The value of mutable globals can be mutated through variable instructions or by external means provided by the
    # embedder.
    def __init__(self, value: 'Value', mut: bool):
        self.value = value
        self.mut = mut

    def copy(self):
        o = GlobalInstance(Value(self.value.valtype, self.value.n), self.mut)
        return o


class ExportInstance:
    # An export instance is the runtime representation of an export. It defines the export’s name and the associated
    # external value.
    #
    # exportinst ::= {name name, value externval}
    def __init__(self, name: str, value: 'ExternValue'):
        self.name = name
        self.value = value

class Store:
    # The store represents all global state that can be manipulated by WebAssembly programs. It consists of the runtime
    # representation of all instances of functions, tables, memories, and globals that have been allocated during the
    # life time of the abstract machine
    # Syntactically, the store is defined as a record listing the existing instances of each category:
    # store ::= {
    #     funcs funcinst∗
    #     tables tableinst∗
    #     mems meminst∗
    #     globals globalinst∗
    # }
    #
    # Addresses are dynamic, globally unique references to runtime objects, in contrast to indices, which are static,
    # module-local references to their original definitions. A memory address memaddr denotes the abstract address of
    # a memory instance in the store, not an offset inside a memory instance.
    def __init__(self):
        self.funcs: typing.List[FunctionInstance] = []
        self.tables: typing.List[TableInstance] = []
        self.mems: typing.List[MemoryInstance] = []
        self.globals: typing.List[GlobalInstance] = []

class ExportInstance:
    # An export instance is the runtime representation of an export. It defines the export’s name and the associated
    # external value.
    #
    # exportinst ::= {name name, value externval}
    def __init__(self, name: str, value: 'ExternValue'):
        self.name = name
        self.value = value

class ModuleInstance:
    # A module instance is the runtime representation of a module. It is created by instantiating a module, and
    # collects runtime representations of all entities that are imported, defined, or exported by the module.
    #
    # moduleinst ::= {
    #     types functype∗
    #     funcaddrs funcaddr∗
    #     tableaddrs tableaddr∗
    #     memaddrs memaddr∗
    #     globaladdrs globaladdr∗
    #     exports exportinst∗
    # }
    def __init__(self):
        self.types: typing.List[wasmModule.FunctionType] = []
        self.funcaddrs: typing.List[int] = []
        self.tableaddrs: typing.List[int] = []
        self.memaddrs: typing.List[int] = []
        self.globaladdrs: typing.List[int] = []
        self.exports: typing.List[ExportInstance] = []

    def instantiate(
        self,
        module: wasmModule.Module,
        store: Store,
        externvals: typing.List[ExternValue] = None,
    ):
        self.types = module.types
        # [TODO] If module is not valid, then panic
        # Assert: module is valid with external types classifying its imports
        for e in module.imports:
            assert e.kind in wasmConvention.extern_type
        # Assert: number m of imports is equal to the number n of provided external values
        assert len(module.imports) == len(externvals)
        # Assert: externvals matching imports of module
        for i in range(len(externvals)):
            e = externvals[i]
            assert e.extern_type in wasmConvention.extern_type
            if e.extern_type == wasmConvention.extern_func:
                a = store.funcs[e.addr]
                b = self.types[module.imports[i].desc]
                assert a.functype.args == b.args
                assert a.functype.rets == b.rets
            elif e.extern_type == wasmConvention.extern_table:
                a = store.tables[e.addr]
                b = module.imports[i].desc
                assert a.elemtype == b.elemtype
                assert import_matching_limits(b.limits, a.limits)
            elif e.extern_type == wasmConvention.extern_mem:
                a = store.mems[e.addr]
                b = module.imports[i].desc
                assert import_matching_limits(b, a.limits)
            elif e.extern_type == wasmConvention.extern_global:
                a = store.globals[e.addr]
                b = module.imports[i].desc
                assert a.value.valtype == b.valtype
        # Let vals be the vector of global initialization values determined by module and externvaln
        auxmod = ModuleInstance()
        auxmod.globaladdrs = [e.addr for e in externvals if e.extern_type == wasmConvention.extern_global]
        stack = Stack()
        frame = Frame(auxmod, [], 1, -1)
        stack.add(frame)
        vals = []
        for glob in module.globals:
            v = exec_expr(store, frame, stack, glob.expr)[0]
            vals.append(v)
        assert isinstance(stack.pop(), Frame)

        # Allocation
        self.allocate(module, store, externvals, vals)

        # Push the frame F to the stack
        frame = Frame(self, [], 1, -1)
        stack.add(frame)
        # For each element segment in module.elem, do:
        for e in module.elem:
            #TODO
            offset = exec_expr(store, frame, stack, e.expr)[0]
            # assert offset.valtype == wasmConvention.i32
            # offset = Value(wasmConvention.i32, 0)

            t = store.tables[self.tableaddrs[e.tableidx]]
            for i, e in enumerate(e.init):
                if isinstance(offset.n, int):
                    t.elements[offset.n + i] = e
                else:
                    key = str(simplify(offset.n + i))
                    t.elements[key] = e
        # For each data segment in module.data, do:
        for e in module.data:
            #TODO
            offset = exec_expr(store, frame, stack, e.expr)[0]
            #assert offset.valtype == wasmConvention.i32
            # offset = Value(wasmConvention.i32, 0)
            if isinstance(offset.n, int):
                m = store.mems[self.memaddrs[e.memidx]]
                m.datas[0] = {}
                m.datas[0][offset.n] =  (len(e.init), e.init)
            else:
                m.datas[str(offset.n)] = {}
                m.datas[str(offset.n)][0] = (len(e.init), e.init)

        # Assert: due to validation, the frame F is now on the top of the stack.
        assert isinstance(stack.pop(), Frame)
        assert stack.len() == 0
        # If the start function module.start is not empty, invoke the function instance
        if module.start is not None:
            log.debugln(f'Running start function {module.start}:')
            # call(self, module.start, store, stack)

    def allocate(
        self,
        module: wasmModule.Module,
        store: Store,
        externvals: typing.List[ExternValue],
        vals: typing.List[Value],
    ):
        self.types = module.types
        # Imports
        self.funcaddrs.extend([e.addr for e in externvals if e.extern_type == wasmConvention.extern_func])
        self.tableaddrs.extend([e.addr for e in externvals if e.extern_type == wasmConvention.extern_table])
        self.memaddrs.extend([e.addr for e in externvals if e.extern_type == wasmConvention.extern_mem])
        self.globaladdrs.extend([e.addr for e in externvals if e.extern_type == wasmConvention.extern_global])
        # For each function func in module.funcs, do:
        for func in module.funcs:
            functype = self.types[func.typeidx]
            funcinst = WasmFunc(functype, self, func)
            store.funcs.append(funcinst)
            self.funcaddrs.append(len(store.funcs) - 1)
        # For each table in module.tables, do:
        for table in module.tables:
            tabletype = table.tabletype
            elemtype = tabletype.elemtype
            tableinst = TableInstance(elemtype, tabletype.limits)
            store.tables.append(tableinst)
            self.tableaddrs.append(len(store.tables) - 1)
        # For each memory module.mems, do:
        for mem in module.mems:
            meminst = MemoryInstance(mem.memtype)
            store.mems.append(meminst)
            self.memaddrs.append(len(store.mems) - 1)
        # For each global in module.globals, do:
        for i, glob in enumerate(module.globals):
            val = vals[i]
            if val.valtype != glob.globaltype.valtype:
                raise Exception('pywasm: mismatch valtype')
            globalinst = GlobalInstance(val, glob.globaltype.mut)
            store.globals.append(globalinst)
            self.globaladdrs.append(len(store.globals) - 1)
        # For each export in module.exports, do:
        for i, export in enumerate(module.exports):
            externval = ExternValue(export.kind, export.desc)
            exportinst = ExportInstance(export.name, externval)
            self.exports.append(exportinst)

class Frame:
    # Activation frames carry the return arity of the respective function, hold the values of its locals (including
    # arguments) in the order corresponding to their static local indices, and a reference to the function’s own module
    # instance:
    #
    # activation ::= framen{frame}
    # frame ::= {locals val∗, module moduleinst}
    def __init__(self, module: '', locs: typing.List[Value], arity: int, continuation: int):
        self.module = module
        self.locals = locs
        self.arity = arity
        self.continuation = continuation

    def __repr__(self):
        return '*'

    def copy(self):
        o = Frame(self.module, list(self.locals), self.arity, self.continuation)
        return o

class Stack:
    # Besides the store, most instructions interact with an implicit stack. The stack contains three kinds of entries:
    #
    # Values: the operands of instructions.
    # Labels: active structured control instructions that can be targeted by branches.
    # Activations: the call frames of active function calls.
    #
    # These entries can occur on the stack in any order during the execution of a program. Stack entries are described
    # by abstract syntax as follows.
    def __init__(self):
        self.data = []

    def __repr__(self):
        return self.data.__repr__()

    def copy(self):
        o = Stack()
        o.data = []
        for e in self.data:
            if isinstance(e, Value):
                o.data.append(e)
            elif isinstance(e, Frame):
                o.data.append(e.copy())
            else:
                raise("unkonw element type in stack")


    def add(self, e):
        self.data.append(e)

    def ext(self, e: typing.List):
        for i in e:
            self.add(i)

    def pop(self):
        return self.data.pop()

    def len(self):
        return len(self.data)

    def top(self):
        return self.data[-1]

    def status(self):
        for i in range(len(self.data)):
            i = -1 - i
            if isinstance(self.data[i], Label):
                return Label
            if isinstance(self.data[i], Frame):
                return Frame
#

def import_matching_limits(limits1: wasmModule.Limits, limits2: wasmModule.Limits):
    n1 = limits1.minimum
    m1 = limits1.maximum
    n2 = limits2.minimum
    m2 = limits2.maximum
    if m2 is None or (m1 is not None and m1 <= m2):
        return True
    return False

def exec_expr(
    store: Store,
    frame: Frame,
    stack: Stack,
    expr: wasmModule.Expression,
):
    module = frame.module
    if not expr.data:
        raise Exception('pywasm: empty init expr')
    pc = -1
    while True:
        pc += 1
        if pc >= len(expr.data):
            break
        i = expr.data[pc]

        log.debugln(f'{str(i):<18} {stack}')

        if log.lvl >= 2:
            ls = [f'{i}: {wasmConvention.valtype[l.valtype][0]} {l.n}' for i, l in enumerate(frame.locals)]
            gs = [f'{i}: {"mut " if g.mut else ""}{wasmConvention.valtype[g.value.valtype][0]} {g.value.n}' for i,
                                                                                                            g in
                  enumerate(store.globals)]
            for n, e in (('locals', ls), ('globals', gs)):
                log.verboseln(f'{" " * 18} {str(n) + ":":<8} [{", ".join(e)}]')

        opcode = i.code

        if opcode == wasmConvention.get_global:
            stack.add(store.globals[module.globaladdrs[i.immediate_arguments]].value)
            continue
        if opcode >= wasmConvention.i32_const and opcode <= wasmConvention.f64_const:
            if opcode == wasmConvention.i32_const:
                stack.add(Value.from_i32(i.immediate_arguments))
                continue
            if opcode == wasmConvention.i64_const:
                stack.add(Value.from_i64(i.immediate_arguments))
                continue
            if opcode == wasmConvention.f32_const:
                stack.add(Value.from_f32(i.immediate_arguments))
                continue
            if opcode == wasmConvention.f64_const:
                stack.add(Value.from_f64(i.immediate_arguments))
                continue
            continue

    return [stack.pop() for _ in range(frame.arity)][::-1]
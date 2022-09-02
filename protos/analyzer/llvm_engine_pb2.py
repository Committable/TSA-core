# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: protos/analyzer/llvm_engine.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from protos.analyzer import bytecode_analyzer_pb2 as protos_dot_analyzer_dot_bytecode__analyzer__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='protos/analyzer/llvm_engine.proto',
  package='analyzer',
  syntax='proto3',
  serialized_options=b'Z\032protobuf/analyzer;analyzer',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n!protos/analyzer/llvm_engine.proto\x12\x08\x61nalyzer\x1a\'protos/analyzer/bytecode_analyzer.proto2f\n\nLLVMEngine\x12X\n\x0f\x41nalyseByteCode\x12!.analyzer.ByteCodeAnalysisRequest\x1a\".analyzer.ByteCodeAnalysisResponseB\x1cZ\x1aprotobuf/analyzer;analyzerb\x06proto3'
  ,
  dependencies=[protos_dot_analyzer_dot_bytecode__analyzer__pb2.DESCRIPTOR,])



_sym_db.RegisterFileDescriptor(DESCRIPTOR)


DESCRIPTOR._options = None

_LLVMENGINE = _descriptor.ServiceDescriptor(
  name='LLVMEngine',
  full_name='analyzer.LLVMEngine',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=88,
  serialized_end=190,
  methods=[
  _descriptor.MethodDescriptor(
    name='AnalyseByteCode',
    full_name='analyzer.LLVMEngine.AnalyseByteCode',
    index=0,
    containing_service=None,
    input_type=protos_dot_analyzer_dot_bytecode__analyzer__pb2._BYTECODEANALYSISREQUEST,
    output_type=protos_dot_analyzer_dot_bytecode__analyzer__pb2._BYTECODEANALYSISRESPONSE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_LLVMENGINE)

DESCRIPTOR.services_by_name['LLVMEngine'] = _LLVMENGINE

# @@protoc_insertion_point(module_scope)
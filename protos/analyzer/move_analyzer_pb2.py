# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: protos/analyzer/move_analyzer.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from protos.analyzer import source_code_analyzer_pb2 as protos_dot_analyzer_dot_source__code__analyzer__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='protos/analyzer/move_analyzer.proto',
  package='analyzer',
  syntax='proto3',
  serialized_pb=_b('\n#protos/analyzer/move_analyzer.proto\x12\x08\x61nalyzer\x1a*protos/analyzer/source_code_analyzer.proto2x\n\x16MoveSourceCodeAnalysis\x12^\n\x11\x41nalyseSourceCode\x12#.analyzer.SourceCodeAnalysisRequest\x1a$.analyzer.SourceCodeAnalysisResponseB\x1cZ\x1aprotobuf/analyzer;analyzerb\x06proto3')
  ,
  dependencies=[protos_dot_analyzer_dot_source__code__analyzer__pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)





DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), _b('Z\032protobuf/analyzer;analyzer'))
# @@protoc_insertion_point(module_scope)
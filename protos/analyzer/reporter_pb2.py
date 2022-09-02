# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: protos/analyzer/reporter.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='protos/analyzer/reporter.proto',
  package='analyzer',
  syntax='proto3',
  serialized_options=b'Z\032protobuf/analyzer;analyzer',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x1eprotos/analyzer/reporter.proto\x12\x08\x61nalyzer\"\x8a\x01\n\x0f\x41nalysisRequest\x12/\n\rbefore_change\x18\x01 \x01(\x0b\x32\x18.analyzer.AnalysisTarget\x12.\n\x0c\x61\x66ter_change\x18\x02 \x01(\x0b\x32\x18.analyzer.AnalysisTarget\x12\x16\n\x0e\x64iffs_log_path\x18\x03 \x01(\t\"\xd0\x01\n\x10\x41nalysisResponse\x12\x0e\n\x06status\x18\x01 \x01(\x05\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x33\n\x10structure_report\x18\x03 \x01(\x0b\x32\x19.analyzer.StructureReport\x12\x33\n\x10semantics_report\x18\x04 \x01(\x0b\x32\x19.analyzer.SemanticsReport\x12\x31\n\x0f\x61\x62stract_report\x18\x05 \x01(\x0b\x32\x18.analyzer.AbstractReport\"6\n\x0e\x41nalysisTarget\x12\x11\n\trepo_path\x18\x01 \x01(\t\x12\x11\n\tfile_path\x18\x02 \x01(\t\"\x81\x02\n\x0fStructureReport\x12\x17\n\x0f\x61st_before_path\x18\x01 \x01(\t\x12\x16\n\x0e\x61st_after_path\x18\x02 \x01(\t\x12\x17\n\x0f\x63\x66g_before_path\x18\x03 \x01(\t\x12\x16\n\x0e\x63\x66g_after_path\x18\x04 \x01(\t\x12\"\n\x1a\x61st_edge_lists_before_path\x18\x05 \x01(\t\x12!\n\x19\x61st_edge_lists_after_path\x18\x06 \x01(\t\x12\"\n\x1a\x63\x66g_edge_lists_before_path\x18\x07 \x01(\t\x12!\n\x19\x63\x66g_edge_lists_after_path\x18\x08 \x01(\t\"\x89\x01\n\x0fSemanticsReport\x12\x17\n\x0fssg_before_path\x18\x01 \x01(\t\x12\x16\n\x0essg_after_path\x18\x02 \x01(\t\x12\"\n\x1assg_edge_lists_before_path\x18\x03 \x01(\t\x12!\n\x19ssg_edge_lists_after_path\x18\x04 \x01(\t\"*\n\x0e\x41\x62stractReport\x12\x18\n\x10meta_commit_path\x18\x01 \x01(\t\"\x07\n\x05\x45mpty2\xf5\x01\n\x08\x41nalysis\x12\x43\n\nGetReports\x12\x19.analyzer.AnalysisRequest\x1a\x1a.analyzer.AnalysisResponse\x12\x36\n\x12GetStructureReport\x12\x0f.analyzer.Empty\x1a\x0f.analyzer.Empty\x12\x35\n\x11GetSemanticReport\x12\x0f.analyzer.Empty\x1a\x0f.analyzer.Empty\x12\x35\n\x11GetAbstractReport\x12\x0f.analyzer.Empty\x1a\x0f.analyzer.EmptyB\x1cZ\x1aprotobuf/analyzer;analyzerb\x06proto3'
)




_ANALYSISREQUEST = _descriptor.Descriptor(
  name='AnalysisRequest',
  full_name='analyzer.AnalysisRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='before_change', full_name='analyzer.AnalysisRequest.before_change', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='after_change', full_name='analyzer.AnalysisRequest.after_change', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='diffs_log_path', full_name='analyzer.AnalysisRequest.diffs_log_path', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=45,
  serialized_end=183,
)


_ANALYSISRESPONSE = _descriptor.Descriptor(
  name='AnalysisResponse',
  full_name='analyzer.AnalysisResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='analyzer.AnalysisResponse.status', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='message', full_name='analyzer.AnalysisResponse.message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='structure_report', full_name='analyzer.AnalysisResponse.structure_report', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='semantics_report', full_name='analyzer.AnalysisResponse.semantics_report', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='abstract_report', full_name='analyzer.AnalysisResponse.abstract_report', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=186,
  serialized_end=394,
)


_ANALYSISTARGET = _descriptor.Descriptor(
  name='AnalysisTarget',
  full_name='analyzer.AnalysisTarget',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='repo_path', full_name='analyzer.AnalysisTarget.repo_path', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='file_path', full_name='analyzer.AnalysisTarget.file_path', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=396,
  serialized_end=450,
)


_STRUCTUREREPORT = _descriptor.Descriptor(
  name='StructureReport',
  full_name='analyzer.StructureReport',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ast_before_path', full_name='analyzer.StructureReport.ast_before_path', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ast_after_path', full_name='analyzer.StructureReport.ast_after_path', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cfg_before_path', full_name='analyzer.StructureReport.cfg_before_path', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cfg_after_path', full_name='analyzer.StructureReport.cfg_after_path', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ast_edge_lists_before_path', full_name='analyzer.StructureReport.ast_edge_lists_before_path', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ast_edge_lists_after_path', full_name='analyzer.StructureReport.ast_edge_lists_after_path', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cfg_edge_lists_before_path', full_name='analyzer.StructureReport.cfg_edge_lists_before_path', index=6,
      number=7, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cfg_edge_lists_after_path', full_name='analyzer.StructureReport.cfg_edge_lists_after_path', index=7,
      number=8, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=453,
  serialized_end=710,
)


_SEMANTICSREPORT = _descriptor.Descriptor(
  name='SemanticsReport',
  full_name='analyzer.SemanticsReport',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ssg_before_path', full_name='analyzer.SemanticsReport.ssg_before_path', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ssg_after_path', full_name='analyzer.SemanticsReport.ssg_after_path', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ssg_edge_lists_before_path', full_name='analyzer.SemanticsReport.ssg_edge_lists_before_path', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='ssg_edge_lists_after_path', full_name='analyzer.SemanticsReport.ssg_edge_lists_after_path', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=713,
  serialized_end=850,
)


_ABSTRACTREPORT = _descriptor.Descriptor(
  name='AbstractReport',
  full_name='analyzer.AbstractReport',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='meta_commit_path', full_name='analyzer.AbstractReport.meta_commit_path', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=852,
  serialized_end=894,
)


_EMPTY = _descriptor.Descriptor(
  name='Empty',
  full_name='analyzer.Empty',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=896,
  serialized_end=903,
)

_ANALYSISREQUEST.fields_by_name['before_change'].message_type = _ANALYSISTARGET
_ANALYSISREQUEST.fields_by_name['after_change'].message_type = _ANALYSISTARGET
_ANALYSISRESPONSE.fields_by_name['structure_report'].message_type = _STRUCTUREREPORT
_ANALYSISRESPONSE.fields_by_name['semantics_report'].message_type = _SEMANTICSREPORT
_ANALYSISRESPONSE.fields_by_name['abstract_report'].message_type = _ABSTRACTREPORT
DESCRIPTOR.message_types_by_name['AnalysisRequest'] = _ANALYSISREQUEST
DESCRIPTOR.message_types_by_name['AnalysisResponse'] = _ANALYSISRESPONSE
DESCRIPTOR.message_types_by_name['AnalysisTarget'] = _ANALYSISTARGET
DESCRIPTOR.message_types_by_name['StructureReport'] = _STRUCTUREREPORT
DESCRIPTOR.message_types_by_name['SemanticsReport'] = _SEMANTICSREPORT
DESCRIPTOR.message_types_by_name['AbstractReport'] = _ABSTRACTREPORT
DESCRIPTOR.message_types_by_name['Empty'] = _EMPTY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

AnalysisRequest = _reflection.GeneratedProtocolMessageType('AnalysisRequest', (_message.Message,), {
  'DESCRIPTOR' : _ANALYSISREQUEST,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.AnalysisRequest)
  })
_sym_db.RegisterMessage(AnalysisRequest)

AnalysisResponse = _reflection.GeneratedProtocolMessageType('AnalysisResponse', (_message.Message,), {
  'DESCRIPTOR' : _ANALYSISRESPONSE,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.AnalysisResponse)
  })
_sym_db.RegisterMessage(AnalysisResponse)

AnalysisTarget = _reflection.GeneratedProtocolMessageType('AnalysisTarget', (_message.Message,), {
  'DESCRIPTOR' : _ANALYSISTARGET,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.AnalysisTarget)
  })
_sym_db.RegisterMessage(AnalysisTarget)

StructureReport = _reflection.GeneratedProtocolMessageType('StructureReport', (_message.Message,), {
  'DESCRIPTOR' : _STRUCTUREREPORT,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.StructureReport)
  })
_sym_db.RegisterMessage(StructureReport)

SemanticsReport = _reflection.GeneratedProtocolMessageType('SemanticsReport', (_message.Message,), {
  'DESCRIPTOR' : _SEMANTICSREPORT,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.SemanticsReport)
  })
_sym_db.RegisterMessage(SemanticsReport)

AbstractReport = _reflection.GeneratedProtocolMessageType('AbstractReport', (_message.Message,), {
  'DESCRIPTOR' : _ABSTRACTREPORT,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.AbstractReport)
  })
_sym_db.RegisterMessage(AbstractReport)

Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), {
  'DESCRIPTOR' : _EMPTY,
  '__module__' : 'protos.analyzer.reporter_pb2'
  # @@protoc_insertion_point(class_scope:analyzer.Empty)
  })
_sym_db.RegisterMessage(Empty)


DESCRIPTOR._options = None

_ANALYSIS = _descriptor.ServiceDescriptor(
  name='Analysis',
  full_name='analyzer.Analysis',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=906,
  serialized_end=1151,
  methods=[
  _descriptor.MethodDescriptor(
    name='GetReports',
    full_name='analyzer.Analysis.GetReports',
    index=0,
    containing_service=None,
    input_type=_ANALYSISREQUEST,
    output_type=_ANALYSISRESPONSE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetStructureReport',
    full_name='analyzer.Analysis.GetStructureReport',
    index=1,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetSemanticReport',
    full_name='analyzer.Analysis.GetSemanticReport',
    index=2,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetAbstractReport',
    full_name='analyzer.Analysis.GetAbstractReport',
    index=3,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_ANALYSIS)

DESCRIPTOR.services_by_name['Analysis'] = _ANALYSIS

# @@protoc_insertion_point(module_scope)
// Code generated by protoc-gen-go. DO NOT EDIT.
// source: protos/analyzer/js_analyzer.proto

package analyzer // import "protobuf/analyzer"

import proto "github.com/golang/protobuf/proto"
import fmt "fmt"
import math "math"

import (
	context "golang.org/x/net/context"
	grpc "google.golang.org/grpc"
)

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = fmt.Errorf
var _ = math.Inf

// This is a compile-time assertion to ensure that this generated file
// is compatible with the proto package it is being compiled against.
// A compilation error at this line likely means your copy of the
// proto package needs to be updated.
const _ = proto.ProtoPackageIsVersion2 // please upgrade the proto package

// Reference imports to suppress errors if they are not otherwise used.
var _ context.Context
var _ grpc.ClientConn

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
const _ = grpc.SupportPackageIsVersion4

// JsSourceCodeAnalysisClient is the client API for JsSourceCodeAnalysis service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://godoc.org/google.golang.org/grpc#ClientConn.NewStream.
type JsSourceCodeAnalysisClient interface {
	AnalyseSourceCode(ctx context.Context, in *SourceCodeAnalysisRequest, opts ...grpc.CallOption) (*SourceCodeAnalysisResponse, error)
}

type jsSourceCodeAnalysisClient struct {
	cc *grpc.ClientConn
}

func NewJsSourceCodeAnalysisClient(cc *grpc.ClientConn) JsSourceCodeAnalysisClient {
	return &jsSourceCodeAnalysisClient{cc}
}

func (c *jsSourceCodeAnalysisClient) AnalyseSourceCode(ctx context.Context, in *SourceCodeAnalysisRequest, opts ...grpc.CallOption) (*SourceCodeAnalysisResponse, error) {
	out := new(SourceCodeAnalysisResponse)
	err := c.cc.Invoke(ctx, "/analyzer.JsSourceCodeAnalysis/AnalyseSourceCode", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// JsSourceCodeAnalysisServer is the server API for JsSourceCodeAnalysis service.
type JsSourceCodeAnalysisServer interface {
	AnalyseSourceCode(context.Context, *SourceCodeAnalysisRequest) (*SourceCodeAnalysisResponse, error)
}

func RegisterJsSourceCodeAnalysisServer(s *grpc.Server, srv JsSourceCodeAnalysisServer) {
	s.RegisterService(&_JsSourceCodeAnalysis_serviceDesc, srv)
}

func _JsSourceCodeAnalysis_AnalyseSourceCode_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(SourceCodeAnalysisRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(JsSourceCodeAnalysisServer).AnalyseSourceCode(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/analyzer.JsSourceCodeAnalysis/AnalyseSourceCode",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(JsSourceCodeAnalysisServer).AnalyseSourceCode(ctx, req.(*SourceCodeAnalysisRequest))
	}
	return interceptor(ctx, in, info, handler)
}

var _JsSourceCodeAnalysis_serviceDesc = grpc.ServiceDesc{
	ServiceName: "analyzer.JsSourceCodeAnalysis",
	HandlerType: (*JsSourceCodeAnalysisServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "AnalyseSourceCode",
			Handler:    _JsSourceCodeAnalysis_AnalyseSourceCode_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "protos/analyzer/js_analyzer.proto",
}

func init() {
	proto.RegisterFile("protos/analyzer/js_analyzer.proto", fileDescriptor_js_analyzer_60fae805aa5cc2d8)
}

var fileDescriptor_js_analyzer_60fae805aa5cc2d8 = []byte{
	// 142 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff, 0xe2, 0x52, 0x2c, 0x28, 0xca, 0x2f,
	0xc9, 0x2f, 0xd6, 0x4f, 0xcc, 0x4b, 0xcc, 0xa9, 0xac, 0x4a, 0x2d, 0xd2, 0xcf, 0x2a, 0x8e, 0x87,
	0xb1, 0xf5, 0xc0, 0x72, 0x42, 0x1c, 0x30, 0xbe, 0x94, 0x16, 0xba, 0xe2, 0xe2, 0xfc, 0xd2, 0xa2,
	0xe4, 0xd4, 0xf8, 0xe4, 0xfc, 0x94, 0x54, 0x34, 0x5d, 0x46, 0x65, 0x5c, 0x22, 0x5e, 0xc5, 0xc1,
	0x60, 0x79, 0xe7, 0xfc, 0x94, 0x54, 0x47, 0x90, 0x6c, 0x71, 0x66, 0xb1, 0x50, 0x1c, 0x97, 0x20,
	0x84, 0x9d, 0x8a, 0x90, 0x14, 0x52, 0xd6, 0x83, 0xeb, 0xc6, 0xd4, 0x12, 0x94, 0x5a, 0x58, 0x9a,
	0x5a, 0x5c, 0x22, 0xa5, 0x82, 0x5f, 0x51, 0x71, 0x41, 0x7e, 0x5e, 0x71, 0xaa, 0x93, 0x4c, 0x94,
	0x14, 0xd8, 0x01, 0x49, 0xa5, 0x69, 0x70, 0x77, 0x5a, 0xc3, 0x18, 0x49, 0x6c, 0x60, 0x39, 0x63,
	0x40, 0x00, 0x00, 0x00, 0xff, 0xff, 0x70, 0xb5, 0xf8, 0xeb, 0xf7, 0x00, 0x00, 0x00,
}

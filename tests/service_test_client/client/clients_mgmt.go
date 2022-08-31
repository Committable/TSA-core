package client

import (
	"github.com/pkg/errors"
	pb "service_test/protos/analyzer"
)

type SourceType int32

const (
	CCPP     SourceType = 0
	SOLIDITY SourceType = 1
	RUST     SourceType = 2
	GO       SourceType = 3
	UNKNOWN  SourceType = -1
	EVM      SourceType = 4
	LLVMIR   SourceType = 5
	MD       SourceType = 6
)

type SrcClient interface {
	Analyse(before, after *pb.AnalysisTarget, diff string) (*pb.SourceCodeAnalysisResponse, error)
	Close()
	IsOk() bool
}

type BytecodeClient interface {
	Analyse(before, after *pb.AnalysisTarget, diff string) (*pb.ByteCodeAnalysisResponse, error)
	Close()
	IsOk() bool
}

type ClientsMgr struct {
	srcClients      map[SourceType]SrcClient
	bytecodeClients map[SourceType]BytecodeClient
	handlerClient *HandlerClient
}

func NewClientMgr() *ClientsMgr {
	return &ClientsMgr{srcClients: make(map[SourceType]SrcClient),
		bytecodeClients: make(map[SourceType]BytecodeClient)}
}

func (mgr *ClientsMgr) GetSrcClient(fileType SourceType, address string, timeout int) (SrcClient, error) {
	var client SrcClient
	var err error

	if _, ok := mgr.srcClients[fileType]; ok {
		if mgr.srcClients[fileType].IsOk() {
			return mgr.srcClients[fileType], nil
		}
	}

	switch fileType {
	case CCPP:
		client, err = NewCppClient(address, timeout)
		if err != nil {
			return nil, err
		}
	case SOLIDITY:
		client, err = NewSolidityClient(address, timeout)
		if err != nil {
			return nil, err
		}
	case RUST:
		client, err = NewRustClient(address, timeout)
		if err != nil {
			return nil, err
		}
	case GO:
		client, err = NewGoClient(address, timeout)
		if err != nil {
			return nil, err
		}
	case MD:
		client, err = NewMdClient(address, timeout)
	default:
		return nil, errors.Errorf("unknown source file type %d", fileType)

	}
	mgr.srcClients[fileType] = client
	return client, nil
}

func (mgr *ClientsMgr) GetBytecodeClient(fileType SourceType, address string, timeout int) (BytecodeClient, error) {
	var client BytecodeClient
	var err error

	if _, ok := mgr.bytecodeClients[fileType]; ok {
		if mgr.bytecodeClients[fileType].IsOk() {
			return mgr.bytecodeClients[fileType], nil
		}
	}

	switch fileType {
	case EVM:
		client, err = NewEvmClient(address, timeout)
		if err != nil {
			return nil, err
		}
	case LLVMIR:
		client, err = NewLlvmClient(address, timeout)
		if err != nil {
			return nil, err
		}
	default:
		return nil, errors.Errorf("unknown bytecode file type %d", fileType)

	}
	mgr.bytecodeClients[fileType] = client
	return client, nil
}

func (mgr *ClientsMgr) GetHandlerClient(address string, timeout int) (*HandlerClient, error) {
	var client *HandlerClient
	var err error

	if mgr.handlerClient != nil {
		if mgr.handlerClient.IsOk() {
			return mgr.handlerClient, nil
		}
	}

	client, err = NewHandlerClient(address, timeout)
	if err != nil {
		return nil, err
	}

	mgr.handlerClient = client
	return client, nil
}

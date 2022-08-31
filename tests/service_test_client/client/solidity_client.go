package client

import (
	"log"
	"time"

	"golang.org/x/net/context"
	// 导入grpc包
	"google.golang.org/grpc"
	// 导入刚才我们生成的代码所在的proto包。
	pb "service_test/protos/analyzer"
)

type SolidityClient struct {
	conn     *grpc.ClientConn
	endpoint string
	client   pb.SoliditySourceCodeAnalysisClient
	timeout int

	status bool
}

func NewSolidityClient(endpoint string, timeout int) (*SolidityClient, error) {
	// 连接grpc服务器
	conn, err := grpc.Dial(endpoint, grpc.WithInsecure())
	if err != nil {
		log.Fatalf("did not connect: %v", err)
		return nil, err
	}

	// 初始化Greeter服务客户端
	c := pb.NewSoliditySourceCodeAnalysisClient(conn)

	client := &SolidityClient{
		conn:     conn,
		endpoint: endpoint,
		client:   c,
		timeout: timeout,
		status:   true,
	}

	return client, nil
}

func (client *SolidityClient) Close() {
	// 延迟关闭连接
	client.conn.Close()
	client.status = false
	log.Printf("close client %s", client.endpoint)
}

func (client *SolidityClient) Analyse(before, after *pb.AnalysisTarget, diff string) (*pb.SourceCodeAnalysisResponse, error) {
	// 初始化上下文，设置请求超时时间为1秒
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(client.timeout)*time.Second)
	// 延迟关闭请求会话
	defer cancel()

	// 调用SayHello接口，发送一条消息
	r, err := client.client.AnalyseSourceCode(ctx, &pb.SourceCodeAnalysisRequest{BeforeChange: before, AfterChange: after, DiffsLogPath: diff})
	if err != nil{
		client.Close()
	}
	return r, err
}

func (client *SolidityClient) IsOk() bool{
	return client.status
}

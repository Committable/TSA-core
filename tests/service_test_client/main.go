package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/go-git/go-git/v5/plumbing"

	cl "service_test/client"
	"service_test/config"

	"github.com/go-git/go-git/v5"
	"github.com/xuri/excelize/v2"

	// 导入刚才我们生成的代码所在的proto包。
	pb "service_test/protos/analyzer"
)

var conf = config.GetConf("./config.yaml")

var SUFFIX2TYPE = map[string]cl.SourceType{
	"cpp": cl.CCPP,
	"c":   cl.CCPP,
	"h":   cl.CCPP,
	"hpp": cl.CCPP,

	"sol": cl.SOLIDITY,

	".rs": cl.RUST,

	".go": cl.GO,
	".md": cl.MD,
}

var TYPE2CONF = map[cl.SourceType]config.ServiceConf{
	cl.CCPP:     conf.CCppService,
	cl.SOLIDITY: conf.SolidityService,
	cl.RUST:     conf.RustService,
	cl.GO:       conf.GoService,
	cl.EVM:      conf.EvmService,
	cl.LLVMIR:   conf.LlvmService,
	cl.MD:       conf.MdService,
}

var SOURCE2BYTECODE = map[cl.SourceType]cl.SourceType{
	cl.CCPP:     cl.LLVMIR,
	cl.SOLIDITY: cl.EVM,
}

type Result struct {
	Total   int
	Success int
	Fail    int
	Detail  map[string]string
}

type Response struct {
	row int
	err error
}

type Abstract struct {
	DataFlow     int `json:"data_flow"`
	ControlFlow  int `json:"control_flow"`
	LoopBin      int `json:"loop_bin"`
	LoopSrc      int `json:"loop_src"`
	SequenceBin  int `json:"sequence_bin"`
	SequenceSrc  int `json:"sequence_src"`
	SelectionBin int `json:"selection_bin"`
	SelectionSrc int `json:"selection_src"`
}

type MetaCommit struct {
	Basic Basic `json:"basic"`
}

type Basic struct {
	Files []CommitFile `json:"files"`
}

type CommitFile struct {
	ModifyMode string     `json:"modify_mode"`
	Language   string     `json:"language"`
	Before     ChangeFile `json:"before"`
	After      ChangeFile `json:"after"`
}

type ChangeFile struct {
	Hash   string `json:"hash"`
	Path   string `json:"path"`
	GitUrl string `json:"git_url"`
}

func analyze_go(mgr *cl.ClientsMgr, beforeChange, afterChange *pb.AnalysisTarget, diffs, timestamp string) (*pb.SourceCodeAnalysisResponse, error) {
	// 连接grpc服务器
	log.Printf("start analyse at %s", timestamp)
	sourceClient, err := mgr.GetSrcClient(cl.GO, TYPE2CONF[cl.GO].Address, TYPE2CONF[cl.GO].Timeout)
	if err != nil {
		log.Printf("get source client fail: %v", err)
		return nil, err
	}
	log.Printf("get source client[%s] success for %s", TYPE2CONF[cl.GO].Address, timestamp)
	// 3. calling client rpc service to analyze source file
	sourceResult, err := sourceClient.Analyse(beforeChange, afterChange, diffs)
	if err != nil {
		log.Printf("call source client err: %v", err)
		return nil, err
	}
	log.Printf("analyse source success for %s, source_result=%+v", timestamp, sourceResult)
	return sourceResult, nil
}

func analyze_all(mgr *cl.ClientsMgr, beforeChange, afterChange *pb.AnalysisTarget, diffs, timestamp string) (*pb.AnalysisResponse, error) {
	// 连接grpc服务器
	log.Printf("start analyse at %s", timestamp)
	handlerClient, err := mgr.GetHandlerClient(conf.HandlerService.Address, conf.HandlerService.Timeout)
	if err != nil {
		log.Printf("get source client fail: %v", err)
		return nil, err
	}
	log.Printf("get handler client[%s] success for %s", conf.HandlerService.Address, timestamp)
	// 3. calling client rpc service to analyze source file
	result, err := handlerClient.Analyse(beforeChange, afterChange, diffs)
	if err != nil {
		log.Printf("call source client err: %v", err)
		return nil, err
	}
	log.Printf("analyse source success for %s, source_result=%+v", timestamp, result)
	return result, nil
}

func analyze_markdown(mgr *cl.ClientsMgr, beforeChange, afterChange *pb.AnalysisTarget, diffs, timestamp string) (*pb.SourceCodeAnalysisResponse, error) {
	// 连接grpc服务器
	log.Printf("start analyse at %s", timestamp)
	sourceClient, err := mgr.GetSrcClient(cl.MD, TYPE2CONF[cl.MD].Address, TYPE2CONF[cl.MD].Timeout)
	if err != nil {
		log.Printf("get source client fail: %v", err)
		return nil, err
	}
	log.Printf("get source client[%s] success for %s", TYPE2CONF[cl.MD].Address, timestamp)
	// 3. calling client rpc service to analyze source file
	sourceResult, err := sourceClient.Analyse(beforeChange, afterChange, diffs)
	if err != nil {
		log.Printf("call source client err: %v", err)
		return nil, err
	}
	log.Printf("analyse source success for %s, source_result=%+v", timestamp, sourceResult)
	return sourceResult, nil
}

func analyze_solidity(mgr *cl.ClientsMgr, beforeChange, afterChange *pb.AnalysisTarget, diffs, timestamp string) (*pb.SourceCodeAnalysisResponse, error) {
	// 连接grpc服务器
	log.Printf("start analyse at %s", timestamp)
	sourceClient, err := mgr.GetSrcClient(cl.SOLIDITY, TYPE2CONF[cl.SOLIDITY].Address, TYPE2CONF[cl.SOLIDITY].Timeout)
	if err != nil {
		log.Printf("get source client fail: %v", err)
		return nil, err
	}
	log.Printf("get source client[%s] success for %s", TYPE2CONF[cl.SOLIDITY].Address, timestamp)
	// 3. calling client rpc service to analyze source file
	sourceResult, err := sourceClient.Analyse(beforeChange, afterChange, diffs)
	if err != nil {
		log.Printf("call source client err: %v", err)
		return nil, err
	}
	log.Printf("analyse source success for %s, source_result=%+v", timestamp, sourceResult)
	return sourceResult, nil
}

func analyze_evm(mgr *cl.ClientsMgr, beforeChange, afterChange *pb.AnalysisTarget, diffs, timestamp string) (*pb.ByteCodeAnalysisResponse, error) {
	log.Printf("start analyse at %s", timestamp)

	bytecodeClient, err := mgr.GetBytecodeClient(SOURCE2BYTECODE[cl.SOLIDITY],
		TYPE2CONF[SOURCE2BYTECODE[cl.SOLIDITY]].Address,
		TYPE2CONF[SOURCE2BYTECODE[cl.SOLIDITY]].Timeout)
	if err != nil {
		log.Printf("get bytecode client fail: %v", err)
		return nil, err
	}
	log.Printf("get bytecode client[%s] success for %s", TYPE2CONF[SOURCE2BYTECODE[cl.SOLIDITY]].Address, timestamp)

	// 6. calling client rpc service to analyze bytecode file of source file
	bytecodeResult, err := bytecodeClient.Analyse(beforeChange, afterChange, diffs)
	if err != nil {
		log.Printf("call bytecode client err: %v", err)
		return nil, err
	}
	log.Printf("analyse bytecode success for %s, source_result=%+v", timestamp, bytecodeResult)

	return bytecodeResult, nil
}

func generateReposDir(first, second string) (string, error) {
	dirName := filepath.Join(conf.ReposPath, first, second)
	err := os.MkdirAll(dirName, os.ModePerm)
	return dirName, err
}

func exists(path string) bool {
	_, err := os.Stat(path) //os.Stat获取文件信息
	if err != nil {
		if os.IsExist(err) {
			return true
		}
		return false
	}
	return true
}

func cloneFromCommitHash(repoPath, repoUrl, commitHash string) (string, error) {
	if exists(repoPath) {
		dir, _ := ioutil.ReadDir(repoPath)
		if len(dir) != 0 {
			log.Printf("%s already cloned", commitHash)
			return repoPath, nil
		}
	}
	repo, err := git.PlainClone(repoPath, false, &git.CloneOptions{
		URL:      repoUrl,
		Progress: os.Stdout,
	})
	if err != nil {
		return "", err
	}
	wt, err := repo.Worktree()
	if err != nil {
		return "", err
	}
	err = wt.Checkout(&git.CheckoutOptions{Hash: plumbing.NewHash(commitHash), Force: true})
	if err != nil {
		return "", err
	}
	return repoPath, nil
}

func handlerUintTest(rows [][]string, mgr *cl.ClientsMgr, i int) (*pb.AnalysisResponse, error) {
	timestamp := strconv.FormatInt(time.Now().UnixNano(), 10)

	rowChild := rows[i]
	rowParent := rows[i+1]
	if len(rowChild) != 2 || len(rowParent) != 2 {
		log.Printf("Error: wrong format of row: %d, at %s", i, timestamp)
		return nil, errors.New("wrong format")
	}
	childCommitHash := rowChild[0]
	childFile := rowChild[1]
	parentCommitHash := rowParent[0]
	parentFile := rowParent[1]
	if childFile != parentFile {
		log.Printf("Error: mismatch child and parent of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	if filepath.Ext(childFile) != ".sol" {
		log.Printf("Error: not file of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	dirChild, err := generateReposDir(childCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate child dir: %v at %s", err, timestamp)
		return nil, err
	}
	dirParent, err := generateReposDir(parentCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate parent dir: %v at %s", err, timestamp)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirChild, conf.RepoUrl, childCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", childCommitHash, err)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirParent, conf.RepoUrl, parentCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", parentCommitHash, err)
		return nil, err
	}
	after := &pb.AnalysisTarget{RepoPath: childCommitHash, FilePath: childFile}
	before := &pb.AnalysisTarget{RepoPath: parentCommitHash, FilePath: parentFile}

	response, err := analyze_all(mgr, before, after, "", timestamp)
	if err != nil {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, err.Error(), timestamp)
		return nil, fmt.Errorf("analysze fail for %s", err)
	}
	if response.Status != 200 {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, response.Message, timestamp)
		return nil, fmt.Errorf("analysze fail for %s", response.Message)
	}
	b, err := json.Marshal(response)
	if err != nil {
		log.Printf("Error: marshal for %s result fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	filePath := filepath.Join(conf.ResultPath, childCommitHash+strings.TrimSuffix(filepath.Base(childFile), ".sol")+".json")
	err = ioutil.WriteFile(filePath, b, 0777)
	if err != nil {
		log.Printf("Error: write result for %s fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	log.Printf("success analyze for %s and %s, file: %s at %s", childCommitHash, parentCommitHash, childFile, timestamp)
	return response, nil
}

func goUintTest(rows [][]string, mgr *cl.ClientsMgr, i int) (*pb.SourceCodeAnalysisResponse, error) {
	timestamp := strconv.FormatInt(time.Now().UnixNano(), 10)

	rowChild := rows[i]
	rowParent := rows[i+1]
	if len(rowChild) != 2 || len(rowParent) != 2 {
		log.Printf("Error: wrong format of row: %d, at %s", i, timestamp)
		return nil, errors.New("wrong format")
	}
	childCommitHash := rowChild[0]
	childFile := rowChild[1]
	parentCommitHash := rowParent[0]
	parentFile := rowParent[1]
	if childFile != parentFile {
		log.Printf("Error: mismatch child and parent of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	if filepath.Ext(childFile) != ".go" {
		log.Printf("Error: not go file of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	dirChild, err := generateReposDir(childCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate child dir: %v at %s", err, timestamp)
		return nil, err
	}
	dirParent, err := generateReposDir(parentCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate parent dir: %v at %s", err, timestamp)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirChild, conf.RepoUrl, childCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", childCommitHash, err)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirParent, conf.RepoUrl, parentCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", parentCommitHash, err)
		return nil, err
	}
	after := &pb.AnalysisTarget{RepoPath: childCommitHash, FilePath: childFile}
	before := &pb.AnalysisTarget{RepoPath: parentCommitHash, FilePath: parentFile}

	response, err := analyze_go(mgr, before, after, "", timestamp)
	if err != nil {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, err.Error(), timestamp)
		return nil, fmt.Errorf("analysze fail for %s", err)
	}
	if response.Status != 200 {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, response.Message, timestamp)
		return nil, fmt.Errorf("analysze fail for %s", response.Message)
	}
	b, err := json.Marshal(response)
	if err != nil {
		log.Printf("Error: marshal for %s result fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	filePath := filepath.Join(conf.ResultPath, childCommitHash+strings.TrimSuffix(filepath.Base(childFile), ".sol")+".json")
	err = ioutil.WriteFile(filePath, b, 0777)
	if err != nil {
		log.Printf("Error: write result for %s fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	log.Printf("success analyze for %s and %s, file: %s at %s", childCommitHash, parentCommitHash, childFile, timestamp)
	return response, nil
}

func markdownUintTest(rows [][]string, mgr *cl.ClientsMgr, i int) (*pb.SourceCodeAnalysisResponse, error) {
	timestamp := strconv.FormatInt(time.Now().UnixNano(), 10)

	rowChild := rows[i]
	rowParent := rows[i+1]
	if len(rowChild) != 2 || len(rowParent) != 2 {
		log.Printf("Error: wrong format of row: %d, at %s", i, timestamp)
		return nil, errors.New("wrong format")
	}
	childCommitHash := rowChild[0]
	childFile := rowChild[1]
	parentCommitHash := rowParent[0]
	parentFile := rowParent[1]
	if childFile != parentFile {
		log.Printf("Error: mismatch child and parent of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	if filepath.Ext(childFile) != ".md" {
		log.Printf("Error: not markdown file of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	dirChild, err := generateReposDir(childCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate child dir: %v at %s", err, timestamp)
		return nil, err
	}
	dirParent, err := generateReposDir(parentCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate parent dir: %v at %s", err, timestamp)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirChild, conf.RepoUrl, childCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", childCommitHash, err)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirParent, conf.RepoUrl, parentCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", parentCommitHash, err)
		return nil, err
	}
	after := &pb.AnalysisTarget{RepoPath: childCommitHash, FilePath: childFile}
	before := &pb.AnalysisTarget{RepoPath: parentCommitHash, FilePath: parentFile}

	response, err := analyze_markdown(mgr, before, after, "", timestamp)
	if err != nil {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, err.Error(), timestamp)
		return nil, fmt.Errorf("analysze fail for %s", err)
	}
	if response.Status != 200 {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, response.Message, timestamp)
		return nil, fmt.Errorf("analysze fail for %s", response.Message)
	}
	b, err := json.Marshal(response)
	if err != nil {
		log.Printf("Error: marshal for %s result fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	filePath := filepath.Join(conf.ResultPath, childCommitHash+strings.TrimSuffix(filepath.Base(childFile), ".sol")+".json")
	err = ioutil.WriteFile(filePath, b, 0777)
	if err != nil {
		log.Printf("Error: write result for %s fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	log.Printf("success analyze for %s and %s, file: %s at %s", childCommitHash, parentCommitHash, childFile, timestamp)
	return response, nil
}

func solidityUintTest(rows [][]string, mgr *cl.ClientsMgr, i int) (*pb.SourceCodeAnalysisResponse, error) {
	timestamp := strconv.FormatInt(time.Now().UnixNano(), 10)

	rowChild := rows[i]
	rowParent := rows[i+1]
	if len(rowChild) != 2 || len(rowParent) != 2 {
		log.Printf("Error: wrong format of row: %d, at %s", i, timestamp)
		return nil, errors.New("wrong format")
	}
	childCommitHash := rowChild[0]
	childFile := rowChild[1]
	parentCommitHash := rowParent[0]
	parentFile := rowParent[1]
	if childFile != parentFile {
		log.Printf("Error: mismatch child and parent of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	if filepath.Ext(childFile) != ".sol" {
		log.Printf("Error: not solidity file of row %d at %s", i, timestamp)
		return nil, errors.New("not solidity ")
	}
	dirChild, err := generateReposDir(childCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate child dir: %v at %s", err, timestamp)
		return nil, err
	}
	dirParent, err := generateReposDir(parentCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate parent dir: %v at %s", err, timestamp)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirChild, conf.RepoUrl, childCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", childCommitHash, err)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirParent, conf.RepoUrl, parentCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", parentCommitHash, err)
		return nil, err
	}
	after := &pb.AnalysisTarget{RepoPath: childCommitHash, FilePath: childFile}
	before := &pb.AnalysisTarget{RepoPath: parentCommitHash, FilePath: parentFile}

	response, err := analyze_solidity(mgr, before, after, "", timestamp)
	if err != nil {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, err.Error(), timestamp)
		return nil, fmt.Errorf("analysze fail for %s", err)
	}
	if response.Status != 200 {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, response.Message, timestamp)
		return nil, fmt.Errorf("analysze fail for %s", response.Message)
	}
	b, err := json.Marshal(response)
	if err != nil {
		log.Printf("Error: marshal for %s result fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	filePath := filepath.Join(conf.ResultPath, childCommitHash+strings.TrimSuffix(filepath.Base(childFile), ".sol")+".json")
	err = ioutil.WriteFile(filePath, b, 0777)
	if err != nil {
		log.Printf("Error: write result for %s fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	log.Printf("success analyze for %s and %s, file: %s at %s", childCommitHash, parentCommitHash, childFile, timestamp)
	return response, nil
}

func evmUintTest(rows [][]string, mgr *cl.ClientsMgr, i int) (*pb.ByteCodeAnalysisResponse, error) {
	timestamp := strconv.FormatInt(time.Now().UnixNano(), 10)

	rowChild := rows[i]
	rowParent := rows[i+1]
	if len(rowChild) != 2 || len(rowParent) != 2 {
		log.Printf("Error: wrong format of row: %d, at %s", i, timestamp)
		return nil, errors.New("wrong format")
	}
	childCommitHash := rowChild[0]
	childFile := rowChild[1]
	parentCommitHash := rowParent[0]
	parentFile := rowParent[1]
	if childFile != parentFile {
		log.Printf("Error: mismatch child and parent of row %d at %s", i, timestamp)
		return nil, errors.New("mismatch child and parent")
	}
	if filepath.Ext(childFile) != ".sol" {
		log.Printf("Error: not solidity file of row %d at %s", i, timestamp)
		return nil, errors.New("not solidity file")
	}
	dirChild, err := generateReposDir(childCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate child dir: %v at %s", err, timestamp)
		return nil, err
	}
	dirParent, err := generateReposDir(parentCommitHash, "")
	if err != nil {
		log.Printf("Error: cannot generate parent dir: %v at %s", err, timestamp)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirChild, conf.RepoUrl, childCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", childCommitHash, err)
		return nil, err
	}
	_, err = cloneFromCommitHash(dirParent, conf.RepoUrl, parentCommitHash)
	if err != nil {
		log.Printf("Error: cannot clone commitHash: %s, error: %v", parentCommitHash, err)
		return nil, err
	}
	after := &pb.AnalysisTarget{RepoPath: childCommitHash, FilePath: childFile}
	before := &pb.AnalysisTarget{RepoPath: parentCommitHash, FilePath: parentFile}

	response, err := analyze_evm(mgr, before, after, "", timestamp)
	if err != nil {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, err.Error(), timestamp)
		return nil, fmt.Errorf("analysze fail for %s", err)
	}
	if response.Status != 200 {
		log.Printf("Error: analyze fail for %s and %s, file: %s, error: %s at %s", childCommitHash, parentCommitHash, childFile, response.Message, timestamp)
		return nil, fmt.Errorf("analysze fail for %s", response.Message)
	}
	b, err := json.Marshal(response)
	if err != nil {
		log.Printf("Error: marshal for %s result fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	filePath := filepath.Join(conf.ResultPath, childCommitHash+strings.TrimSuffix(filepath.Base(childFile), ".sol")+".json")
	err = ioutil.WriteFile(filePath, b, 0777)
	if err != nil {
		log.Printf("Error: write result for %s fail: %v at %s", childCommitHash, err, timestamp)
		return nil, err
	}
	log.Printf("success analyze for %s and %s, file: %s at %s", childCommitHash, parentCommitHash, childFile, timestamp)
	return response, nil
}

var testingType = flag.String("type", "", "type of tested service")
var inputFile = flag.String("input", "", "input file for testing")
var reposDir = flag.String("repos", "", "dirs for repos")
var resultDir = flag.String("result", "", "dirs for result")
var reportsDir = flag.String("reports", "", "dirs for reports")

func worker(wait *sync.WaitGroup, id int, s string, rows [][]string, mgr *cl.ClientsMgr, jobs <-chan int, results chan<- Response) {
	for i := range jobs {
		fmt.Println("worker", id, "processing job", i)
		var err error
		if s == "evm" {
			_, err = evmUintTest(rows, mgr, i)
		} else if s == "sol" {
			_, err = solidityUintTest(rows, mgr, i)
		} else if s == "md" {
			_, err = markdownUintTest(rows, mgr, i)
		} else if s == "go" {
			_, err = goUintTest(rows, mgr, i)
		} else if s == "all" {
			_, err = handlerUintTest(rows, mgr, i)
		}
		results <- Response{i, err}
	}
	wait.Done()
}

func GetAllFiles(dirPth string) (files []string, err error) {
	var dirs []string
	dir, err := ioutil.ReadDir(dirPth)
	if err != nil {
		return nil, err
	}

	PthSep := string(os.PathSeparator)
	//suffix = strings.ToUpper(suffix) //忽略后缀匹配的大小写

	for _, fi := range dir {
		if fi.IsDir() { // 目录, 递归遍历
			dirs = append(dirs, dirPth+PthSep+fi.Name())
			GetAllFiles(dirPth + PthSep + fi.Name())
		} else {
			// 过滤指定格式
			if fi.Name() == "meta_commit.json" {
				files = append(files, dirPth+PthSep+fi.Name())
			}
		}
	}

	// 读取子目录下文件
	for _, table := range dirs {
		temp, _ := GetAllFiles(table)
		for _, temp1 := range temp {
			files = append(files, temp1)
		}
	}

	return files, nil
}

func main() {
	flag.Parse()
	log.Printf("Testing file: %s, type: %s", *inputFile, *testingType)
	mgr := cl.NewClientMgr()
	result := &Result{Detail: make(map[string]string)}
	var rows [][]string



    if *reposDir != "" {
        conf.ReposPath = *reposDir
    }
    if *resultDir != "" {
        conf.ResultPath = *resultDir
    }
    if *reportsDir != "" {
        conf.ReportsPath = * reportsDir
    }
    if *inputFile != "" {
        f, err := excelize.OpenFile(*inputFile)
        if err != nil {
            log.Printf(err.Error())
            return
        }
        // 获取 Sheet1 上所有单元格
        rows, err = f.GetRows("Sheet1")
        if err != nil {
            log.Printf(err.Error())
            return
        }
    }else{
        log.Printf("has no input")
        return
    }


	// for i := 0; i < len(rows); i = i + 2 {
	jobs := make(chan int, 1000)
	results := make(chan Response, 1000)
	wg := sync.WaitGroup{}
	wg.Add(3)
	for w := 1; w <= 3; w++ {
		go worker(&wg, w, *testingType, rows, mgr, jobs, results)
	}
	for i := 0; i+1 < 199; i = i + 2 {
		jobs <- i
	}
	close(jobs)

	wg.Wait()
	close(results)

	MetaCommit := make(map[string]int)
	files, err := GetAllFiles(conf.ReportsPath)
	for i, file := range files {
		fmt.Println(strconv.Itoa(i), ":", file)
		data, err := ioutil.ReadFile(file)
		if err != nil {
			return
		}
		abstract := Abstract{}
		//读取的数据为json格式，需要进行解码
		err = json.Unmarshal(data, &abstract)
		if _, ok := MetaCommit["control_flow"]; ok {
			MetaCommit["control_flow"] += abstract.ControlFlow
		} else {
			MetaCommit["control_flow"] = abstract.ControlFlow
		}
		if _, ok := MetaCommit["data_flow"]; ok {
			MetaCommit["data_flow"] += abstract.DataFlow
		} else {
			MetaCommit["data_flow"] = abstract.DataFlow
		}
		if _, ok := MetaCommit["sequence_bin"]; ok {
			MetaCommit["sequence_bin"] += abstract.SequenceBin
		} else {
			MetaCommit["sequence_bin"] = abstract.SequenceBin
		}
		if _, ok := MetaCommit["sequence_src"]; ok {
			MetaCommit["sequence_src"] += abstract.SequenceSrc
		} else {
			MetaCommit["sequence_src"] = abstract.SequenceSrc
		}
		if _, ok := MetaCommit["selection_bin"]; ok {
			MetaCommit["selection_bin"] += abstract.SelectionBin
		} else {
			MetaCommit["selection_bin"] = abstract.SelectionBin
		}
		if _, ok := MetaCommit["selection_src"]; ok {
			MetaCommit["selection_src"] += abstract.SelectionSrc
		} else {
			MetaCommit["selection_src"] = abstract.SelectionSrc
		}
		if _, ok := MetaCommit["loop_bin"]; ok {
			MetaCommit["loop_bin"] += abstract.LoopBin
		} else {
			MetaCommit["loop_bin"] = abstract.LoopBin
		}
		if _, ok := MetaCommit["loop_src"]; ok {
			MetaCommit["loop_src"] += abstract.LoopSrc
		} else {
			MetaCommit["loop_src"] = abstract.LoopSrc
		}
	}
	for key := range MetaCommit {
		fmt.Println(key, ":", MetaCommit[key])
	}

	for response := range results {
		result.Total++
		if response.err != nil {
			result.Fail++
			result.Detail[rows[response.row][0]+"_"+strconv.Itoa(response.row)] = response.err.Error()
			continue
		}
		result.Success++
		result.Detail[rows[response.row][0]+"_"+strconv.Itoa(response.row)] = "success"
	}

	b, err := json.Marshal(result)
	if err != nil {
		log.Printf("Error: marshal result fail: %v", err)
		return
	}
	err = ioutil.WriteFile(filepath.Join(conf.ResultPath, "result.json"), b, 0777)
	if err != nil {
		log.Printf("Error: write result fail: %v", err)
	}
	log.Printf("analysis testing end")
	return
}

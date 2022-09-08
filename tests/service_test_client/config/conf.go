package config

import (
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"log"
)

type ServiceConf struct {
	Address string `yaml:"address"`
	Enabled bool   `yaml:"enabled"`
	Timeout int    `yaml:"timeout"`
}
type Config struct {
	CCppService     ServiceConf `yaml:"c_cpp_service"`
	RustService     ServiceConf `yaml:"rust_service"`
	GoService       ServiceConf `yaml:"go_service"`
	SolidityService ServiceConf `yaml:"solidity_service"`
	EvmService      ServiceConf `yaml:"evm_service"`
	LlvmService     ServiceConf `yaml:"llvm_service"`
	MdService       ServiceConf `yaml:"md_service"`
	HandlerService ServiceConf `yaml:"handler_service"`

	ResultPath      string `yaml:"result_path"`
	ReposPath     string `yaml:"repos_path"`
	ReportsPath   string `yaml:"reports_path"`
	RepoUrl       string `yaml:"repo_url"`
	ListenAddress string `yaml:"listen_address"`
}

func GetConf(configPath string) *Config {
	c := &Config{}
	yamlFile, err := ioutil.ReadFile(configPath)
	if err != nil {
		log.Printf("get config error for %v", err.Error())
		return nil
	}

	err = yaml.Unmarshal(yamlFile, c)

	if err != nil {
		log.Printf("get config error for %v", err.Error())
		return nil
	}
	log.Printf("get config from %s success", configPath)
	return c
}

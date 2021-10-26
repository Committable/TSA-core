import os
import xlrd
import xlwt
import subprocess
from xlutils.copy import copy
import logging, coloredlogs
import signal

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s',
                    datefmt = '%H:%M:%S')
logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] [%(process)d]: %(message)s'
coloredlogs.DEFAULT_DATE_FORMAT = '%H:%M:%S'
coloredlogs.DEFAULT_FIELD_STYLES = dict(
                                    asctime=dict(color='green'),
                                    hostname=dict(color='magenta'),
                                    levelname=dict(color='black', bold=True),
                                    name=dict(color='blue'),
                                    programname=dict(color='cyan'),
                                    username=dict(color='yellow'),
                                    filename=dict(color='cyan'),
                                    lineno=dict(color='cyan'),
                                    process=dict(color='magenta'))
coloredlogs.install(level='INFO')

project = "openzeppelin-contracts"
wb = xlrd.open_workbook(project+".xlsx")
sh1 = wb.sheet_by_index(0)

logger.info(u"sheet %s 共 %d 行 %d 列" % (sh1.name, sh1.nrows, sh1.ncols))

BASE_CMD_ENVIRONMENT_VARIABLES = {'http_proxy': 'http://192.168.177.1:7890',
                                  'https_proxy': 'http://192.168.177.1:7890'}
local_repository_path = "/Users/zhiqiang/transparenC/"+project

branch_name = "master"
environment_variables = BASE_CMD_ENVIRONMENT_VARIABLES
result_path = "/Users/zhiqiang/transparenC/result/"+project

if not os.path.exists(result_path):
    os.makedirs(result_path)

success = 0
failed = 0
tried = 0
total = 0

result = [["commit", "file", "status", "reason"]]


def write_excel_xls(path, sheet_name, value):
    index = len(value)  # 获取需要写入数据的行数
    workbook = xlwt.Workbook()  # 新建一个工作簿
    sheet = workbook.add_sheet(sheet_name)  # 在工作簿中新建一个表格
    for i in range(0, index):
        for j in range(0, len(value[i])):
            sheet.write(i, j, value[i][j])  # 像表格中写入数据（对应的行和列）
    workbook.save(path)  # 保存工作簿
    logger.info("xls格式表格写入数据成功！")


def write_excel_xls_append(path, value):
    index = len(value)  # 获取需要写入数据的行数
    workbook = xlrd.open_workbook(path)  # 打开工作簿
    sheets = workbook.sheet_names()  # 获取工作簿中的所有表格
    worksheet = workbook.sheet_by_name(sheets[0])  # 获取工作簿中所有表格中的的第一个表格
    rows_old = worksheet.nrows  # 获取表格中已存在的数据的行数
    new_workbook = copy(workbook)  # 将xlrd对象拷贝转化为xlwt对象
    new_worksheet = new_workbook.get_sheet(0)  # 获取转化后工作簿中的第一个表格
    for i in range(0, index):
        for j in range(0, len(value[i])):
            new_worksheet.write(i+rows_old, j, value[i][j])  # 追加写入数据，注意是从i+rows_old行开始写入
    new_workbook.save(path)  # 保存工作簿
    logger.info("xls格式表格【追加】写入数据成功！")


last_commit = ""

for i in range(0, sh1.nrows):
    if tried >= 100:
        write_excel_xls(result_path+"_compile_result_"+str(total)+".xlsx", "sheet1", result)
        write_excel_xls_append(result_path+"_compile_result_"+str(total)+".xlsx", [[tried, success, failed]])
        success = 0
        failed = 0
        tried = 0
        result = [["commit", "file", "status", "reason"]]
    commit_id = sh1.cell_value(i, 0)
    if last_commit != commit_id:
        tried += 1
        total += 1
        status = "success"
        reason = ""
        build_type = "unknown"
    else:
        continue
    last_commit = commit_id

    logger.info("begin test commit: %s", commit_id)
    logger.info("git checkout...")
    if status != "fail":
        try:
            git_checkout_cmd = subprocess.Popen(args=r'git checkout {} && git reset --hard {}'.format(branch_name, commit_id),
                                                shell=True, cwd=local_repository_path, stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, encoding='utf8', env=environment_variables)

            stdout, stderr = git_checkout_cmd.communicate()
            # if not stderr == '' and not stderr.startswith('Already on'):  # Once git reset returns any error
            if git_checkout_cmd.returncode != 0:
                status = "fail"
                reason = "Checkout fail::"+str(stderr)
                logger.error("git reset error: %s", str(stderr))

        except Exception as err:
            status = "fail"
            reason = "Checkout fail::"+str(err)
            logger.error("git reset error: %s", str(err))
    logger.info("detecting build type...")
    if status != "fail":
        try:
            if os.path.exists(os.path.join(local_repository_path,
                                           "hardhat.config.js")):
                build_type = "hardhad"
            elif os.path.exists(os.path.join(local_repository_path,
                                             ".waffle.json")):
                build_type = "waffle"
            elif os.path.exists(os.path.join(local_repository_path,
                                             "buidler.config.js")):
                build_type = "buidler"
            elif os.path.exists(os.path.join(local_repository_path,
                                             "truffle-config.js")) or os.path.exists(os.path.join(local_repository_path,
                                             "truffle.js")):
                build_type = "truffle"
            else:
                build_type = "unknown"
        except Exception as err:
            status = "fail"
            reason = "get build type fail::" + str(stderr)
    logger.info("compiling...")
    if status != "fail":
        try:
            compile_cmd = subprocess.Popen("yarn compile",
                                           shell=True, cwd=local_repository_path,
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
            stdout, stderr = compile_cmd.communicate()

            if compile_cmd.returncode != 0:
                if build_type == "truffle":
                    compile_cmd = subprocess.Popen("npx truffle compile",
                                           shell=True, cwd=local_repository_path,
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
                    stdout, stderr = compile_cmd.communicate()
                if compile_cmd.returncode != 0:
                    status = "fail"
                    reason = "compile fail::" + str(stderr)

        except Exception as err:
            status = "fail"
            reason = "compile fail::" + str(err)

    if status == "fail":
        logger.info("yarn installing...")
        install_cmd = subprocess.Popen("yarn",
                                       shell=True, cwd=local_repository_path,
                                       stderr=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
        try:
            stdout, stderr = install_cmd.communicate(timeout=300)

            if install_cmd.returncode != 0:
                status = "fail"
                reason = "compile fail::" + str(stderr)
            #logger.error("err: %s",str(stderr))
            #logger.error("out: %s", str(stdout))
        except subprocess.TimeoutExpired:
            install_cmd.kill()
            install_cmd.terminate()
            os.killpg(install_cmd.pid, signal.SIGTERM)
            reason = "npm install timeout"
            logger.error("timeout")
        except Exception as err:
            reason = "npm install fail"
            logger.error(str(err))

        try:
            logger.info("second compiling...")
            compile_cmd = subprocess.Popen("yarn compile",
                                           shell=True, cwd=local_repository_path,
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
            stdout, stderr = compile_cmd.communicate()

            if compile_cmd.returncode != 0:
                status = "fail"
                reason = "compile fail::" + str(stderr)
                if build_type == "truffle":
                    compile_cmd = subprocess.Popen("npx truffle compile",
                                           shell=True, cwd=local_repository_path,
                                           stderr=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
                    stdout, stderr = compile_cmd.communicate()
                if compile_cmd.returncode != 0:
                    status = "fail"
                    reason = "compile fail::" + str(stderr)
                else:
                    status = "success"
                    reason = ""
        except Exception as err:
            status = "fail"
            reason = "compile fail::" + str(err)

    if "fail" == status:
        failed += 1
    else:
        success += 1
    result.append([commit_id, status, reason, build_type])
    logger.info("commit: %s \n status: %s \n type: %s \n reason: %s", commit_id, status, build_type, reason)


write_excel_xls(result_path+"_compile_result.xlsx", "sheet1", result)
write_excel_xls_append(result_path+"_compile_result.xlsx", [[tried, success, failed]])

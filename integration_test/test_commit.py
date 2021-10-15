import os
import xlrd
import xlwt
import subprocess
import re
from xlutils.copy import copy
import logging, coloredlogs


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

logger.info( u"sheet %s 共 %d 行 %d 列" % (sh1.name, sh1.nrows, sh1.ncols))

BASE_CMD_ENVIRONMENT_VARIABLES = {'http_proxy': 'http://192.168.177.1:7890',
                                  'https_proxy': 'http://192.168.177.1:7890'}
local_repository_path = "/home/yangzq18/transparentC/"+project

branch_name = "master"
environment_variables = BASE_CMD_ENVIRONMENT_VARIABLES
result_path = "/home/yangzq18/result/"+project

if not os.path.exists(result_path):
    os.makedirs(result_path)

success = 0
failed = 0
tried = 0

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


for i in range(0, sh1.nrows):
    tried += 1
    status = "success"
    reason = ""

    commit_id = sh1.cell_value(i, 0)
    last_commit = ""
    file = sh1.cell_value(i, 1)

    logger.info("begine test commit: %s, file: %s", commit_id, file)

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

    if status != "fail":
        try:
            log_cmd = subprocess.Popen(["git", "log"], cwd=local_repository_path, stdout=subprocess.PIPE)
            stdout, stderr = log_cmd.communicate()
            if log_cmd.returncode != 0:
                status = "fail"
                reason = "diff fail::" + str(stderr)
                logger.error("git log error: %s", str(stderr))
            lines = str(stdout, 'utf-8').split('\n')
            first = True
            for line in lines:
                tmp = re.match(r'commit (\S{40})(.*)', line)
                if tmp:
                    if not first:
                        last_commit = tmp.group(1)
                        break
                    else:
                        first = False

            diff_cmd = subprocess.Popen(["git", "diff", last_commit, commit_id, file], cwd=local_repository_path, stdout=subprocess.PIPE)
            stdout, stderr = diff_cmd.communicate()
            if diff_cmd.returncode != 0:
                status = "fail"
                reason = "diff fail::" + str(stderr)
            if not os.path.exists(result_path+os.sep+"diff"):
                os.makedirs(result_path+os.sep+"diff")

            lines = str(stdout,'utf-8').split("\n")
            start_line = 0
            for i in range(0, len(lines)):
                m = re.match(r"(['|\"]?)@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)", lines[i])
                if m:
                    start_line = i
                    break

            with open(result_path+os.sep+"diff"+os.sep+file.split("/")[-1], 'w') as outputfile:
                outputfile.write("\n".join(lines[i:]))

        except Exception as err:
            status = "fail"
            reason = "diff fail::" + str(err)
            logger.error("git log error: %s", str(err))

    if status != "fail":
        try:
            output_path = result_path+os.sep+commit_id+os.sep+file.split("/")[-1].split(".sol")[0]
            if commit_id == "4e2641a9151fcbb0cd59126a52040fea68ecb807" and file=="contracts/utils/introspection/ERC165Checker.sol":
                print("here")
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            seraph_cmd = subprocess.Popen(["python",
                                         "/home/yangzq18/transparentC/seraph/seraph.py",
                                         "-s",
                                         local_repository_path,
                                         "-j",
                                         file,
                                         "-sol",
                                         "-p",
                                         "ethereum",
                                         "-o",
                                         output_path,
                                         "-diff",
                                         result_path + os.sep + "diff" + os.sep + file.split("/")[-1]
                                         ],
                                         stderr=subprocess.PIPE,
                                         stdout=subprocess.PIPE)
            stdout, stderr = seraph_cmd.communicate()

            if seraph_cmd.returncode != 100:
                status = "fail:" + str(seraph_cmd.returncode)
                reason = "Seraph fail::" + str(stderr)
                logger.error("seraph error: %s", str(stderr))
                logger.error("returncode: %s", str(seraph_cmd.returncode))
            # else:
            #     lines = str(stderr, "utf-8").split("\n")
            #     for line in lines:
            #         if "ERROR" in line or "CRITICAL" in line:
            #             status = "fail"
            #             reason = "Seraph fail::" + line
            #             logger.error("seraph error: %s", reason)
            #             break
        except Exception as err:
            status = "fail"
            reason = "Seraph fail::" + str(err)
            logger.error("seraph error: %s", str(err))

    if "fail" in status:
        failed += 1
    else:
        success += 1
    result.append([commit_id, file, status, reason])
    # logger.info(" ".join([
    #                  "-s",
    #                  local_repository_path,
    #                  "-j",
    #                  file,
    #                  "-sol",
    #                  "-p",
    #                  "ethereum",
    #                  "-o",
    #                  output_path,
    #                  "-diff",
    #                  result_path + os.sep + "diff" + os.sep + file.split("/")[-1]
    #                  ]))
    logger.info("end test commit: %s, file: %s", commit_id, file)


write_excel_xls(result_path+"result.xlsx", "sheet1", result)
write_excel_xls_append(result_path+"result.xlsx", [[tried, success, failed]])

import os
import xlrd
import xlwt
import subprocess
import re
from xlutils.copy import copy
import logging, coloredlogs

import signal
import random


def write_excel_xls(path, sheet_name, value):
    index = len(value)  # 获取需要写入数据的行数
    workbook = xlwt.Workbook()  # 新建一个工作簿
    sheet = workbook.add_sheet(sheet_name)  # 在工作簿中新建一个表格
    for i in range(0, index):
        for j in range(0, len(value[i])):
            sheet.write(i, j, value[i][j])  # 像表格中写入数据（对应的行和列）
    workbook.save(path)  # 保存工作簿
    logger.info("xls格式表格写入数据成功！")


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s',
                    datefmt='%H:%M:%S')
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

r_file = "openzeppelin-contracts_result.xlsx"
c_file = "selected_commit.xlsx"
t_file = "selected_task.xlsx"

wb = xlrd.open_workbook(r_file)
r_sh = wb.sheet_by_index(0)
wb = xlrd.open_workbook(c_file)
c_sh = wb.sheet_by_index(0)
wb = xlrd.open_workbook(t_file)
t_sh = wb.sheet_by_index(0)

logger.info(u"sheet %s 共 %d 行 %d 列" % (r_sh.name, c_sh.nrows, t_sh.ncols))

success = 0
failed = 0
partial = 0

commits_status = {}
for i in range(1, r_sh.nrows-1):
    status = r_sh.cell_value(i, 2)
    commit_id = r_sh.cell_value(i, 0)
    if commit_id not in commits_status:
        commits_status[commit_id] = status
    else:
        if commits_status[commit_id] != status:
            commits_status[commit_id] = "partial"

for i in commits_status:
    status = commits_status[i]
    if "fail" in status:
        failed += 1
    elif status == "success":
        success += 1
    else:
        partial += 1

result = [["commit_hash", "status"]]
for i in range(0, c_sh.nrows):
    commit_id = c_sh.cell_value(i, 0)
    if commit_id in commits_status:
        result.append([commit_id, commits_status[commit_id]])
    else:
        result.append([commit_id, "non-code"])

write_excel_xls("new_commmits.xlsx", "sheet1", result)

result = [["id", "name", "status", "type", "Priority", "description", "commits"]]
for i in range(0, t_sh.nrows):
    commit_ids = t_sh.cell_value(i, 5).split("、")
    first_status = ""
    for commit_id in commit_ids:
        if commit_id in commits_status:
            if first_status == "":
                first_status = commits_status[commit_id]
            elif first_status != commits_status[commit_id]:
                first_status = "partial"
    if first_status == "":
        result.append([int(t_sh.cell_value(i, 0)), t_sh.cell_value(i, 1), "non-code", t_sh.cell_value(i, 2),
                       t_sh.cell_value(i, 3), t_sh.cell_value(i, 4), t_sh.cell_value(i, 5)])
    else:
        result.append([int(t_sh.cell_value(i, 0)), t_sh.cell_value(i, 1), first_status, t_sh.cell_value(i, 2),
                   t_sh.cell_value(i, 3), t_sh.cell_value(i, 4), t_sh.cell_value(i, 5)])

write_excel_xls("new_tasks.xlsx", "sheet1", result)

print("end")

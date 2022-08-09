import json
from pandas import DataFrame


def main():
    with open("/home/liyue/Desktop/psr_exclude_set_3_fix_one_page.json", 'r') as load_f:
        load_dict = json.load(load_f)

    data = {'hash':[], 'psr':[], 'problem':[], 'solution':[], 'risk':[]}
    for commit in load_dict['meta_commits']:
        hash = commit['hash']
        psr = commit['contribution']['score']
        problem = commit['contribution']['problem']['score']
        solution = commit['contribution']['solution']['score']
        risk = commit['contribution']['risk']['score']
        data['hash'].append(hash)
        data['psr'].append(psr)
        data['problem'].append(problem)
        data['solution'].append(solution)
        data['risk'].append(risk)

    df = DataFrame(data)

    df.to_excel('/home/liyue/transparentCenter/AnalysisService/seraph/tmp/file_fix.xlsx')


if __name__ == '__main__':
    main()
import ujson
from utils import *
import itertools
import math
import pulp as lp

# %% 战区关卡参数
# 枪种系数：
TYPE = ["", "HG", "SMG", "RF", "AR", "MG", "SG"]
COEF = {'HG': 1, 'SMG': 1, 'RF': 1, 'AR': 1, 'MG': 1, 'SG': 1}
# 妖精加成：5星1.25
FAIRY = 1.25
# 优势人形
ADVANTAGE = []
# 昼夜战
ENVIRONMENT = 'night'
# 上场人形数量
MAX_DOLL = 30
# %%


def theater_area_setting(theater_area_id):
    with open(r'resource/theater_area_info.json') as f_theater_area:
        theater_area_info = ujson.load(f_theater_area)
        f_theater_area.close()

    for area in theater_area_info:
        if area["id"] == theater_area_id:
            COEF['HG'] = area["boss_score_coef"].split(";")[0]
            COEF['SMG'] = area["boss_score_coef"].split(";")[1]
            COEF['RF'] = area["boss_score_coef"].split(";")[2]
            COEF['AR'] = area["boss_score_coef"].split(";")[3]
            COEF['MG'] = area["boss_score_coef"].split(";")[4]
            COEF['SG'] = area["boss_score_coef"].split(";")[5]

            global MAX_DOLL
            global ADVANTAGE
            global ENVIRONMENT
            MAX_DOLL = 5 + 10 + int(area["theater_spare_gun_num"])
            ADVANTAGE = area["advantage_gun"].split(",")
            ENVIRONMENT = "night" if (area["boss"].split("-")[1] == "1") else "day"


def user_info_handle():
    user_info = open_json(r'info/user_info.json')

    gun_text = open_text(r'resource/gun.txt')
    equip_text = open_text(r'resource/equip.txt')
    gun_info = open_json(r'resource/gun_info.json', "utf-8")
    equip_info = open_json(r'resource/equip_info.json', "utf-8")

    # %% 统计持有人形信息
    my_dolls = {}
    for gun in gun_info:
        doll_id = int(gun['id'])
        if 1200 < doll_id < 20000 or doll_id > 30000:
            continue
        my_dolls[gun['id']] = {
            'id': gun['id'],
            'name': stc_to_text(gun_text, gun["name"]),
            'gun_level': 0,
            'skill1': 1,
            'skill2': 0,
            'number': 1,
            'favor': 0,
        }

    for doll in user_info['gun_with_user_info']:
        for k in ['gun_level', 'skill1', 'skill2', 'number']:
            my_dolls[doll['gun_id']][k] = max(int(doll[k]), my_dolls[doll['gun_id']][k])
        my_dolls[doll['gun_id']]['favor'] = max(int(doll['favor']) // 10000, my_dolls[doll['gun_id']]['favor'])

    # %% 统计持有装备信息
    my_equips = {}
    for equip in equip_info:
        my_equips[equip['id']] = {
            'id': equip['id'],
            'name': stc_to_text(equip_text, equip["name"]),
            'fit_guns': equip['fit_guns'],
            'level_00': 0,
            'level_10': 0,
        }

    for _, equip in user_info['equip_with_user_info'].items():
        if equip['equip_id'] not in my_equips.keys():
            continue
        level = int(equip['equip_level'])
        if level == 10:
            my_equips[equip['equip_id']]['level_10'] += 1
        else:
            my_equips[equip['equip_id']]['level_00'] += 1

    return {"my_dolls": my_dolls, "my_equips": my_equips}


def main():
    gun_info = open_json(r'resource/gun_info.json', "utf-8")
    equip_info = open_json(r'resource/equip_info.json', "utf-8")
    equip_text = open_text(r'resource/equip.txt')
    user_info = user_info_handle()
    my_dolls = user_info["my_dolls"]
    my_equips = user_info["my_equips"]

    # %% 计算各人形不同配装的效能
    choices = {}
    for gun in gun_info:
        gun_id = gun['id']
        if 1200 < int(gun_id) < 20000 or int(gun_id) > 30000:
            continue
        if my_dolls[gun_id]['gun_level'] == 0:
            continue

        equip_group_all = []
        for num in ["1", "2", "3"]:
            equip_group_category = []
            types = gun[f'type_equip{num}'].split(";")[-1].split(',')
            for equip in equip_info:
                if equip['type'] not in types:
                    continue
                if equip['fit_guns'] and gun_id not in equip['fit_guns'].split(','):
                    continue
                eid = equip['id']
                if my_equips[eid]['level_10'] > 0:
                    equip_group_category.append((equip, 10))
                if my_equips[eid]['level_00'] > 0 and my_equips[eid]['level_10'] < MAX_DOLL:
                    equip_group_category.append((equip, 0))
            equip_group_all.append(equip_group_category)

        for i, j, k in itertools.product(*equip_group_all):
            strength = doll_attr_calculate(gun, my_dolls[gun_id], [i, j, k])
            # print(strength)
            sp_ratio = 1.2 if gun_id in ADVANTAGE else 1
            score = math.floor(int(COEF[TYPE[int(gun['type'])]]) * sp_ratio * FAIRY * strength[ENVIRONMENT] / 100)
            # print(name_table[i[0]['name']],i[1],name_table[j[0]['name']],j[1],name_table[k[0]['name']],k[1],score)
            recipe_name = f"{my_dolls[gun_id]['name']}_" \
                          f"{stc_to_text(equip_text, i[0]['name'])}_{i[1]}_" \
                          f"{stc_to_text(equip_text, j[0]['name'])}_{j[1]}_" \
                          f"{stc_to_text(equip_text, k[0]['name'])}_{k[1]}"
            recipe_content = {
                my_dolls[gun_id]['name']: -1,
                f"{stc_to_text(equip_text, i[0]['name'])}_{i[1]}": 0,
                f"{stc_to_text(equip_text, j[0]['name'])}_{j[1]}": 0,
                f"{stc_to_text(equip_text, k[0]['name'])}_{k[1]}": 0,
                'score': score
            }
            recipe_content[f"{stc_to_text(equip_text, i[0]['name'])}_{i[1]}"] -= 1
            recipe_content[f"{stc_to_text(equip_text, j[0]['name'])}_{j[1]}"] -= 1
            recipe_content[f"{stc_to_text(equip_text, k[0]['name'])}_{k[1]}"] -= 1
            choices[recipe_name] = recipe_content
    print("Choice number", len(choices.items()))

    # %%
    resource = {}
    for _, doll in my_dolls.items():
        if doll['gun_level'] > 0:
            resource[doll['name']] = 1
    for _, equip in my_equips.items():
        if equip['level_10'] > 0:
            resource[f"{equip['name']}_10"] = equip['level_10']
        if equip['level_00'] > 0:
            resource[f"{equip['name']}_0"] = equip['level_00']
    resource['count'] = MAX_DOLL
    resource['score'] = 0

    lp_vars = {}
    # 定义线性规划，求解最大值
    problem = lp.LpProblem('battlefield', lp.LpMaximize)
    for k, recipe in choices.items():

        # 每个人形和其装备选择构成一个变量
        lp_vars[k] = lp.LpVariable(k, cat=lp.LpBinary)
        for r, c in recipe.items():
            # 全部的装备数量减去使用的装备大于等于0
            resource[r] += c * lp_vars[k]

        # 选取的人形数量小于等于MAX_DOLL
        resource['count'] -= lp_vars[k]
    for k, v in resource.items():
        problem += v >= 0, k

    # 线性规划求解分数的最大值
    problem += resource['score']
    print(problem.solve())
    print(resource['score'].value())
    res = []
    for k, v in lp_vars.items():
        if v.value() > 0:
            res.append((k, choices[k]['score'], v.value()))
    res.sort(key=lambda x: x[1], reverse=True)
    for r in res:
        print(r[0], r[1], r[2])
    # %%


theater_area_setting(input("-- Please type in the target theater area id -- "))
main()

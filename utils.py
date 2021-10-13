
import csv
import math
import ujson


def doll_attr_calculate(gun, my_doll, equip_group):
    lv = my_doll['gun_level']
    favor_factor = 0.95 + (my_doll['favor'] + 10) // 50 * 0.05

    attr_change = {"life": 0, "pow": 0, "rate": 0, "hit": 0, "dodge": 0, "armor": 0}
    attr_fixed = {"critical_harm_rate": 150, "critical_percent": gun['crit'],
                  "armor_piercing": gun['armor_piercing'], "night_view_percent": 0, "bullet": gun['special']}
    attr_other = {"id": gun["id"], "star": gun["rank"], "upgrade": lv, "type": gun["type"], "skill_effect_per": 0,
                  "skill_effect": 0, 'number': my_doll['number'], 'skill1': my_doll['skill1'], 'skill2': my_doll['skill2']}

    for key in ["pow", "hit", "dodge"]:
        attr_change[key] = gf_ceil(calculate(lv, key, gun) * favor_factor)
    for key in ["life", "rate", "armor"]:
        attr_change[key] = gf_ceil(calculate(lv, key, gun))

    for equip, elv in equip_group:
        if not equip:
            continue

        attr_other["skill_effect_per"] += int(equip["skill_effect_per"])
        attr_other["skill_effect"] += int(equip["skill_effect"])

        equip_mul = {}
        if equip['bonus_type']:
            equip_mul = bonus_handle(equip['bonus_type'])

        for key in attr_change.keys():
            if key in equip.keys() and equip[key] and (key not in equip_mul.keys()):
                equip_mul[key] = "1"
        for key in attr_fixed.keys():
            if key in equip.keys() and equip[key] and (key not in equip_mul.keys()):
                equip_mul[key] = "1"

        # print(equip_mul)
        for key in equip_mul.keys():
            attr = math.floor(float(equip[key].split(",")[-1]) * float(equip_mul[key]))

            if key in attr_change.keys():
                attr_change[key] = int(attr_change[key]) + int(attr)
            elif key in attr_fixed.keys():
                attr_fixed[key] = int(attr_fixed[key]) + int(attr)

    day = doll_effect_calculate({"attr_change": attr_change, "attr_fixed": attr_fixed, "attr_other": attr_other}, "day")
    night = doll_effect_calculate({"attr_change": attr_change, "attr_fixed": attr_fixed, "attr_other": attr_other}, "night")

    return {"day": day, "night": night}


def doll_effect_calculate(gun_attr, fight_type):

    skill1 = gun_attr["attr_other"]['skill1']
    skill2 = gun_attr["attr_other"]['skill2']
    star = int(gun_attr["attr_other"]["star"])
    number = gun_attr["attr_other"]["number"]
    skill_effect = int(gun_attr["attr_other"]["skill_effect"])
    skill_effect_per = int(gun_attr["attr_other"]["skill_effect_per"])

    # 1技能效能 = ceiling（5*(0.8+星级/10)*[35+5*(技能等级-1)]*(100+skill_effect_per)/100,1) + skill_effect
    # 2技能效能 = ceiling（5*(0.8+星级/10)*[15+2*(技能等级-1)]*(100+skill_effect_per)/100,1) + skill_effect
    doll_skill_effect = gf_ceil(number*(0.8+star/10)*(35+5*(skill1-1))*(100+skill_effect_per)/100) + skill_effect
    if gun_attr["attr_other"]["upgrade"] >= 110:
        doll_skill_effect += gf_ceil(number*(0.8+star/10)*(15+2*(skill2-1))*(100+skill_effect_per)/100)

    life = int(gun_attr["attr_change"]["life"])
    dodge = int(gun_attr["attr_change"]["dodge"])
    armor = int(gun_attr["attr_change"]["armor"])
    # 防御效能 = CEILING(生命*(35+闪避)/35*(4.2*100/MAX(1,100-护甲)-3.2),1)
    defend_effect = gf_ceil(life*number*(35+dodge)/35*(4.2*100/max(1, 100-armor)-3.2))

    hit = int(gun_attr["attr_change"]["hit"])
    night_view_percent = int(gun_attr["attr_fixed"]["night_view_percent"])
    if fight_type == "night":
        # 夜战命中 = CEILING(命中*(1+(-0.9*(1-夜视仪数值/100))),1)
        hit = gf_ceil(hit*(1+(-0.9*(1-night_view_percent/100))))

    attack = int(gun_attr["attr_change"]["pow"])
    rate = int(gun_attr["attr_change"]["rate"])
    critical = int(gun_attr["attr_fixed"]["critical_percent"])
    critical_damage = int(gun_attr["attr_fixed"]["critical_harm_rate"])
    armor_piercing = int(gun_attr["attr_fixed"]["armor_piercing"])
    bullet = int(gun_attr["attr_fixed"]["bullet"])
    if gun_attr["attr_other"]["type"] == "SG":
        # SG攻击 = 6*5*(3*弹量*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)/(1.5+弹量*50/射速+0.5*弹量)*命中/(命中+23)+8)
        attack_effect = gf_ceil(6*number*(3*bullet*(attack+armor_piercing/3)*(1+critical*(critical_damage-100)/10000)/(1.5+bullet*50/rate+0.5*bullet)*hit/(hit+23)+8))
    elif gun_attr["attr_other"]["type"] == "MG":
        # MG攻击 = 7*5*(弹量*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)/(弹量/3+4+200/射速)*命中/(命中+23)+8)
        attack_effect = gf_ceil(7*number*(bullet*(attack+armor_piercing/3)*(1+critical*(critical_damage-100)/10000)/(bullet/3+4+200/rate)*hit/(hit+23)+8))
    else:
        # 其他攻击 = 5*5*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)*射速/50*命中/(命中+23)+8)
        attack_effect = gf_ceil(5*number*((attack+armor_piercing/3)*(1+critical*(critical_damage-100)/10000)*rate/50*hit/(hit+23)+8))

    effect_total = doll_skill_effect + defend_effect + attack_effect
    return effect_total


def stc_to_text(text, name):
    tem = text[text.find(name) + len(name) + 1:]
    out_text = tem[:tem.find("\n")]
    return out_text


def open_json(path, encoding="none"):
    if encoding == "utf-8":
        with open(path, encoding='utf-8') as f:
            info = ujson.load(f)
            f.close()
    else:
        with open(path) as f:
            info = ujson.load(f)
            f.close()

    return info


def open_text(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
        f.close()
    return text


def bonus_handle(string):
    dict1 = {}
    attr1 = string.split(',')
    for key in attr1:
        type1 = key.split(':')[0]
        numb1 = key.split(':')[1]
        dict1[type1] = str(1 + int(numb1) / 1000)
    return dict1


def gf_ceil(number):
    if number % 1 < 0.0001:
        number = number - (number % 1)
    else:
        number = number - (number % 1) + 1
    return int(number)


BASIC = [16, 45, 5, 5]
BASIC_LIFE_ARMOR = [
    [[55, 0.555], [2, 0.161]],
    [[96.283, 0.138], [13.979, 0.04]]
]
BASE_ATTR = [
    [0.60, 0.60, 0.80, 1.20, 1.80, 0.00],
    [1.60, 0.60, 1.20, 0.30, 1.60, 0.00],
    [0.80, 2.40, 0.50, 1.60, 0.80, 0.00],
    [1.00, 1.00, 1.00, 1.00, 1.00, 0.00],
    [1.50, 1.80, 1.60, 0.60, 0.60, 0.00],
    [2.00, 0.70, 0.40, 0.30, 0.30, 1.00]
]
GROW = [
    [[0.242, 0], [0.181, 0], [0.303, 0], [0.303, 0]],
    [[0.06, 18.018], [0.022, 15.741], [0.075, 22.572], [0.075, 22.572]]
]
TYPE_ENUM = {"HG": 0, "SMG": 1, "RF": 2, "AR": 3, "MG": 4, "SG": 5}
ATTR_ENUM = {"life": 0, "pow": 1, "rate": 2, "hit": 3, "dodge": 4, "armor": 5}


def calculate(lv, attr_type, gun):
    mod = 1
    if lv <= 100:
        mod = 0

    guntype = int(gun['type']) - 1
    attr = ATTR_ENUM[attr_type]
    ratio = int(gun['ratio_' + attr_type])
    growth = int(gun['eat_ratio'])

    if attr == 0 or attr == 5:
        return math.ceil(
            (BASIC_LIFE_ARMOR[mod][attr & 1][0] + (lv-1)*BASIC_LIFE_ARMOR[mod][attr & 1][1]) * BASE_ATTR[guntype][attr] * ratio / 100
        )
    else:
        base = BASIC[attr-1] * BASE_ATTR[guntype][attr] * ratio / 100
        accretion = (GROW[mod][attr-1][1] + (lv-1)*GROW[mod][attr-1][0]) * BASE_ATTR[guntype][attr] * ratio * growth / 100 / 100
        return math.ceil(base) + math.ceil(accretion)

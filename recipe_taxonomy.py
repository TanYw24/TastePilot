from __future__ import annotations

SOLAR_TERMS = [
    "立春",
    "雨水",
    "惊蛰",
    "春分",
    "清明",
    "谷雨",
    "立夏",
    "小满",
    "芒种",
    "夏至",
    "小暑",
    "大暑",
    "立秋",
    "处暑",
    "白露",
    "秋分",
    "寒露",
    "霜降",
    "立冬",
    "小雪",
    "大雪",
    "冬至",
    "小寒",
    "大寒",
]

CANONICAL_MAIN_TYPES = {"正餐主食", "正餐菜品", "轻食早午餐", "甜品", "饮品"}
CANONICAL_FOOD_ORIGINS = {"中式", "日式", "韩式", "东南亚", "西式", "拉美", "饮品特调"}
CHINESE_REGIONAL_CUISINES = {
    "中式家常",
    "川菜",
    "湘菜",
    "粤菜",
    "港式",
    "台式",
    "江浙",
    "西北风味",
    "云贵风味",
    "闽味",
    "中式甜品",
}
CANONICAL_REGIONAL_CUISINES = CHINESE_REGIONAL_CUISINES | {
    "日式",
    "韩式",
    "泰式",
    "越式",
    "南洋风味",
    "意式",
    "法式西餐",
    "美式西餐",
    "西式轻食",
    "西式甜点",
    "墨西哥风味",
    "拉美风味",
    "饮品特调",
}
CANONICAL_SUB_TYPES = {
    "饭类",
    "面类",
    "粉类",
    "饼类",
    "锅汤类",
    "菜肴类",
    "沙拉碗类",
    "三明治贝果类",
    "吐司卷饼类",
    "早餐碗类",
    "轻主食类",
    "蛋糕类",
    "布丁冻品类",
    "中式甜品类",
    "冰品类",
    "烘焙点心类",
    "咖啡类",
    "茶饮类",
    "奶茶类",
    "果饮类",
    "气泡饮类",
    "奶昔类",
    "热饮类",
}
SIMPLIFIED_FLAVOR_TAGS = {"鲜香", "香辣", "麻辣", "酸甜", "蒜香", "奶香", "酱香", "清淡", "重口"}
SIMPLIFIED_SCENE_TAGS = {"一个人吃", "双人晚餐", "朋友聚餐", "早餐", "下午茶", "夜宵", "健身准备餐"}
SIMPLIFIED_FEATURE_TAGS = {"快手", "省钱", "高蛋白", "素食友好", "清爽", "暖胃", "解馋", "治愈", "下饭", "分享"}


def parse_tags(raw_value: str) -> list[str]:
    if raw_value is None or raw_value != raw_value:
        return []
    return [item.strip() for item in str(raw_value).split("|") if item.strip()]


def join_tags(tags: list[str]) -> str:
    return "|".join(dict.fromkeys(tag for tag in tags if tag))


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def normalize_seasonal_terms(recipe: dict) -> list[str]:
    direct_terms = [tag for tag in parse_tags(recipe.get("seasonal_terms", "")) if tag in SOLAR_TERMS]
    if direct_terms:
        return list(dict.fromkeys(direct_terms))

    legacy_terms = [tag for tag in parse_tags(recipe.get("feature_tags", "")) if tag in SOLAR_TERMS]
    return list(dict.fromkeys(legacy_terms))


def _canonicalize_main_type(value: str) -> str:
    mapping = {
        "正餐": "正餐",
        "正餐主食": "正餐主食",
        "正餐菜品": "正餐菜品",
        "家常菜肴": "正餐菜品",
        "汤锅粥羹": "正餐菜品",
        "轻食早午餐": "轻食早午餐",
        "甜品": "甜品",
        "甜品点心": "甜品",
        "饮品": "饮品",
    }
    return mapping.get(str(value or "").strip(), "")


def _legacy_cuisine_value(recipe: dict) -> str:
    return str(recipe.get("regional_cuisine") or recipe.get("cuisine") or "").strip()


def _legacy_sub_type_value(recipe: dict) -> str:
    return str(recipe.get("sub_type") or recipe.get("staple_category") or recipe.get("beverage_category") or "").strip()


def classify_main_type(recipe: dict) -> str:
    current = _canonicalize_main_type(str(recipe.get("main_type", "")).strip())
    if current and current != "正餐":
        return current

    sub_type = classify_sub_type(recipe)
    if sub_type in {"饭类", "面类", "粉类", "饼类"}:
        return "正餐主食"
    if sub_type in {"锅汤类", "菜肴类"}:
        return "正餐菜品"
    if sub_type in {"沙拉碗类", "三明治贝果类", "吐司卷饼类", "早餐碗类", "轻主食类"}:
        return "轻食早午餐"
    if sub_type in {"蛋糕类", "布丁冻品类", "中式甜品类", "冰品类", "烘焙点心类"}:
        return "甜品"
    if sub_type in {"咖啡类", "茶饮类", "奶茶类", "果饮类", "气泡饮类", "奶昔类", "热饮类"}:
        return "饮品"
    if current == "正餐":
        return "正餐主食"
    return "正餐主食"


def classify_food_origin(recipe: dict) -> str:
    current = str(recipe.get("food_origin", "")).strip()
    if current in CANONICAL_FOOD_ORIGINS:
        return current

    regional = classify_regional_cuisine(recipe)
    if regional in CHINESE_REGIONAL_CUISINES:
        return "中式"
    if regional == "日式":
        return "日式"
    if regional == "韩式":
        return "韩式"
    if regional in {"泰式", "越式", "南洋风味"}:
        return "东南亚"
    if regional in {"意式", "法式西餐", "美式西餐", "西式轻食", "西式甜点"}:
        return "西式"
    if regional in {"墨西哥风味", "拉美风味"}:
        return "拉美"
    if regional == "饮品特调":
        return "饮品特调"
    return "中式"


def classify_regional_cuisine(recipe: dict) -> str:
    current = str(recipe.get("regional_cuisine", "")).strip()
    if current in CANONICAL_REGIONAL_CUISINES:
        return current

    legacy = _legacy_cuisine_value(recipe)
    name = str(recipe.get("name", ""))
    main_type = _canonicalize_main_type(str(recipe.get("main_type", "")).strip()) or ""

    explicit_mapping = {
        "家常": "中式家常",
        "汤品": "中式家常",
        "热食": "中式家常",
        "冷盘": "中式家常",
        "夜宵": "中式家常",
        "川菜": "川菜",
        "川味": "川菜",
        "川式": "川菜",
        "川黔": "川菜",
        "湘菜": "湘菜",
        "湘式": "湘菜",
        "粤式": "粤菜",
        "港式": "港式",
        "港式甜品": "港式",
        "台式": "台式",
        "日式": "日式",
        "韩式": "韩式",
        "泰式": "泰式",
        "越式": "越式",
        "东南亚": "南洋风味",
        "东南亚甜品": "南洋风味",
        "意式": "意式",
        "墨西哥风味": "墨西哥风味",
    }
    if legacy in explicit_mapping:
        return explicit_mapping[legacy]

    if legacy in {"轻食", "早午餐"}:
        return "西式轻食"
    if legacy in {"西式", "烘焙", "甜品"}:
        if main_type == "甜品":
            if _contains_any(name, ["汤圆", "酒酿", "银耳", "冰粉", "芝麻糊", "糯米", "圆子", "羹", "西米露", "甘露"]):
                return "中式甜品"
            return "西式甜点"
        if main_type == "轻食早午餐":
            return "西式轻食"
        return "法式西餐" if _contains_any(name, ["可丽饼", "洋葱汤", "布蕾"]) else "美式西餐"
    if legacy == "饮品":
        if _contains_any(name, ["姜茶", "酸梅汤", "桂圆", "核桃露", "芝麻糊", "红糖"]) or _contains_any(name, ["乌梅", "银耳"]):
            return "中式家常"
        if _contains_any(name, ["拿铁", "美式", "摩卡", "咖啡"]):
            return "美式西餐"
        if _contains_any(name, ["椰", "泰", "南洋"]):
            return "南洋风味"
        return "饮品特调"

    if _contains_any(name, ["抛猪", "冬阴功", "椰浆", "打抛"]):
        return "泰式"
    if _contains_any(name, ["河粉", "越式", "牛肉河粉"]):
        return "越式"
    if _contains_any(name, ["塔可", "莎莎", "法士达", "可萨迪亚", "卷饼"]):
        return "墨西哥风味"
    if _contains_any(name, ["意面", "烩饭", "披萨", "帕玛森", "罗勒"]):
        return "意式"
    if _contains_any(name, ["可颂", "贝果", "帕尼尼", "沙拉", "凯撒", "吐司"]):
        return "西式轻食"
    if _contains_any(name, ["蛋糕", "布朗尼", "司康", "派", "挞", "布丁", "慕斯"]):
        return "西式甜点"
    return "中式家常"


def classify_sub_type(recipe: dict) -> str:
    current = str(recipe.get("sub_type", "")).strip()
    if current in CANONICAL_SUB_TYPES:
        return current

    name = str(recipe.get("name", ""))
    main_type = _canonicalize_main_type(str(recipe.get("main_type", "")).strip())
    if not main_type:
        legacy_main = str(recipe.get("main_type", "")).strip()
        if legacy_main:
            main_type = _canonicalize_main_type(legacy_main)
    legacy_sub = _legacy_sub_type_value(recipe)
    beverage_sub = str(recipe.get("beverage_category", "")).strip()

    if main_type == "饮品":
        if beverage_sub == "咖啡" or _contains_any(name, ["美式", "拿铁", "摩卡", "馥芮白", "咖啡"]):
            return "咖啡类"
        if beverage_sub == "奶茶" or "奶茶" in name:
            return "奶茶类"
        if beverage_sub == "茶饮" or _contains_any(name, ["冷泡茶", "乌龙", "红茶", "绿茶", "茉莉", "姜茶"]):
            return "茶饮类"
        if beverage_sub in {"果茶", "果饮"} or _contains_any(name, ["果茶", "柠檬红茶"]):
            return "果饮类"
        if beverage_sub == "气泡饮" or _contains_any(name, ["气泡", "苏打"]):
            return "气泡饮类"
        if beverage_sub == "奶昔" or _contains_any(name, ["奶昔", "冰沙"]):
            return "奶昔类"
        if beverage_sub == "热饮" or _contains_any(name, ["热巧克力", "热饮", "燕麦奶", "热可可"]):
            return "热饮类"
        return "果饮类"

    if main_type == "甜品":
        if _contains_any(name, ["冰淇淋", "雪糕", "冰粉", "刨冰", "冰糕"]):
            return "冰品类"
        if _contains_any(name, ["布丁", "奶冻", "慕斯", "茶冻", "果冻"]):
            return "布丁冻品类"
        if _contains_any(name, ["汤圆", "酒酿", "银耳", "羹", "糍粑", "糯米", "圆子", "甘露", "西米露", "山药糕", "芝麻糊"]):
            return "中式甜品类"
        if _contains_any(name, ["司康", "派", "挞", "玛芬", "曲奇", "泡芙", "麻薯卷", "奶油卷"]):
            return "烘焙点心类"
        return "蛋糕类"

    if main_type == "轻食早午餐":
        if _contains_any(name, ["沙拉", "波奇", "藜麦碗", "能量碗"]):
            return "沙拉碗类"
        if _contains_any(name, ["果麦杯", "燕麦杯", "酸奶碗", "酸奶杯"]) or ("酸奶" in name and _contains_any(name, ["燕麦", "果麦"])):
            return "早餐碗类"
        if _contains_any(name, ["三明治", "贝果"]):
            return "三明治贝果类"
        if _contains_any(name, ["吐司", "卷", "可颂", "帕尼尼", "可萨迪亚"]):
            return "吐司卷饼类"
        return "轻主食类"

    direct_map = {
        "饭类": "饭类",
        "面类": "面类",
        "粉类": "粉类",
        "饼类": "饼类",
        "锅物": "锅汤类",
        "汤粥": "锅汤类",
        "菜肴": "菜肴类",
        "面包三明治": "饼类",
    }
    if legacy_sub in direct_map:
        return direct_map[legacy_sub]
    if _contains_any(name, ["饭", "盖饭", "炒饭", "丼", "饭团", "烩饭"]):
        return "饭类"
    if _contains_any(name, ["米线", "米粉", "河粉", "凉皮", "酸辣粉", "牛河"]):
        return "粉类"
    if _contains_any(name, ["面", "拉面", "乌冬", "线面", "意面", "冷面"]):
        return "面类"
    if _contains_any(name, ["汤", "粥", "羹", "锅", "火锅", "煲"]):
        return "锅汤类"
    if _contains_any(name, ["饼", "卷", "馄饨", "饺", "披萨", "春卷"]):
        return "饼类"
    return "菜肴类"


def classify_staple_category(recipe: dict) -> str:
    return classify_sub_type(recipe)


def classify_cuisine_group(recipe: dict) -> str:
    food_origin = classify_food_origin(recipe)
    regional = classify_regional_cuisine(recipe)
    if food_origin == "中式":
        if regional in {"川菜", "湘菜"}:
            return "川菜湘菜"
        if regional in {"粤菜", "港式"}:
            return "粤港"
        if regional == "台式":
            return "台式"
        if regional == "中式甜品":
            return "中式甜品"
        return "中式"
    return food_origin


def classify_beverage_category(recipe: dict) -> str:
    sub_type = classify_sub_type(recipe)
    mapping = {
        "咖啡类": "咖啡",
        "茶饮类": "茶饮",
        "奶茶类": "奶茶",
        "果饮类": "果饮",
        "气泡饮类": "气泡饮",
        "奶昔类": "奶昔",
        "热饮类": "热饮",
    }
    return mapping.get(sub_type, "")


def simplify_flavor_tags(recipe: dict) -> list[str]:
    existing = parse_tags(recipe.get("flavor_tags", ""))
    name = str(recipe.get("name", ""))

    mapped = []
    for tag in existing:
        if tag in SIMPLIFIED_FLAVOR_TAGS:
            mapped.append(tag)
        elif tag in {"咸香", "家常"}:
            mapped.append("鲜香")
        elif tag == "甜香":
            mapped.append("奶香" if "奶" in name else "酸甜")
        elif tag == "果香":
            mapped.append("酸甜")

    if _contains_any(name, ["麻婆", "水煮", "麻辣"]):
        mapped.append("麻辣")
    if _contains_any(name, ["酸汤", "泡菜", "柠檬", "百香果", "杨枝甘露"]):
        mapped.append("酸甜")
    return list(dict.fromkeys(tag for tag in mapped if tag in SIMPLIFIED_FLAVOR_TAGS))


def simplify_scene_tags(recipe: dict) -> list[str]:
    existing = parse_tags(recipe.get("scene_tags", ""))
    main_type = classify_main_type(recipe)
    mapped = []
    for tag in existing:
        if tag == "家庭晚餐":
            mapped.append("双人晚餐")
        elif tag == "深夜加餐":
            mapped.append("夜宵")
        elif tag in SIMPLIFIED_SCENE_TAGS:
            mapped.append(tag)
    if main_type == "甜品" and "下午茶" not in mapped:
        mapped.append("下午茶")
    return list(dict.fromkeys(tag for tag in mapped if tag in SIMPLIFIED_SCENE_TAGS))


def simplify_feature_tags(recipe: dict) -> list[str]:
    feature_tags = parse_tags(recipe.get("feature_tags", ""))
    legacy_diet_tags = parse_tags(recipe.get("diet_tags", ""))
    name = str(recipe.get("name", ""))
    mapped = []

    tag_mapping = {
        "快手": "快手",
        "省钱": "省钱",
        "高蛋白": "高蛋白",
        "素食友好": "素食友好",
        "清爽": "清爽",
        "轻负担": "清爽",
        "低糖感": "清爽",
        "暖胃": "暖胃",
        "热乎": "暖胃",
        "解馋": "解馋",
        "治愈": "治愈",
        "下饭": "下饭",
        "分享": "分享",
        "聚餐": "分享",
    }
    for tag in feature_tags + legacy_diet_tags:
        if tag in tag_mapping:
            mapped.append(tag_mapping[tag])
        if tag == "下饭解馋":
            mapped.extend(["下饭", "解馋"])

    if recipe.get("is_vegetarian") in {1, "1"}:
        mapped.append("素食友好")
    if _contains_any(name, ["汤", "粥", "锅", "面"]) and "暖胃" not in mapped:
        mapped.append("暖胃")
    return list(dict.fromkeys(tag for tag in mapped if tag in SIMPLIFIED_FEATURE_TAGS))


def get_recipe_profile_tags(recipe: dict) -> list[str]:
    tags = simplify_flavor_tags(recipe)
    name = str(recipe.get("name", ""))
    sub_type = classify_sub_type(recipe)

    if sub_type == "咖啡类" and _contains_any(name, ["美式", "黑咖啡", "冷萃"]):
        tags.append("苦香")
    if sub_type == "果饮类":
        tags.extend(["酸甜", "清淡"])
    if sub_type == "奶茶类":
        tags.append("奶香")
    return list(dict.fromkeys(tag for tag in tags if tag))


def build_display_tags(recipe: dict) -> list[str]:
    tags = [
        classify_main_type(recipe),
        classify_food_origin(recipe),
        classify_regional_cuisine(recipe),
        classify_sub_type(recipe),
    ]
    tags.extend(normalize_seasonal_terms(recipe))
    tags.extend(parse_tags(recipe.get("flavor_tags", "")))
    tags.extend(parse_tags(recipe.get("scene_tags", "")))
    return list(dict.fromkeys(tag for tag in tags if tag))


def add_compatibility_fields(recipe: dict) -> dict:
    normalized = dict(recipe)
    normalized["main_type"] = classify_main_type(recipe)
    normalized["food_origin"] = classify_food_origin(recipe)
    normalized["regional_cuisine"] = classify_regional_cuisine(recipe)
    normalized["sub_type"] = classify_sub_type(recipe)
    normalized["flavor_tags"] = join_tags(simplify_flavor_tags(recipe))
    normalized["scene_tags"] = join_tags(simplify_scene_tags(recipe))
    normalized["feature_tags"] = join_tags(simplify_feature_tags(recipe))
    normalized["seasonal_terms"] = join_tags(normalize_seasonal_terms(recipe))

    normalized["cuisine"] = normalized["regional_cuisine"]
    normalized["staple_category"] = normalized["sub_type"]
    normalized["cuisine_group"] = classify_cuisine_group(recipe)
    normalized["beverage_category"] = classify_beverage_category(recipe)
    normalized["diet_tags"] = ""
    return normalized

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


def parse_tags(raw_value: str) -> list[str]:
    if raw_value is None or raw_value != raw_value:
        return []
    return [item.strip() for item in str(raw_value).split("|") if item.strip()]


def classify_staple_category(recipe: dict) -> str:
    name = str(recipe.get("name", ""))
    feature_tags = parse_tags(recipe.get("feature_tags", ""))
    cuisine = str(recipe.get("cuisine", ""))
    drink_exceptions = ["茶叶蛋", "茶香蛋", "茶香鸡丝", "茶饭", "茶冻"]

    if "饮品" in feature_tags or cuisine == "饮品":
        return "饮品"
    if (
        any(keyword in name for keyword in ["奶茶", "咖啡", "拿铁", "美式", "冷泡茶", "果茶", "气泡饮", "奶昔", "冰饮", "姜茶", "酸梅汤"])
        or (any(keyword in name for keyword in ["茶", "饮", "露"]) and not any(keyword in name for keyword in drink_exceptions))
    ):
        return "饮品"
    if "甜品" in feature_tags or "甜点心" in feature_tags or "甜品" in cuisine or "甜品" in name:
        return "甜品"
    if any(keyword in name for keyword in ["杯", "冻", "糕", "团", "糍粑", "汤圆", "挞", "圆子", "米团", "冰粉"]):
        return "甜品"
    if "汤锅" in feature_tags or any(keyword in name for keyword in ["火锅", "锅物", "部队锅", "豆乳锅"]):
        return "锅物"
    if "汤面" in feature_tags or any(
        keyword in name for keyword in ["面", "拉面", "乌冬", "荞麦面", "意面", "凉面"]
    ):
        return "面类"
    if any(keyword in name for keyword in ["米线", "河粉", "米粉", "炒粉", "酸辣粉", "凉粉", "粿条"]):
        return "粉类"
    if any(keyword in name for keyword in ["饭", "盖饭", "焗饭", "烩饭", "炒饭", "丼", "饭团"]):
        return "饭类"
    if "汤品" in feature_tags or any(keyword in name for keyword in ["粥", "羹", "汤"]):
        return "汤粥"
    if any(keyword in name for keyword in ["饼", "卷饼", "蛋饼", "可丽饼", "煎饼", "馅饼", "披萨", "春卷", "盒子", "饺", "馄饨"]):
        return "饼类"
    if any(keyword in name for keyword in ["三明治", "汉堡", "热狗", "贝果", "吐司", "可颂"]):
        return "面包三明治"
    if "轻食" in feature_tags or any(keyword in name for keyword in ["沙拉", "波奇", "藜麦碗", "酸奶杯"]):
        return "轻食"
    if any(keyword in name for keyword in ["司康", "蛋糕", "布丁", "奶冻", "千层", "派", "麻薯", "冰淇淋", "雪糕"]):
        return "甜品"
    return "菜肴"


def classify_cuisine_group(recipe: dict) -> str:
    cuisine = str(recipe.get("cuisine", ""))
    name = str(recipe.get("name", ""))

    if cuisine in {"川菜", "川味", "川式", "川黔"}:
        return "川渝湘辣"
    if cuisine in {"粤式", "港式", "港式甜品"}:
        return "粤港风味"
    if cuisine == "台式":
        return "台式风味"
    if cuisine == "日式":
        return "日式"
    if cuisine == "韩式":
        return "韩式"
    if cuisine in {"泰式", "东南亚", "东南亚甜品"}:
        return "东南亚风味"
    if cuisine in {"意式"} or "意面" in name or "披萨" in name:
        return "意式"
    if cuisine in {"西式"}:
        return "西式"
    if cuisine in {"轻食", "早午餐"}:
        return "轻食早午餐"
    if cuisine in {"烘焙", "甜品"}:
        return "甜品烘焙"
    if cuisine == "饮品":
        return "饮品特调"
    if cuisine in {"家常", "汤品", "热食", "冷盘", "夜宵"}:
        return "中式家常"
    if cuisine == "墨西哥风味":
        return "拉美风味"
    return "其他风味"


def classify_beverage_category(recipe: dict) -> str:
    name = str(recipe.get("name", ""))
    feature_tags = parse_tags(recipe.get("feature_tags", ""))

    if "饮品" not in feature_tags and recipe.get("staple_category") != "饮品":
        return ""
    if any(keyword in name for keyword in ["美式", "拿铁", "摩卡", "馥芮白", "咖啡"]):
        return "咖啡"
    if "奶茶" in name:
        return "奶茶"
    if "果茶" in name or (
        any(keyword in name for keyword in ["柠檬", "柚", "葡萄", "百香果", "草莓", "西瓜", "苹果"])
        and any(keyword in name for keyword in ["茶", "冷泡茶", "红茶", "绿茶", "乌龙", "茉莉"])
    ):
        return "果茶"
    if any(keyword in name for keyword in ["冷泡茶", "红茶", "绿茶", "乌龙", "茉莉", "茶"]):
        return "茶饮"
    if any(keyword in name for keyword in ["气泡饮", "苏打", "气泡"]):
        return "气泡饮"
    if any(keyword in name for keyword in ["奶昔", "冰沙", "酸奶昔"]):
        return "奶昔"
    if any(keyword in name for keyword in ["热饮", "热巧克力", "燕麦奶"]):
        return "热饮"
    if any(keyword in name for keyword in ["果汁", "冰饮"]):
        return "果饮"
    return "特调饮品"


def get_recipe_profile_tags(recipe: dict) -> list[str]:
    tags = parse_tags(recipe.get("flavor_tags", ""))
    beverage_category = recipe.get("beverage_category") or classify_beverage_category(recipe)
    name = str(recipe.get("name", ""))

    if any(keyword in name for keyword in ["酸辣", "酸汤", "泡菜", "柠檬"]):
        tags.append("酸口")
    if any(keyword in name for keyword in ["青梅", "酸梅"]):
        tags.append("酸甜")
    if any(keyword in name for keyword in ["酸辣", "麻辣", "香辣", "剁椒", "泡菜", "辣"]):
        tags.append("香辣")
    if beverage_category == "咖啡" and any(keyword in name for keyword in ["美式", "黑咖啡", "冷萃"]):
        tags.append("苦香")
    if beverage_category == "果茶":
        tags.extend(["果香", "酸甜", "清爽"])
    if beverage_category == "奶茶":
        tags.extend(["奶香", "甜香"])
    if beverage_category == "茶饮":
        tags.extend(["清淡", "回甘"])
    return list(dict.fromkeys(tag for tag in tags if tag))


def build_display_tags(recipe: dict) -> list[str]:
    tags = [
        recipe.get("staple_category") or classify_staple_category(recipe),
        recipe.get("cuisine_group") or classify_cuisine_group(recipe),
    ]
    beverage_category = recipe.get("beverage_category") or classify_beverage_category(recipe)
    if beverage_category:
        tags.append(beverage_category)
    feature_tags = parse_tags(recipe.get("feature_tags", ""))
    tags.extend([tag for tag in feature_tags if tag in SOLAR_TERMS])
    tags.extend(parse_tags(recipe.get("flavor_tags", "")))
    tags.extend(parse_tags(recipe.get("scene_tags", "")))
    return list(dict.fromkeys(tag for tag in tags if tag))

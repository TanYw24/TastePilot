NEGATION_MARKERS = ["不想吃", "不要", "不吃", "别", "避开", "去掉"]


def _is_negated_at(text: str, index: int) -> bool:
    window = text[max(0, index - 4) : index]
    return any(marker in window for marker in NEGATION_MARKERS)


def _has_positive_keyword(text: str, keyword: str) -> bool:
    start = 0
    while True:
        index = text.find(keyword, start)
        if index == -1:
            return False
        if not _is_negated_at(text, index):
            return True
        start = index + len(keyword)


def _any_positive_keyword(text: str, keywords: list[str]) -> bool:
    return any(_has_positive_keyword(text, keyword) for keyword in keywords)


def _base_parse(user_text: str) -> dict:
    text = user_text.strip().replace(" ", "")
    if not text:
        return {}

    def add_flavor(result_dict: dict, flavor: str) -> None:
        if flavor not in result_dict["favorite_flavors"]:
            result_dict["favorite_flavors"].append(flavor)
        if flavor not in result_dict["recognized_hints"]:
            result_dict["recognized_hints"].append(flavor)

    rules = {
        "favorite_flavors": {
            "辣": "香辣",
            "麻辣": "香辣",
            "酸甜": "酸甜",
            "清淡": "清淡",
            "清爽": "清淡",
            "爽口": "清淡",
            "蒜香": "蒜香",
            "鲜": "鲜香",
            "重口": "重口",
            "家常": "家常",
            "锅气": "家常",
            "酱香": "酱香",
            "甜": "甜香",
            "奶香": "奶香",
            "果香": "果香",
            "咸": "咸香",
        },
        "diet_goal": {
            "减脂": "减脂清爽",
            "健身": "高蛋白增肌",
            "增肌": "高蛋白增肌",
            "蛋白质": "高蛋白增肌",
            "高蛋白": "高蛋白增肌",
            "下饭": "下饭解馋",
            "聚餐": "朋友聚餐",
            "夜宵": "夜宵安慰",
        },
        "scene": {
            "一个人": "一个人吃",
            "自己吃": "一个人吃",
            "双人": "双人晚餐",
            "家庭": "家庭晚餐",
            "聚餐": "朋友聚餐",
            "健身": "健身准备餐",
            "深夜": "深夜加餐",
            "晚上": "深夜加餐",
            "下午茶": "下午茶",
            "甜品": "下午茶",
            "咖啡": "下午茶",
        },
        "budget_level": {
            "便宜": "低预算",
            "省钱": "低预算",
            "预算低": "低预算",
            "别太贵": "低预算",
            "不太贵": "低预算",
            "预算别太高": "低预算",
            "性价比": "低预算",
            "普通预算": "中等预算",
            "丰盛": "高预算",
        },
        "cooking_time_limit": {
            "10 分钟": "15 分钟内",
            "15 分钟": "15 分钟内",
            "快一点": "15 分钟内",
            "快点": "15 分钟内",
            "快手": "15 分钟内",
            "别太久": "30 分钟内",
            "不想等太久": "30 分钟内",
            "半小时": "30 分钟内",
            "30 分钟": "30 分钟内",
            "45 分钟": "45 分钟内",
            "1 小时": "60 分钟内",
        },
        "vegetarian_preference": {
            "素食": "严格素食",
            "少肉": "希望多素食",
        },
    }

    result = {"favorite_flavors": [], "recognized_hints": []}

    for keyword, flavor in rules["favorite_flavors"].items():
        if _has_positive_keyword(text, keyword) and flavor not in result["favorite_flavors"]:
            result["favorite_flavors"].append(flavor)
            result["recognized_hints"].append(flavor)

    for field in ["diet_goal", "scene", "budget_level", "cooking_time_limit", "vegetarian_preference"]:
        for keyword, normalized in rules[field].items():
            if _has_positive_keyword(text, keyword):
                result[field] = normalized
                result["recognized_hints"].append(normalized)
                break

    colloquial_flavor_phrases = {
        "香一点": "鲜香",
        "香香的": "鲜香",
        "够味": "重口",
        "有味道": "鲜香",
        "有满足感": "重口",
        "满足一点": "重口",
        "不腻": "清淡",
        "别太腻": "清淡",
        "轻一点": "清淡",
        "柔和一点": "奶香",
        "软乎一点": "家常",
        "暖呼呼": "家常",
    }
    for phrase, mapped_flavor in colloquial_flavor_phrases.items():
        if _has_positive_keyword(text, phrase):
            add_flavor(result, mapped_flavor)

    if _has_positive_keyword(text, "仪式感") and "高预算" not in result.get("recognized_hints", []):
        result["recognized_hints"].append("仪式感")
    if _has_positive_keyword(text, "清醒一点") and "15 分钟内" not in result.get("recognized_hints", []):
        result["recognized_hints"].append("想提神")

    if _has_positive_keyword(text, "有锅气") or _has_positive_keyword(text, "锅气一点"):
        add_flavor(result, "家常")

    if _has_positive_keyword(text, "顶饱") or _has_positive_keyword(text, "有饱腹感"):
        result["diet_goal"] = "均衡饮食"
        result["recognized_hints"].append("想吃得饱一点")

    avoid_markers = ["不要", "不吃", "别放", "去掉"]
    for marker in avoid_markers:
        if marker in text:
            tail = text.split(marker, maxsplit=1)[1].strip("，。 ")
            if tail:
                generic_tail = tail[:12]
                if "贵" in generic_tail:
                    result["budget_level"] = "低预算"
                    result["recognized_hints"].append("低预算")
                    continue
                if "油" in generic_tail:
                    if "清淡" not in result["favorite_flavors"]:
                        result["favorite_flavors"].append("清淡")
                    result["recognized_hints"].append("清淡")
                    continue
                if any(keyword in generic_tail for keyword in ["正餐", "主食", "盖饭", "饭", "面"]):
                    result["avoid_course_types"] = list(
                        dict.fromkeys(result.get("avoid_course_types", []) + ["main", "savory"])
                    )
                    result["recognized_hints"].append("避开正餐")
                    continue
                if "咸" in generic_tail:
                    result["avoid_course_types"] = list(
                        dict.fromkeys(result.get("avoid_course_types", []) + ["main", "savory"])
                    )
                    result["recognized_hints"].append("避开咸口")
                    continue
                if "甜" in generic_tail:
                    result["avoid_course_types"] = list(
                        dict.fromkeys(result.get("avoid_course_types", []) + ["dessert"])
                    )
                    result["recognized_hints"].append("避开甜品")
                    continue
                result["disliked_ingredients"] = generic_tail
                result["recognized_hints"].append(f"避开 {result['disliked_ingredients']}")
            break

    return result


def analyze_dining_request(user_text: str) -> dict:
    text = user_text.strip().replace(" ", "")
    if not text:
        return {}

    result = _base_parse(text)
    preferred_course_types = []
    avoid_course_types = result.get("avoid_course_types", [])
    intent_tags = []
    primary_bucket = None

    savory_markers = ["咸", "咸口", "正餐", "主食", "吃饭", "饭", "面", "盖饭", "热菜", "锅气"]
    sweet_markers = ["甜", "甜品", "蛋糕", "布丁", "小蛋糕", "甜点", "甜口"]
    drink_markers = ["喝", "咖啡", "饮品", "奶茶", "果汁", "果茶", "冷泡茶", "拿铁", "美式", "气泡饮"]
    dessert_markers = ["下午茶", "甜品", "小蛋糕", "茶点", "甜点"]
    light_meal_markers = ["沙拉", "轻食", "不油", "清爽", "轻盈"]
    warm_markers = ["热乎", "暖胃", "汤", "带汤", "热的", "热腾腾"]
    mood_profiles = [
        {
            "name": "安慰系",
            "markers": ["心情不好", "不开心", "emo", "很丧", "低落", "难过", "委屈", "想被安慰", "安慰一下"],
            "mood_bucket": "negative",
            "intent_tags": ["治愈", "奶香", "暖胃"],
            "search_tags": ["治愈", "奶香", "暖胃", "家常", "热乎", "甜品"],
        },
        {
            "name": "解压系",
            "markers": ["想解压发泄", "解压", "发泄", "压力大", "烦", "烦得很", "过瘾一点", "有满足感", "够味"],
            "mood_bucket": "craving",
            "intent_tags": ["解馋", "香辣", "重口"],
            "search_tags": ["解馋", "香辣", "重口", "下饭", "热食"],
            "preferred_course_types": ["main", "savory"],
            "avoid_course_types": ["drink"],
            "primary_bucket": "main",
        },
        {
            "name": "暖胃系",
            "markers": ["想暖胃", "暖胃", "热乎一点", "喝点热的", "想吃热的", "软乎一点", "暖呼呼"],
            "mood_bucket": "negative",
            "intent_tags": ["暖胃", "热乎", "治愈"],
            "search_tags": ["暖胃", "热乎", "汤面", "汤锅", "奶香", "治愈"],
            "preferred_course_types": ["main", "savory"],
            "avoid_course_types": ["dessert", "drink"],
            "primary_bucket": "main",
        },
        {
            "name": "提神系",
            "markers": ["想提神", "提神", "犯困", "没精神", "想清醒一点", "清醒一点"],
            "mood_bucket": "low_energy",
            "intent_tags": ["提神", "清爽", "咖啡搭子"],
            "search_tags": ["提神", "清爽", "果香", "咖啡搭子"],
            "preferred_course_types": ["drink"],
            "avoid_course_types": ["main", "dessert", "savory", "light_meal"],
            "primary_bucket": "drink",
        },
        {
            "name": "犒赏系",
            "markers": ["想奖励自己", "奖励自己", "犒赏一下", "庆祝一下", "有仪式感", "仪式感"],
            "mood_bucket": "positive",
            "intent_tags": ["仪式感", "治愈", "甜品"],
            "search_tags": ["仪式感", "精致", "治愈", "甜品", "奶香", "分享"],
        },
    ]

    explicit_drink_request = _any_positive_keyword(text, drink_markers)
    explicit_dessert_request = _any_positive_keyword(text, dessert_markers + sweet_markers)

    if _any_positive_keyword(text, savory_markers):
        preferred_course_types.extend(["main", "savory"])
        avoid_course_types.extend(["dessert", "drink"])
        result["recognized_hints"].append("偏正餐")
        intent_tags.extend(["正餐", "咸口"])
        primary_bucket = primary_bucket or "main"

    if _any_positive_keyword(text, sweet_markers):
        preferred_course_types.extend(["dessert", "snack"])
        avoid_course_types.extend(["main"])
        result["recognized_hints"].append("偏甜点")
        intent_tags.extend(["甜品", "甜口"])
        primary_bucket = primary_bucket or "dessert"

    if explicit_drink_request:
        preferred_course_types = ["drink"]
        avoid_course_types.extend(["main", "dessert", "savory", "light_meal"])
        result["recognized_hints"].append("偏饮品")
        intent_tags.append("饮品")
        primary_bucket = "drink"

    if _any_positive_keyword(text, dessert_markers):
        if "scene" not in result:
            result["scene"] = "下午茶"
        preferred_course_types.extend(["dessert", "snack"])
        intent_tags.extend(["下午茶", "甜品"])
        primary_bucket = primary_bucket or "dessert"

    if _has_positive_keyword(text, "安慰人") or _has_positive_keyword(text, "安慰一下"):
        intent_tags.extend(["治愈", "奶香"])
        result["recognized_hints"].append("想被安慰")
        result["mood_search_tags"] = list(dict.fromkeys(result.get("mood_search_tags", []) + ["治愈", "奶香", "暖胃", "甜品"]))
        result["mood_bucket"] = result.get("mood_bucket", "negative")
        result["mood_detected"] = result.get("mood_detected", "安慰系")

    if (_has_positive_keyword(text, "下午茶") or _has_positive_keyword(text, "甜甜的")) and not explicit_drink_request:
        preferred_course_types = [course_type for course_type in preferred_course_types if course_type != "drink"]
        avoid_course_types = [course_type for course_type in avoid_course_types if course_type != "dessert"]
        primary_bucket = "dessert" if explicit_dessert_request else primary_bucket

    if _has_positive_keyword(text, "有仪式感") or _has_positive_keyword(text, "仪式感"):
        intent_tags.extend(["仪式感", "精致"])
        result["recognized_hints"].append("偏精致")

    if _has_positive_keyword(text, "不腻") or _has_positive_keyword(text, "别太腻"):
        intent_tags.extend(["清爽", "轻负担"])

    if (
        _has_positive_keyword(text, "有满足感")
        or _has_positive_keyword(text, "满足一点")
        or _has_positive_keyword(text, "够味")
    ):
        intent_tags.extend(["解馋", "重口"])

    if _any_positive_keyword(text, light_meal_markers):
        preferred_course_types.append("light_meal")
        result["recognized_hints"].append("偏轻食")
        intent_tags.extend(["轻食", "清爽"])
        primary_bucket = primary_bucket or "light_meal"

    if _any_positive_keyword(text, warm_markers):
        preferred_course_types.extend(["main", "savory"])
        intent_tags.extend(["暖胃", "热乎", "汤面"])
        avoid_course_types.extend(["dessert", "drink"])
        result["recognized_hints"].append("偏热食")
        primary_bucket = primary_bucket or "main"

    matched_mood = None
    for profile in mood_profiles:
        if any(marker in text for marker in profile["markers"]):
            matched_mood = profile
            intent_tags.extend(profile["intent_tags"])
            result["mood_search_tags"] = profile["search_tags"]
            result["recognized_hints"].append(f"心情:{profile['name']}")
            result["mood_bucket"] = profile["mood_bucket"]

            for course_type in profile.get("preferred_course_types", []):
                if course_type not in preferred_course_types:
                    preferred_course_types.append(course_type)
            for course_type in profile.get("avoid_course_types", []):
                if course_type not in avoid_course_types:
                    avoid_course_types.append(course_type)
            if profile.get("primary_bucket"):
                primary_bucket = profile["primary_bucket"]

            if profile["mood_bucket"] == "negative" and not profile.get("preferred_course_types"):
                intent_tags.extend(["治愈", "暖胃"])
            if profile["mood_bucket"] == "low_energy":
                intent_tags.extend(["快手"])
            break

    tag_map = {
        "香辣": ["香辣", "解馋"],
        "清淡": ["清淡", "清爽"],
        "鲜香": ["鲜香"],
        "蒜香": ["蒜香"],
        "重口": ["重口", "解馋"],
        "家常": ["家常"],
        "酱香": ["家常"],
        "甜香": ["甜口", "甜品"],
        "奶香": ["奶香", "下午茶"],
        "果香": ["果香", "下午茶"],
        "咸香": ["咸口", "正餐"],
    }
    for flavor in result.get("favorite_flavors", []):
        intent_tags.extend(tag_map.get(flavor, []))

    scene_tag_map = {
        "一个人吃": ["一人食"],
        "双人晚餐": ["双人"],
        "家庭晚餐": ["家庭"],
        "朋友聚餐": ["聚餐", "分享"],
        "健身准备餐": ["高蛋白", "轻食"],
        "深夜加餐": ["夜宵", "暖胃"],
        "下午茶": ["下午茶", "茶点"],
    }
    if result.get("scene"):
        intent_tags.extend(scene_tag_map.get(result["scene"], []))

    if result.get("budget_level") == "低预算":
        intent_tags.append("省钱")
    if result.get("cooking_time_limit") == "15 分钟内":
        intent_tags.append("快手")
    if result.get("diet_goal") == "高蛋白增肌":
        intent_tags.append("高蛋白")
    if result.get("diet_goal") == "减脂清爽":
        intent_tags.extend(["轻食", "清爽"])
    if result.get("diet_goal") == "下饭解馋":
        intent_tags.extend(["下饭", "解馋"])
    if result.get("diet_goal") == "夜宵安慰":
        intent_tags.extend(["夜宵", "治愈"])
    if result.get("vegetarian_preference") in ["严格素食", "希望多素食"]:
        intent_tags.append("素食友好")

    result["preferred_course_types"] = list(dict.fromkeys(preferred_course_types))
    result["avoid_course_types"] = list(dict.fromkeys(avoid_course_types))
    result["intent_tags"] = list(dict.fromkeys(intent_tags))
    if result.get("mood_search_tags"):
        result["mood_search_tags"] = list(dict.fromkeys(result["mood_search_tags"]))
    if matched_mood:
        result["mood_detected"] = matched_mood["name"]
    if primary_bucket:
        result["primary_bucket"] = primary_bucket
    result["recognized_hints"] = list(dict.fromkeys(result.get("recognized_hints", [])))

    if not result["recognized_hints"]:
        return {}
    return result


def parse_free_text_request(user_text: str) -> dict:
    return analyze_dining_request(user_text)

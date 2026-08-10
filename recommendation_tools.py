import random

import pandas as pd

from db import (
    get_all_recipes,
    get_favorite_recipes,
    get_profile_feedback_summary,
    get_recent_query_signals,
    get_recent_user_actions,
    get_recipe_record_by_id,
    get_user_action_counts,
    get_user_preferences,
    init_db,
    postgres_recipes_available,
    record_action,
    record_query_signal,
)
from recipe_taxonomy import (
    build_display_tags,
    classify_beverage_category,
    classify_main_type,
    classify_staple_category,
    get_recipe_profile_tags,
    SOLAR_TERMS,
    parse_tags,
)
_RECIPES_CACHE = None
_BUDGET_RANK = {"低预算": 1, "中等预算": 2, "高预算": 3}
_TIME_RANK = {"15 分钟内": 15, "30 分钟内": 30, "45 分钟内": 45, "60 分钟内": 60}
_PROFILE_ACTION_WEIGHTS = {"favorite": 5.5, "view": 2.4, "skip": -3.8}
_PROFILE_FEEDBACK_WEIGHTS = {"confirm": 4.5, "downvote": -5.5}
_TIME_SLOT_LABELS = ["早餐", "午餐", "下午茶", "晚餐", "夜宵"]

init_db()


def budget_options() -> list[str]:
    return ["低预算", "中等预算", "高预算"]


def cooking_time_options() -> list[str]:
    return ["15 分钟内", "30 分钟内", "45 分钟内", "60 分钟内"]


def diet_goal_options() -> list[str]:
    return ["均衡饮食", "减脂清爽", "高蛋白增肌", "下饭解馋", "朋友聚餐", "夜宵安慰"]


def scene_options() -> list[str]:
    return ["一个人吃", "双人晚餐", "家庭晚餐", "朋友聚餐", "健身准备餐", "深夜加餐"]


def vegetarian_options() -> list[str]:
    return ["不限", "希望多素食", "严格素食"]


def load_recipes() -> pd.DataFrame:
    global _RECIPES_CACHE
    if _RECIPES_CACHE is None:
        _RECIPES_CACHE = pd.DataFrame(get_all_recipes())
    return _RECIPES_CACHE.copy()


def get_recipe_by_id(recipe_id: int) -> dict | None:
    recipe = get_recipe_record_by_id(recipe_id)
    if recipe is None:
        return None
    recipe["display_tags"] = build_display_tags(recipe)
    return recipe


def reset_recipe_cache() -> None:
    global _RECIPES_CACHE
    _RECIPES_CACHE = None


def get_recipe_feature_tags(recipe: dict) -> list[str]:
    return parse_tags(recipe.get("feature_tags", ""))


def get_recipe_search_tags(recipe: dict) -> list[str]:
    beverage_category = recipe.get("beverage_category") or classify_beverage_category(recipe)
    extra_tags = [beverage_category] if beverage_category else []
    return list(
        dict.fromkeys(
            get_recipe_feature_tags(recipe)
            + get_recipe_profile_tags(recipe)
            + parse_tags(recipe.get("scene_tags", ""))
            + extra_tags
        )
    )


def _count_tag_overlap(recipe_tags: list[str], target_tags: list[str]) -> int:
    return sum(1 for tag in target_tags if tag in recipe_tags)


def get_recipe_time_slots(recipe: dict) -> list[str]:
    scene_tags = set(parse_tags(recipe.get("scene_tags", "")))
    feature_tags = set(parse_tags(recipe.get("feature_tags", "")))

    slots = []
    if {"早餐", "早上"}.intersection(scene_tags) or "早午餐" in feature_tags:
        slots.append("早餐")
    if "夏日午餐" in scene_tags or "早午餐" in feature_tags:
        slots.append("午餐")
    if {"下午茶", "夏日午后"}.intersection(scene_tags) or {"下午茶", "茶点", "咖啡搭子"}.intersection(feature_tags):
        slots.append("下午茶")
    if {"双人晚餐", "家庭晚餐", "朋友聚餐", "冬日夜晚"}.intersection(scene_tags) or {"家庭", "聚餐", "正餐", "热食"}.intersection(feature_tags):
        slots.append("晚餐")
    if "深夜加餐" in scene_tags or "夜宵" in feature_tags:
        slots.append("夜宵")
    return list(dict.fromkeys(slots))


def get_scene_time_slot(scene: str) -> str:
    mapping = {
        "早上": "早餐",
        "早餐": "早餐",
        "夏日午餐": "午餐",
        "下午茶": "下午茶",
        "夏日午后": "下午茶",
        "双人晚餐": "晚餐",
        "家庭晚餐": "晚餐",
        "朋友聚餐": "晚餐",
        "冬日夜晚": "晚餐",
        "深夜加餐": "夜宵",
    }
    return mapping.get(scene, "")


def _confidence_label(signal_count: float) -> str:
    if signal_count >= 22:
        return "画像已经比较稳定了，我大致知道你最近的口味重心。"
    if signal_count >= 10:
        return "画像正在逐渐成形，最近几次选择已经能看出明显倾向。"
    return "我还在继续认识你，先根据少量行为和长期偏好做判断。"


def _top_profile_items(score_map: dict[str, float], limit: int = 4) -> list[dict]:
    ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
    return [{"label": label, "score": round(score, 2)} for label, score in ranked[:limit] if score > 0]


def build_user_profile(user_id: int) -> dict:
    preferences = get_user_preferences(user_id)
    recipes = load_recipes().set_index("id")
    feedback_summary = get_profile_feedback_summary(user_id)
    recent_actions = get_recent_user_actions(user_id, limit=120)
    recent_queries = get_recent_query_signals(user_id, limit=40)

    flavor_scores: dict[str, float] = {}
    cuisine_scores: dict[str, float] = {}
    time_slot_scores: dict[str, float] = {}
    signal_count = 0.0

    for flavor in [item for item in preferences.get("favorite_flavors", "").split("|") if item]:
        flavor_scores[flavor] = flavor_scores.get(flavor, 0) + 6.5
        signal_count += 0.6

    for index, action in enumerate(recent_actions):
        recipe_id = action.get("recipe_id")
        if recipe_id not in recipes.index:
            continue

        recipe = recipes.loc[recipe_id].to_dict()
        recency_factor = max(0.35, 1 - index * 0.018)
        weight = _PROFILE_ACTION_WEIGHTS.get(action["action_type"], 0) * recency_factor
        signal_count += abs(weight) * 0.35

        for flavor in get_recipe_profile_tags(recipe):
            flavor_scores[flavor] = flavor_scores.get(flavor, 0) + weight

        cuisine_group = recipe.get("cuisine_group")
        if cuisine_group:
            cuisine_scores[cuisine_group] = cuisine_scores.get(cuisine_group, 0) + weight * 0.95

        for slot in get_recipe_time_slots(recipe):
            time_slot_scores[slot] = time_slot_scores.get(slot, 0) + weight * 0.85

    for index, signal in enumerate(recent_queries):
        recency_factor = max(0.3, 1 - index * 0.045)
        for flavor in parse_tags(signal.get("flavor_tags", "")):
            flavor_scores[flavor] = flavor_scores.get(flavor, 0) + 1.8 * recency_factor
            signal_count += 0.2
        for cuisine_group in parse_tags(signal.get("cuisine_groups", "")):
            cuisine_scores[cuisine_group] = cuisine_scores.get(cuisine_group, 0) + 1.65 * recency_factor
            signal_count += 0.2
        slot = get_scene_time_slot(signal.get("scene", ""))
        if slot:
            time_slot_scores[slot] = time_slot_scores.get(slot, 0) + 1.4 * recency_factor
            signal_count += 0.18

    for (profile_type, profile_value), feedback_counts in feedback_summary.items():
        delta = (
            feedback_counts.get("confirm", 0) * _PROFILE_FEEDBACK_WEIGHTS["confirm"]
            + feedback_counts.get("downvote", 0) * _PROFILE_FEEDBACK_WEIGHTS["downvote"]
        )
        if profile_type == "flavor":
            flavor_scores[profile_value] = flavor_scores.get(profile_value, 0) + delta
        elif profile_type == "cuisine":
            cuisine_scores[profile_value] = cuisine_scores.get(profile_value, 0) + delta
        elif profile_type == "time_slot":
            time_slot_scores[profile_value] = time_slot_scores.get(profile_value, 0) + delta

    top_flavors = _top_profile_items(flavor_scores, limit=4)
    top_cuisines = _top_profile_items(cuisine_scores, limit=4)
    active_time_slots = _top_profile_items(time_slot_scores, limit=3)

    explanations = []
    if top_flavors:
        explanations.append(f"最近最稳定的口味偏向是 {', '.join(item['label'] for item in top_flavors[:2])}。")
    if top_cuisines:
        explanations.append(f"菜系上更常靠近 {', '.join(item['label'] for item in top_cuisines[:2])}。")
    if active_time_slots:
        explanations.append(f"更常在 {active_time_slots[0]['label']} 这个时段来找吃的。")
    if not explanations:
        explanations.append("当前行为还不多，我先用你的长期偏好做一张初始画像。")

    return {
        "top_flavors": top_flavors,
        "top_cuisines": top_cuisines,
        "active_time_slots": active_time_slots,
        "confidence_summary": _confidence_label(signal_count),
        "profile_explanations": explanations,
        "signal_strength": round(signal_count, 2),
    }


def _profile_bonus(recipe: dict, request: dict, profile: dict | None) -> tuple[float, list[str]]:
    if not profile:
        return 0.0, []

    has_strong_current_intent = bool(
        request.get("current_input_flavors")
        or request.get("current_input_cuisine_groups")
        or request.get("current_input_scene")
        or request.get("required_flavors")
        or request.get("mood_search_tags")
    )
    scale = 0.42 if has_strong_current_intent else 1.0

    flavor_weights = {item["label"]: item["score"] for item in profile.get("top_flavors", [])}
    cuisine_weights = {item["label"]: item["score"] for item in profile.get("top_cuisines", [])}
    time_weights = {item["label"]: item["score"] for item in profile.get("active_time_slots", [])}

    bonus = 0.0
    reasons = []

    matched_flavors = [tag for tag in get_recipe_profile_tags(recipe) if tag in flavor_weights]
    if matched_flavors:
        flavor_bonus = sum(min(flavor_weights[tag], 14) for tag in matched_flavors[:2]) * 0.8 * scale
        bonus += flavor_bonus
        reasons.append(f"也贴近你最近常选的 {', '.join(matched_flavors[:2])}")

    cuisine_group = recipe.get("cuisine_group")
    if cuisine_group in cuisine_weights:
        bonus += min(cuisine_weights[cuisine_group], 12) * 0.75 * scale
        reasons.append(f"菜系上靠近你最近偏爱的 {cuisine_group}")

    recipe_slots = get_recipe_time_slots(recipe)
    matched_slots = [slot for slot in recipe_slots if slot in time_weights]
    if matched_slots:
        bonus += min(time_weights[matched_slots[0]], 10) * 0.65 * scale
        reasons.append(f"也符合你常在 {matched_slots[0]} 想吃的节奏")

    return bonus, reasons[:2]


def matches_primary_bucket(recipe: dict, primary_bucket: str) -> bool:
    feature_tags = get_recipe_feature_tags(recipe)
    main_type = recipe.get("main_type") or classify_main_type(recipe)
    mapping = {
        "drink": {"饮品"},
        "dessert": {"甜品点心"},
        "main": {"正餐主食", "家常菜肴", "汤锅粥羹"},
        "staple": {"正餐主食"},
        "dish": {"家常菜肴"},
        "soup_hotpot": {"汤锅粥羹"},
        "light_meal": {"轻食早午餐"},
    }
    target_main_types = mapping.get(primary_bucket, set())
    if main_type in target_main_types:
        return True

    fallback_tags = {
        "drink": {"饮品"},
        "dessert": {"甜品", "甜点心", "下午茶", "茶点"},
        "main": {"正餐", "轻正餐", "汤面", "汤锅", "热食", "早午餐"},
        "staple": {"正餐", "主食", "饭类", "面类", "粉类", "饼类"},
        "dish": {"正餐", "下饭", "家常", "热食"},
        "soup_hotpot": {"汤面", "汤锅", "汤品", "暖胃"},
        "light_meal": {"轻食", "轻正餐", "早午餐"},
    }.get(primary_bucket, set())
    return bool(fallback_tags.intersection(feature_tags))


def infer_course_types(recipe: dict) -> list[str]:
    name = str(recipe.get("name", ""))
    cuisine = str(recipe.get("cuisine", ""))
    scene_tags = parse_tags(recipe.get("scene_tags", ""))
    flavor_tags = parse_tags(recipe.get("flavor_tags", ""))
    staple_category = recipe.get("staple_category") or classify_staple_category(recipe)
    main_type = recipe.get("main_type") or classify_main_type(recipe)

    course_types = []
    dessert_keywords = ["蛋糕", "布丁", "甜品", "派", "司康", "奶冻", "千层", "甘露", "盒子", "糯米饭"]
    drink_keywords = ["咖啡", "奶茶", "果汁", "茶"]
    light_keywords = ["沙拉", "藜麦", "吐司", "酸奶杯"]
    savory_keywords = ["饭", "面", "锅", "汤", "豆腐", "牛肉", "鸡翅", "乌冬"]

    if main_type == "甜品点心" or staple_category == "甜品" or "下午茶" in scene_tags or "甜品" in cuisine or "烘焙" in cuisine or any(
        keyword in name for keyword in dessert_keywords
    ):
        course_types.append("dessert")
    if main_type == "饮品" or staple_category == "饮品" or any(keyword in name for keyword in drink_keywords):
        course_types.append("drink")
    if main_type == "轻食早午餐" or staple_category == "轻食" or any(keyword in name for keyword in light_keywords):
        course_types.append("light_meal")
    if main_type in {"正餐主食", "家常菜肴", "汤锅粥羹"} or staple_category in {"饭类", "面类", "粉类", "饼类", "锅物", "汤粥", "面包三明治", "菜肴"} or any(
        keyword in name for keyword in savory_keywords
    ) or "下饭解馋" in parse_tags(recipe.get("diet_tags", "")):
        course_types.extend(["main", "savory"])
    if "甜香" in flavor_tags or "奶香" in flavor_tags or "果香" in flavor_tags:
        course_types.append("sweet")
    if "香辣" in flavor_tags or "鲜香" in flavor_tags or "家常" in flavor_tags or "咸香" in flavor_tags:
        course_types.append("savory")

    if not course_types:
        course_types.append("main")
    return list(dict.fromkeys(course_types))


def _merge_preference_query(query: dict, preferences: dict) -> dict:
    merged = {}
    merged["current_input_flavors"] = query.get("favorite_flavors", [])
    merged["current_input_cuisine_groups"] = query.get("cuisine_groups", [])
    merged["current_input_scene"] = query.get("scene", "")
    merged["favorite_flavors"] = list(
        dict.fromkeys(
            [tag for tag in preferences.get("favorite_flavors", "").split("|") if tag]
            + query.get("favorite_flavors", [])
        )
    )
    merged["required_flavors"] = query.get("required_flavors", [])
    merged["disliked_ingredients"] = "、".join(
        filter(None, [preferences.get("disliked_ingredients", ""), query.get("disliked_ingredients", "")])
    )
    merged["diet_goal"] = query.get("diet_goal") or preferences.get("diet_goal") or "均衡饮食"
    merged["budget_level"] = query.get("budget_level") or preferences.get("budget_level") or "中等预算"
    merged["cooking_time_limit"] = (
        query.get("cooking_time_limit") or preferences.get("cooking_time_limit") or "30 分钟内"
    )
    merged["vegetarian_preference"] = (
        query.get("vegetarian_preference") or preferences.get("vegetarian_preference") or "不限"
    )
    merged["scene"] = query.get("scene") or "一个人吃"
    merged["preferred_course_types"] = query.get("preferred_course_types", [])
    merged["avoid_course_types"] = query.get("avoid_course_types", [])
    merged["intent_tags"] = query.get("intent_tags", [])
    merged["mood_search_tags"] = query.get("mood_search_tags", [])
    merged["primary_bucket"] = query.get("primary_bucket")
    merged["mood_bucket"] = query.get("mood_bucket")
    merged["mood_detected"] = query.get("mood_detected")
    merged["beverage_categories"] = query.get("beverage_categories", [])
    merged["main_types"] = query.get("main_types", [])
    merged["staple_categories"] = query.get("staple_categories", [])
    merged["solar_terms"] = query.get("solar_terms", [])
    merged["cuisine_groups"] = query.get("cuisine_groups", [])
    return merged


def _allowed_by_budget(recipe_budget: str, target_budget: str) -> bool:
    return _BUDGET_RANK.get(recipe_budget, 2) <= _BUDGET_RANK.get(target_budget, 2)


def _allowed_by_time(cook_time_minutes: int, target_time: str) -> bool:
    return int(cook_time_minutes) <= _TIME_RANK.get(target_time, 30)


def _contains_any_avoids(ingredients: str, disliked_ingredients: str) -> bool:
    if not disliked_ingredients:
        return False
    ingredient_text = str(ingredients)
    avoids = [
        item.strip()
        for item in disliked_ingredients.replace("，", "、").replace(",", "、").split("、")
        if item.strip()
    ]
    return any(item in ingredient_text for item in avoids)


def _matches_flavor_intent(recipe: dict, flavor: str) -> bool:
    recipe_flavors = get_recipe_profile_tags(recipe)
    if flavor in recipe_flavors:
        return True
    if flavor == "香辣" and int(recipe.get("is_spicy") or 0) == 1:
        return True
    return False


def _score_recipe(recipe: dict, request: dict, favorite_counts: dict, skip_counts: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    recipe_flavors = get_recipe_profile_tags(recipe)
    recipe_scenes = parse_tags(recipe["scene_tags"])
    recipe_diets = parse_tags(recipe["diet_tags"])
    course_types = infer_course_types(recipe)
    feature_tags = get_recipe_feature_tags(recipe)
    search_tags = get_recipe_search_tags(recipe)
    solar_terms = request.get("solar_terms", [])

    flavor_overlap = [tag for tag in request["favorite_flavors"] if tag in recipe_flavors]
    if flavor_overlap:
        score += 24 + 8 * min(len(flavor_overlap), 2)
        reasons.append(f"口味上贴近你偏好的 {'、'.join(flavor_overlap)}")

    current_flavor_overlap = [
        tag for tag in request.get("current_input_flavors", []) if _matches_flavor_intent(recipe, tag)
    ]
    if current_flavor_overlap:
        score += 34 + 10 * min(len(current_flavor_overlap), 2)
        reasons.insert(0, f"优先满足你这次想要的 {'、'.join(current_flavor_overlap)}")

    if request["scene"] in recipe_scenes:
        score += 20
        reasons.append(f"很适合“{request['scene']}”这个场景")

    if request["diet_goal"] in recipe_diets:
        score += 18
        reasons.append(f"符合你今天想要的“{request['diet_goal']}”方向")

    if recipe["budget_level"] == request["budget_level"]:
        score += 14
        reasons.append("预算和你今天的计划一致")
    elif _allowed_by_budget(recipe["budget_level"], request["budget_level"]):
        score += 8

    time_limit = _TIME_RANK.get(request["cooking_time_limit"], 30)
    if int(recipe["cook_time_minutes"]) <= time_limit:
        score += 14
        reasons.append("做起来不会太占时间")

    mood_search_tags = request.get("mood_search_tags", [])
    if mood_search_tags:
        mood_overlap = [tag for tag in mood_search_tags if tag in search_tags]
        if mood_overlap:
            score += 26 + 6 * min(len(mood_overlap), 3)
            reasons.append(f"更贴近这次想要的 {' / '.join(mood_overlap[:3])} 氛围")

    intent_tags = request.get("intent_tags", [])
    if intent_tags:
        overlap_tags = [tag for tag in intent_tags if tag in feature_tags]
        if overlap_tags:
            score += 18 + 6 * min(len(overlap_tags), 3)
            reasons.append(f"标签上匹配到 {' / '.join(overlap_tags[:3])}")

    if solar_terms:
        term_overlap = [tag for tag in solar_terms if tag in feature_tags]
        if term_overlap:
            score += 34
            reasons.append(f"正好对应 {term_overlap[0]} 这段时令和习俗")

    preferred_course_types = request.get("preferred_course_types", [])
    avoid_course_types = request.get("avoid_course_types", [])
    if preferred_course_types:
        overlap = [item for item in preferred_course_types if item in course_types]
        if overlap:
            score += 26
            reasons.append(f"类型上更接近你现在想吃的 {' / '.join(overlap[:2])}")
        else:
            score -= 12
    if avoid_course_types:
        blocked = [item for item in avoid_course_types if item in course_types]
        if blocked:
            score -= 42

    if favorite_counts.get(recipe["id"], 0):
        score += 10
        reasons.append("你之前收藏过相似口味的菜")

    if skip_counts.get(recipe["id"], 0):
        score -= 18

    mood_bucket = request.get("mood_bucket")
    if mood_bucket == "negative":
        comfort_tags = {"治愈", "暖胃", "奶香", "家常", "热乎"}
        overlap = comfort_tags.intersection(feature_tags)
        if overlap:
            score += 22 + 4 * min(len(overlap), 2)
            reasons.append(f"更像是在这种状态下会想吃的 {' / '.join(list(overlap)[:2])} 方向")
    elif mood_bucket == "low_energy":
        energy_tags = {"快手", "高蛋白", "提神"}
        overlap = energy_tags.intersection(feature_tags)
        if overlap:
            score += 18
            reasons.append("更适合现在想省点力气、又想快点吃到的状态")
    elif mood_bucket == "positive":
        vibe_tags = {"仪式感", "分享", "聚餐"}
        overlap = vibe_tags.intersection(feature_tags)
        if overlap:
            score += 16
            reasons.append("更符合想让这顿饭更有氛围感的心情")

    return score, reasons


def _diversified_pick(ranked: list[dict], limit: int) -> list[dict]:
    if len(ranked) <= limit:
        return ranked

    picked = []
    remaining = ranked[:]
    while remaining and len(picked) < limit:
        top_score = remaining[0]["score"]
        score_window = [item for item in remaining if item["score"] >= top_score - 10]
        candidate_pool = score_window[: min(len(score_window), 8)]
        chosen = random.choice(candidate_pool)
        picked.append(chosen)

        chosen_scene_tags = set(parse_tags(chosen["scene_tags"]))
        filtered = []
        for item in remaining:
            same_scene = bool(chosen_scene_tags.intersection(parse_tags(item["scene_tags"])))
            same_name = item["id"] == chosen["id"]
            if same_name:
                continue
            if same_scene and len(filtered) + len(picked) < limit:
                item = item.copy()
                item["score"] -= 3
            filtered.append(item)
        remaining = sorted(filtered, key=lambda item: item["score"], reverse=True)

    return picked


def recommend_recipes(
    query: dict,
    preferences: dict,
    user_id: int,
    limit: int = 4,
    exclude_recipe_ids: list[int] | None = None,
) -> list[dict]:
    request = _merge_preference_query(query, preferences)
    recipes = load_recipes()
    exclude_recipe_ids = exclude_recipe_ids or []

    recipes = recipes[
        recipes.apply(
            lambda row: _allowed_by_budget(row["budget_level"], request["budget_level"])
            and _allowed_by_time(row["cook_time_minutes"], request["cooking_time_limit"])
            and not _contains_any_avoids(row["ingredients"], request["disliked_ingredients"]),
            axis=1,
        )
    ]

    if exclude_recipe_ids:
        recipes = recipes[~recipes["id"].isin(exclude_recipe_ids)]

    if request["vegetarian_preference"] == "严格素食":
        recipes = recipes[recipes["is_vegetarian"] == 1]
    elif request["vegetarian_preference"] == "希望多素食":
        recipes = recipes.sort_values(by="is_vegetarian", ascending=False)

    if recipes.empty:
        return []

    preferred_course_types = request.get("preferred_course_types", [])
    avoid_course_types = request.get("avoid_course_types", [])
    intent_tags = request.get("intent_tags", [])
    mood_search_tags = request.get("mood_search_tags", [])
    primary_bucket = request.get("primary_bucket")
    main_types = request.get("main_types", [])
    staple_categories = request.get("staple_categories", [])
    beverage_categories = request.get("beverage_categories", [])
    solar_terms = request.get("solar_terms", [])
    cuisine_groups = request.get("cuisine_groups", [])
    required_flavors = request.get("required_flavors", [])
    current_input_flavors = request.get("current_input_flavors", [])

    recipes["course_types"] = recipes.apply(lambda row: infer_course_types(row.to_dict()), axis=1)
    if "main_type" not in recipes.columns:
        recipes["main_type"] = recipes.apply(lambda row: classify_main_type(row.to_dict()), axis=1)
    if "beverage_category" not in recipes.columns:
        recipes["beverage_category"] = recipes.apply(lambda row: classify_beverage_category(row.to_dict()), axis=1)

    if main_types:
        main_type_filtered = recipes[recipes["main_type"].isin(main_types)]
        if not main_type_filtered.empty:
            recipes = main_type_filtered.copy()

    if staple_categories:
        staple_filtered = recipes[recipes["staple_category"].isin(staple_categories)]
        if not staple_filtered.empty:
            recipes = staple_filtered.copy()

    if primary_bucket:
        strict_bucket = recipes[
            recipes.apply(lambda row: matches_primary_bucket(row.to_dict(), primary_bucket), axis=1)
        ]
        if not strict_bucket.empty:
            recipes = strict_bucket.copy()

    if beverage_categories:
        drink_filtered = recipes[recipes["beverage_category"].isin(beverage_categories)]
        if not drink_filtered.empty:
            recipes = drink_filtered.copy()

    if cuisine_groups:
        cuisine_filtered = recipes[recipes["cuisine_group"].isin(cuisine_groups)]
        if not cuisine_filtered.empty:
            recipes = cuisine_filtered.copy()

    if current_input_flavors:
        recipes["profile_flavor_tags"] = recipes.apply(lambda row: get_recipe_profile_tags(row.to_dict()), axis=1)
        flavor_intent_filtered = recipes[
            recipes.apply(
                lambda row: any(
                    _matches_flavor_intent(row.to_dict(), flavor)
                    for flavor in current_input_flavors
                ),
                axis=1,
            )
        ]
        if len(flavor_intent_filtered) >= max(limit, 3):
            recipes = flavor_intent_filtered.copy()

    if required_flavors:
        if "profile_flavor_tags" not in recipes.columns:
            recipes["profile_flavor_tags"] = recipes.apply(lambda row: get_recipe_profile_tags(row.to_dict()), axis=1)
        flavor_filtered = recipes[
            recipes["profile_flavor_tags"].apply(
                lambda tags: all(required_flavor in tags for required_flavor in required_flavors)
            )
        ]
        if not flavor_filtered.empty:
            recipes = flavor_filtered.copy()

    if solar_terms:
        recipes["feature_tags_list"] = recipes.apply(lambda row: get_recipe_feature_tags(row.to_dict()), axis=1)
        seasonal_filtered = recipes[
            recipes["feature_tags_list"].apply(lambda tags: any(solar_term in tags for solar_term in solar_terms))
        ]
        if not seasonal_filtered.empty:
            recipes = seasonal_filtered.copy()

    if mood_search_tags:
        recipes["search_tags_list"] = recipes.apply(lambda row: get_recipe_search_tags(row.to_dict()), axis=1)
        recipes["mood_overlap_count"] = recipes["search_tags_list"].apply(
            lambda recipe_tags: _count_tag_overlap(recipe_tags, mood_search_tags)
        )
        strong_mood_tagged = recipes[recipes["mood_overlap_count"] >= 2]
        mood_tagged = recipes[recipes["mood_overlap_count"] >= 1]
        if len(strong_mood_tagged) >= max(limit, 3):
            recipes = strong_mood_tagged.copy()
        if len(mood_tagged) >= max(limit, 3):
            recipes = mood_tagged.copy()

    if intent_tags:
        if "feature_tags_list" not in recipes.columns:
            recipes["feature_tags_list"] = recipes.apply(lambda row: get_recipe_feature_tags(row.to_dict()), axis=1)
        tagged = recipes[
            recipes["feature_tags_list"].apply(
                lambda feature_tags: any(tag in feature_tags for tag in intent_tags)
            )
        ]
        if request.get("mood_bucket"):
            if len(tagged) >= max(limit, 3):
                recipes = tagged.copy()
        elif len(tagged) >= max(limit * 2, 6):
            recipes = tagged.copy()

    if avoid_course_types:
        filtered = recipes[
            recipes["course_types"].apply(
                lambda course_types: not any(course_type in course_types for course_type in avoid_course_types)
            )
        ]
        if not filtered.empty:
            recipes = filtered.copy()

    if preferred_course_types:
        focused = recipes[
            recipes["course_types"].apply(
                lambda course_types: any(course_type in course_types for course_type in preferred_course_types)
            )
        ]
        if len(focused) >= max(limit, 3):
            recipes = focused.copy()

    favorite_counts = get_user_action_counts(user_id, "favorite")
    skip_counts = get_user_action_counts(user_id, "skip")
    favorite_recipe_ids = set(get_favorite_recipes(user_id))
    profile = build_user_profile(user_id)

    ranked = []
    for _, row in recipes.iterrows():
        recipe = row.to_dict()
        score, reasons = _score_recipe(recipe, request, favorite_counts, skip_counts)
        profile_bonus, profile_reasons = _profile_bonus(recipe, request, profile)
        score += profile_bonus
        reasons.extend(profile_reasons)
        if recipe["id"] in favorite_recipe_ids:
            score += 8
        score += random.uniform(0, 2.5)
        recipe["score"] = score
        recipe["reason"] = "；".join(reasons[:3]) if reasons else "整体条件比较均衡，适合作为今天的候选菜。"
        recipe["display_tags"] = build_display_tags(recipe)
        ranked.append(recipe)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    picked = _diversified_pick(ranked, limit)

    for recipe in picked:
        record_action(user_id, recipe["id"], "view")

    return picked


def persist_query_profile_signal(user_id: int, query: dict) -> None:
    record_query_signal(
        user_id,
        flavor_tags=query.get("favorite_flavors", []),
        cuisine_groups=query.get("cuisine_groups", []),
        scene=query.get("scene", ""),
    )

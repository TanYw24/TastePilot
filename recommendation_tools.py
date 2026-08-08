from pathlib import Path
import random

import pandas as pd

from db import get_favorite_recipes, get_user_action_counts, record_action
from recipe_taxonomy import (
    build_display_tags,
    classify_beverage_category,
    classify_staple_category,
    get_recipe_profile_tags,
    SOLAR_TERMS,
    parse_tags,
)
DATA_PATH = Path(__file__).resolve().parent / "data" / "recipes.csv"
_RECIPES_CACHE = None
_BUDGET_RANK = {"低预算": 1, "中等预算": 2, "高预算": 3}
_TIME_RANK = {"15 分钟内": 15, "30 分钟内": 30, "45 分钟内": 45, "60 分钟内": 60}


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
        _RECIPES_CACHE = pd.read_csv(DATA_PATH)
    return _RECIPES_CACHE.copy()
def get_recipe_by_id(recipe_id: int) -> dict | None:
    recipes = load_recipes()
    match = recipes[recipes["id"] == recipe_id]
    if match.empty:
        return None
    recipe = match.iloc[0].to_dict()
    recipe["display_tags"] = build_display_tags(recipe)
    return recipe


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


def matches_primary_bucket(recipe: dict, primary_bucket: str) -> bool:
    feature_tags = get_recipe_feature_tags(recipe)
    mapping = {
        "drink": {"饮品"},
        "dessert": {"甜品", "甜点心", "下午茶", "茶点"},
        "main": {"正餐", "轻正餐", "汤面", "汤锅", "热食", "早午餐"},
        "light_meal": {"轻食", "轻正餐", "早午餐"},
    }
    target_tags = mapping.get(primary_bucket, set())
    return bool(target_tags.intersection(feature_tags))


def infer_course_types(recipe: dict) -> list[str]:
    name = str(recipe.get("name", ""))
    cuisine = str(recipe.get("cuisine", ""))
    scene_tags = parse_tags(recipe.get("scene_tags", ""))
    flavor_tags = parse_tags(recipe.get("flavor_tags", ""))
    staple_category = recipe.get("staple_category") or classify_staple_category(recipe)

    course_types = []
    dessert_keywords = ["蛋糕", "布丁", "甜品", "派", "司康", "奶冻", "千层", "甘露", "盒子", "糯米饭"]
    drink_keywords = ["咖啡", "奶茶", "果汁", "茶"]
    light_keywords = ["沙拉", "藜麦", "吐司", "酸奶杯"]
    savory_keywords = ["饭", "面", "锅", "汤", "豆腐", "牛肉", "鸡翅", "乌冬"]

    if staple_category == "甜品" or "下午茶" in scene_tags or "甜品" in cuisine or "烘焙" in cuisine or any(
        keyword in name for keyword in dessert_keywords
    ):
        course_types.append("dessert")
    if staple_category == "饮品" or any(keyword in name for keyword in drink_keywords):
        course_types.append("drink")
    if staple_category == "轻食" or any(keyword in name for keyword in light_keywords):
        course_types.append("light_meal")
    if staple_category in {"饭类", "面类", "粉类", "饼类", "锅物", "汤粥", "面包三明治", "菜肴"} or any(
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
    beverage_categories = request.get("beverage_categories", [])
    solar_terms = request.get("solar_terms", [])
    cuisine_groups = request.get("cuisine_groups", [])
    required_flavors = request.get("required_flavors", [])

    recipes["course_types"] = recipes.apply(lambda row: infer_course_types(row.to_dict()), axis=1)
    if "beverage_category" not in recipes.columns:
        recipes["beverage_category"] = recipes.apply(lambda row: classify_beverage_category(row.to_dict()), axis=1)

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

    if required_flavors:
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

    ranked = []
    for _, row in recipes.iterrows():
        recipe = row.to_dict()
        score, reasons = _score_recipe(recipe, request, favorite_counts, skip_counts)
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

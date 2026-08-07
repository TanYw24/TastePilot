import pandas as pd


def check_data_quality(df: pd.DataFrame) -> dict:
    missing_values = df.isnull().sum()
    duplicate_count = int(df.duplicated().sum())

    abnormal_rows = pd.DataFrame()
    if "每日学习时间" in df.columns:
        abnormal_rows = df[(df["每日学习时间"] < 0) | (df["每日学习时间"] > 16)]

    return {
        "missing_values": missing_values,
        "duplicate_count": duplicate_count,
        "abnormal_rows": abnormal_rows,
    }


def get_score_summary(df: pd.DataFrame) -> dict:
    scores = pd.to_numeric(df["期末成绩"], errors="coerce").dropna()

    return {
        "平均分": round(scores.mean(), 2),
        "最高分": round(scores.max(), 2),
        "最低分": round(scores.min(), 2),
        "及格人数": int((scores >= 60).sum()),
        "不及格人数": int((scores < 60).sum()),
        "及格率": round((scores >= 60).mean() * 100, 2),
    }


def group_average(df: pd.DataFrame, group_column: str, value_column: str) -> pd.DataFrame:
    result = (
        df.groupby(group_column)[value_column]
        .mean()
        .round(2)
        .sort_values(ascending=False)
        .reset_index()
    )
    return result


def find_risk_students(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["期末成绩"] < 60) | (df["出勤率"] < 70)]


def prepare_score_distribution(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["期末成绩"] = pd.to_numeric(result["期末成绩"], errors="coerce")
    return result.dropna(subset=["期末成绩"])


def prepare_major_score_chart(df: pd.DataFrame) -> pd.DataFrame:
    return group_average(df, "专业", "期末成绩")


def prepare_study_score_scatter(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["每日学习时间"] = pd.to_numeric(result["每日学习时间"], errors="coerce")
    result["期末成绩"] = pd.to_numeric(result["期末成绩"], errors="coerce")
    return result.dropna(subset=["每日学习时间", "期末成绩"])


def generate_analysis_report(df: pd.DataFrame) -> str:
    summary = get_score_summary(df)
    quality_result = check_data_quality(df)
    risk_students = find_risk_students(df)
    major_scores = prepare_major_score_chart(df)

    top_major = "暂无数据"
    top_major_score = "暂无数据"
    if not major_scores.empty:
        top_major = major_scores.iloc[0]["专业"]
        top_major_score = major_scores.iloc[0]["期末成绩"]

    clean_df = prepare_study_score_scatter(df)
    correlation_text = "由于有效数据不足，暂时无法判断学习时间和成绩之间的关系。"
    if len(clean_df) >= 2:
        correlation = clean_df["每日学习时间"].corr(clean_df["期末成绩"])
        if correlation >= 0.5:
            relation_text = "呈现比较明显的正相关"
        elif correlation >= 0.2:
            relation_text = "有一定正相关"
        elif correlation <= -0.5:
            relation_text = "呈现比较明显的负相关"
        elif correlation <= -0.2:
            relation_text = "有一定负相关"
        else:
            relation_text = "相关性不明显"
        correlation_text = (
            f"从相关系数来看，每日学习时间和期末成绩{relation_text}，"
            f"相关系数约为 {round(correlation, 2)}。"
        )

    missing_total = int(quality_result["missing_values"].sum())
    duplicate_count = quality_result["duplicate_count"]
    abnormal_count = len(quality_result["abnormal_rows"])

    report = f"""# 学生成绩数据分析报告

## 1. 数据概况
- 本次分析共包含 {df.shape[0]} 条记录，{df.shape[1]} 个字段。
- 数据中共发现 {missing_total} 个缺失值，{duplicate_count} 条重复记录，{abnormal_count} 条学习时间异常记录。

## 2. 成绩总体表现
- 期末成绩平均分为 {summary["平均分"]} 分，最高分为 {summary["最高分"]} 分，最低分为 {summary["最低分"]} 分。
- 当前及格率为 {summary["及格率"]}%，及格人数 {summary["及格人数"]} 人，不及格人数 {summary["不及格人数"]} 人。

## 3. 分组分析结论
- 平均成绩最高的专业是 {top_major}，平均期末成绩为 {top_major_score} 分。
- {correlation_text}

## 4. 风险预警
- 当前共识别出 {len(risk_students)} 名风险学生，判断规则为期末成绩低于 60 分或出勤率低于 70%。

## 5. 建议
- 优先处理缺失值、重复值和异常值，提升数据质量。
- 重点关注风险学生，结合出勤率和成绩进行早期干预。
- 如果后续数据量更大，可以继续加入更细的专业对比、时间趋势分析和 AI 问答能力。
"""
    return report

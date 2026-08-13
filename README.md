# TastePilot

TastePilot 是一个帮助用户快速回答“今天吃什么”的智能菜谱推荐 Web 应用。

它不要求用户填写复杂问卷或逐层筛选。用户可以直接说一句自然语言需求，例如：

- `想吃点暖胃的`
- `今天想吃甜品，不要太腻，不要正餐`
- `想喝点提神的饮品`
- `一个人吃，15分钟内，最好省钱`

系统会解析当前需求，再结合长期偏好、历史行为、本地菜谱数据和时间场景，给出可以继续调整的个性化推荐。

## 核心体验

- **一句话推荐**：识别口味、菜品类型、场景、预算、时间、饮食目标、情绪和否定条件。
- **低负担辅助选择**：可以先选正餐、轻食、甜品或饮品，也可以使用随时间和偏好变化的快捷标签。
- **推荐理由**：每道候选菜都会解释口味、场景、预算、时间或情绪等匹配依据。
- **继续调整**：支持“换一批”以及更快、更省钱、更清爽、更辣等快捷细化。
- **行为记忆**：记录浏览、收藏、取消收藏、跳过和“就吃这个”等反馈。
- **口味画像**：根据搜索、浏览、收藏、跳过和用户反馈逐步形成个人口味轮廓。
- **节气灵感**：提供二十四节气专题卡片、时令食材提示、分类筛选和对应菜品推荐。
- **响应式界面**：桌面端和移动端均可使用，核心菜品操作在手机端保持同一横排。

## 当前功能

### 用户与偏好

- 注册、登录和退出登录
- 密码哈希存储
- 30 天登录会话
- 邮箱验证码找回密码；未配置 SMTP 时使用本地调试模式
- 保存偏爱口味、忌口、饮食目标、预算、做饭时间和素食倾向

### 自然语言理解

当前规则解析可以识别：

- 口味：香辣、麻辣、清淡、鲜香、酸甜、奶香、重口等
- 类型：正餐主食、正餐菜品、轻食早午餐、甜品、饮品
- 场景：一个人吃、双人晚餐、朋友聚餐、下午茶、夜宵等
- 情绪：安慰、解压、暖胃、提神、犒赏等
- 限制：低预算、15/30/45/60 分钟、素食和忌口
- 否定表达：不要正餐、不要甜品、不要太腻、不要咸口等
- 菜系、主食形态、饮品子类和节气关键词

例如，“甜品，不要太腻，不要正餐”会优先返回清爽甜品；“提神饮品”会优先匹配咖啡、茶饮和具有清醒感的饮品；“15分钟内”会作为硬时间条件执行。

### 推荐与反馈

- 先按时间、预算、忌口、素食和菜品类型等硬条件筛选
- 再按口味、场景、情绪、标签、用户画像和历史行为综合打分
- 在高分候选池中加入有限随机性，减少重复
- 支持换一批且避开本轮已展示菜品
- 已收藏菜品再次出现时显示“取消收藏”
- 收藏状态写入数据库并在不同推荐页面保持一致

### 节气专题

项目内置完整的二十四节气配置和配套图片资源。专题页会展示：

- 当前节气主题与时令介绍
- 代表食材和适合口感
- 对应节气菜谱
- 菜品大类筛选
- “换一批这个时节的菜”

## 技术栈

- Python
- Streamlit
- Pandas
- SQLite（默认）
- PostgreSQL / psycopg（可选）

## 项目结构

```text
TastePilot/
├── app.py                    # Streamlit 页面、交互和样式
├── agent.py                  # 自然语言规则解析
├── recommendation_tools.py   # 筛选、打分、随机化和用户画像
├── recipe_taxonomy.py        # 菜谱类型、菜系和标签归一化
├── db.py                     # SQLite/PostgreSQL 数据访问
├── analysis_tools.py         # 辅助分析工具
├── requirements.txt
├── README.md
├── assets/
│   └── inspiration/          # 二十四节气卡片图片
├── data/
│   └── recipes.csv           # 1000 条本地菜谱
└── scripts/
    └── init_postgres.py      # PostgreSQL 初始化和数据迁移
```

菜谱数据包含 1000 条记录，覆盖正餐主食、正餐菜品、轻食早午餐、甜品和饮品五个一级分类，并包含多种地区菜系及完整节气数据。

## 菜谱数据字段

`data/recipes.csv` 的主要字段包括：

- `id`、`name`
- `food_origin`、`regional_cuisine`
- `main_type`、`sub_type`
- `flavor_tags`、`scene_tags`、`feature_tags`
- `seasonal_terms`
- `budget_level`、`cook_time_minutes`、`difficulty`
- `ingredients`
- `is_spicy`、`is_vegetarian`、`calorie_level`
- `description`

## 本地运行

建议使用 Python 3.10 或更高版本。

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

### 3. 访问网站

```text
http://localhost:8501
```

首次运行时会自动初始化 SQLite 数据库 `data/tastepilot.db`。

## 可选：配置 PostgreSQL

默认无需配置即可使用 SQLite。若要切换到 PostgreSQL：

```bash
export TASTEPILOT_USE_POSTGRES=true
export DATABASE_URL='postgresql://user:password@host:5432/tastepilot'
python scripts/init_postgres.py
streamlit run app.py
```

也可以使用 `POSTGRES_DSN` 或 `POSTGRES_URL` 提供连接地址。初始化脚本会创建所需表、导入菜谱，并迁移现有 SQLite 用户数据。

## 可选：配置密码重置邮件

可通过环境变量或 Streamlit secrets 设置：

```text
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM_EMAIL
SMTP_FROM_NAME
SMTP_USE_TLS
```

未配置邮件服务时，应用会在本地调试界面显示验证码，不会实际发送邮件。

## 当前边界

- 自然语言理解以规则、关键词和标签归一化为主，并非通用大模型理解。
- 菜谱来自本地数据集，不会自动获取在线内容或实时价格。
- 推荐系统属于可解释的规则打分与行为反馈原型，尚未训练机器学习排序模型。
- 项目适合课程展示、产品原型和小规模个人使用；正式部署仍需补充自动化测试、监控、安全策略和生产级资源配置。

## 一句话总结

TastePilot 想解决的不是“菜谱不够多”，而是用户明明饿了，却很难快速决定现在到底该吃什么。它用一句话输入、时令灵感、可解释推荐和持续反馈，做一个会逐渐记住个人口味的菜谱顾问。

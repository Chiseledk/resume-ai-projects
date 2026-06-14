# AI 思维导图生成器

基于 Flask 的文本转思维导图工具。系统将输入文本转换为语义树，再生成图节点、图边和布局坐标，前端使用 SVG 渲染可编辑的思维导图。

## 功能

- 文本生成思维导图
- 本地 NLP 关键词提取
- AI 二次优化语义树
- SVG 可视化渲染
- 节点拖拽编辑
- 节点改名
- 项目保存、打开、删除
- 历史记录
- SVG / JSON 导出

## 项目结构

```text
mindmap_generator/
  backend/
    main.py
    services/
      ai_processor.py
      data_parser.py
      graph_algorithms.py
      mindmap_generator.py
    utils/
      logger.py
      schema.py
  templates/
    index.html
  .env.example
  .gitignore
  README.md
  requirements.txt
```

## 生成流程

```text
用户文本
  -> 本地 NLP 算法生成初稿
  -> AI 二次优化语义树
  -> Pydantic 数据校验
  -> 生成 graph.nodes / graph.edges / graph.layout
  -> 前端 SVG 渲染
```

未配置 AI 密钥时，系统使用本地 NLP 算法生成思维导图。

## 核心算法

### 关键词提取

中文文本使用 `jieba.analyse` 提取关键词：

- `TextRank`：基于词共现图排序关键词
- `TF-IDF`：补充高区分度关键词
- 领域词增强：提高项目相关概念的权重
- 停用词过滤：减少无意义节点

### 图布局

后端将语义树转换为图结构：

- `graph.nodes`
- `graph.edges`
- `graph.layout`

布局算法使用 `radial-tidy-tree`：

- 为叶子节点分配稳定顺序
- 内部节点角度取子节点角度均值
- 按层级映射半径
- 输出每个节点的 `x/y` 坐标

### AI 优化

配置 `SPARK_API_PASSWORD` 后，系统会先生成本地算法初稿，再调用 AI 优化语义树：

- 合并重复或相近分支
- 将泛化节点改为更具体的短标签
- 补充遗漏关键词
- 调整层级结构

AI 只优化语义树，坐标仍由后端图布局算法生成。

## 本地运行

```powershell
cd C:\Users\25495\PycharmProjects\mindmap_generator
py -m pip install -r requirements.txt
py -m backend.main
```

浏览器访问：

```text
http://127.0.0.1:5000
```

## 环境变量

在项目根目录创建 `.env` 文件：

```env
MINDMAP_AI_ENABLED=false
SPARK_API_PASSWORD=your_api_password_here
SPARK_API_URL=https://spark-api-open.xf-yun.com/v1/chat/completions
SPARK_MODEL=4.0Ultra
FLASK_SECRET_KEY=your_secret_here
```

`SPARK_API_PASSWORD` 对应讯飞控制台鉴权信息中的 `APIPassword`。请求头格式：

```http
Authorization: Bearer your_api_password_here
```

`MINDMAP_AI_ENABLED=false` 表示关闭 AI 调用，只使用本地算法。需要启用 AI 时改为 `true`，并填写 `SPARK_API_PASSWORD`。

## API

### `POST /api/generate_mindmap`

请求：

```json
{
  "text": "需要转换为思维导图的文本"
}
```

响应核心字段：

```json
{
  "success": true,
  "mindmap": {
    "title": "中心主题",
    "nodes": [],
    "graph": {
      "nodes": [],
      "edges": [],
      "layout": "radial-tidy-tree"
    }
  },
  "graph_data": {
    "nodes": [],
    "edges": [],
    "layout": "radial-tidy-tree"
  },
  "generation_source": "ai_optimized"
}
```

`generation_source` 取值：

- `ai_optimized`：本地算法初稿已被 AI 二次优化
- `ai_direct`：本地算法无法生成时，由 AI 直接生成
- `algorithm_only`：使用本地算法结果

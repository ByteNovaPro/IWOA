# IWOA (Intelligent Work Order Assistant)

IWOA 是一个面向应届生作品集场景设计的双服务项目：

- `backend/`: Java Spring Boot 业务后端，提供工单和订单相关 API
- `agent-service/`: Python FastAPI Agent 服务，负责理解用户意图、调用后端工具并生成答复
- `frontend/`: 极简演示页面，用于展示对话式交互

## 项目目标

这个项目重点展示两类能力：

- Java 后端工程能力：REST API、数据建模、鉴权预留、日志、异常处理、测试扩展点
- AI Agent 能力：任务识别、工具调用、多步工作流、失败兜底、可观测性预留

## 当前实现

### Java 后端

已实现以下接口：

- `GET /tickets/{id}`
- `POST /tickets/{id}/comment`
- `POST /tickets/{id}/assign`
- `GET /orders/{id}`
- `POST /orders/{id}/refund-check`

数据目前使用内存示例数据，方便快速演示，后续可替换为 MySQL/PostgreSQL。

### Python Agent 服务

已实现以下能力：

- 根据用户输入识别任务类型
- 调用对应 Java API 查询或执行操作
- 将多接口结果整理成自然语言回复
- 当权限不足、信息缺失或意图不明确时给出兜底回复

目前使用规则驱动的 `workflow`，后续可替换为：

- OpenAI Agents SDK
- LangGraph
- 评估与追踪平台（如 LangSmith / OpenTelemetry）

### 前端

提供一个静态单页 demo，可直接调用 Agent 服务进行演示。

## 推荐演示场景

1. 查询工单详情：`帮我看看 T-1001 现在是谁负责`
2. 给工单追加评论：`给 T-1001 添加评论：客户已经补充截图`
3. 指派工单：`把 T-1002 指派给 wangwu`
4. 查询订单：`查一下 O-9001`
5. 退款校验：`帮我检查 O-9002 能不能退款`

## 启动方式

### 1. 启动 Java 后端

```bash
cd backend
export JAVA_HOME=/opt/homebrew/Cellar/openjdk@17/17.0.18/libexec/openjdk.jdk/Contents/Home
mvn spring-boot:run
```

默认地址：`http://localhost:8080`

要求：JDK 17+

### 2. 启动 Python Agent 服务

```bash
cd agent-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

默认地址：`http://localhost:8000`

Agent 支持接入 DashScope 的 OpenAI 兼容接口。可选两种配置方式：

1. 环境变量：`DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`、`DASHSCOPE_MODEL`
2. 本地文件：`agent-service/config/model.local.json`

示例文件见 `agent-service/config/model.local.example.json`。

### 3. 打开前端页面

可以直接用浏览器打开 `frontend/index.html`，或使用任意静态文件服务启动。

## Docker 部署

推荐直接使用 Docker Compose 启动整套服务。

### 1. 准备环境变量

复制 `.env.example` 为 `.env`，填入你的 DashScope Key：

```bash
cp .env.example .env
```

至少需要配置：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
```

### 2. 一键启动

```bash
docker compose up --build
```

启动后访问：

- 前端：`http://localhost:3000`
- Agent：`http://localhost:8000`
- Java 后端：`http://localhost:8080`

### 3. 停止服务

```bash
docker compose down
```

### 说明

- Compose 中 Agent 通过 `http://backend:8080` 访问 Java 后端
- 浏览器中的前端仍通过宿主机端口访问 Agent，所以前端脚本使用 `http://localhost:8000`
- 如果你只想重建某一个服务，可以执行 `docker compose up --build agent`

## 下一步建议

- 接入真实数据库和持久化
- 增加用户、角色、权限校验
- 将 Agent 规则流升级为 LLM + Tool Calling
- 增加测试、日志追踪、调用链 ID
- 接入消息队列或异步任务处理复杂工单流程

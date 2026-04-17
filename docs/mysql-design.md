# IWOA MySQL 数据库设计

这版设计基于当前后端接口和内存数据结构，目标是先稳定支撑现有能力，再为后续接 MySQL、做审计、接真实业务流程留扩展空间。

## 1. 当前接口对应的数据对象

现有 Java 后端实际涉及 2 个核心领域对象：

- `Ticket`
  - `GET /tickets/{id}`
  - `POST /tickets/{id}/comment`
  - `POST /tickets/{id}/assign`
- `Order`
  - `GET /orders/{id}`
  - `POST /orders/{id}/refund-check`

基于这组接口，建议至少拆成 5 张表：

- `tickets`：工单主表
- `ticket_comments`：工单评论表
- `ticket_assignment_history`：工单指派历史表
- `orders`：订单主表
- `refund_checks`：退款初审记录表

## 2. 设计原则

- 工单和订单都保留业务编号字段：`ticket_no`、`order_no`
  - 这样可以继续兼容你现在接口里类似 `T-1001`、`O-9001` 的 ID 风格
  - 数据库内部再使用自增 `BIGINT` 做主键，后续关联性能更稳
- 评论和指派历史单独建表，不把它们塞进 JSON
  - 这样后续做时间线、审计、分页、统计都更简单
- `refund-check` 不只即时返回结果，也落库到 `refund_checks`
  - 这样 Agent 触发过什么退款判断、理由是什么，都能追溯
- 状态字段先保留 `VARCHAR`
  - 当前项目还在快速迭代期，用 `VARCHAR` 比 MySQL `ENUM` 更灵活
  - 后续稳定后可改成枚举映射或字典表

## 3. 表结构说明

### tickets

工单主数据。

关键字段：

- `ticket_no`
- `title`
- `status`
- `priority`
- `requester`
- `assignee`
- `summary`
- `created_at`
- `updated_at`

说明：

- `ticket_no` 对应当前接口中的工单 ID
- `assignee` 保留在主表，方便直接查当前负责人
- `updated_at` 用来支持前端展示最新状态

### ticket_comments

工单评论明细。

关键字段：

- `ticket_id`
- `comment_text`
- `comment_source`
- `created_by`
- `created_at`

说明：

- 现在内存模型里 `comments` 只是字符串列表，落库后建议升级为明细表
- `comment_source` 用于区分评论来自用户、Agent、系统

### ticket_assignment_history

工单指派历史。

关键字段：

- `ticket_id`
- `previous_assignee`
- `new_assignee`
- `changed_by`
- `changed_at`

说明：

- 当前 `/tickets/{id}/assign` 只是直接改当前处理人
- 落库后建议同时写一条历史，避免后续追不出工单流转过程

### orders

订单主数据。

关键字段：

- `order_no`
- `customer_name`
- `status`
- `amount`
- `paid`
- `delivered`
- `created_at`
- `updated_at`

说明：

- 当前退款判断主要依赖 `paid`、`delivered`
- `status` 仍然保留，方便与业务语义对齐

### refund_checks

退款初审记录。

关键字段：

- `order_id`
- `reason`
- `eligible`
- `message`
- `checked_by`
- `created_at`

说明：

- 当前 `/orders/{id}/refund-check` 是纯计算接口
- 建议每次调用都记录结果，后续可用于风控审计、统计命中率、复盘 Agent 决策

## 4. 与现有接口的映射关系

`GET /tickets/{id}`

- 先按 `ticket_no` 查 `tickets`
- 再按 `ticket_id` 查 `ticket_comments`
- 返回时把评论列表组装回去

`POST /tickets/{id}/comment`

- 按 `ticket_no` 找到工单
- 插入 `ticket_comments`
- 更新 `tickets.updated_at`

`POST /tickets/{id}/assign`

- 按 `ticket_no` 找到工单
- 插入 `ticket_assignment_history`
- 更新 `tickets.assignee` 与 `tickets.updated_at`

`GET /orders/{id}`

- 按 `order_no` 查询 `orders`

`POST /orders/{id}/refund-check`

- 按 `order_no` 查询 `orders`
- 基于 `paid` 和 `delivered` 做校验
- 将结果写入 `refund_checks`
- 返回 `eligible` 和 `message`

## 5. 为什么现在不建议先上更多表

当前阶段不建议一开始就拆出 `users`、`customers`、`logistics_orders`、`payment_transactions` 等很多实体表，原因很简单：

- 你现在后端接口还比较少
- 当前目标是把 demo 数据切到 MySQL，而不是一次性做完整 ERP/工单平台
- 过早建很多表，后面反而容易因为业务未稳定而频繁返工

所以这版设计是“够用且可扩展”的最小业务模型。

## 6. 后续推荐演进顺序

建议按下面顺序推进：

1. 先把这 5 张表落到 MySQL
2. 后端加入 MySQL 驱动和数据访问层
3. 用数据库查询替换 `DemoDataService`
4. 让 `comment`、`assign`、`refund-check` 真实落库
5. 再考虑补 `users`、`customers`、`refund_requests` 等扩展表

## 7. 建议的下一步代码改造

如果你准备正式接数据库，我建议下一步直接做这几件事：

- 在 `backend/pom.xml` 加入 MySQL 驱动和 Spring Data JDBC / MyBatis
- 在 `application.yml` 增加 `spring.datasource.*`
- 在根目录 `.env.example` 增加：
  - `MYSQL_HOST`
  - `MYSQL_PORT`
  - `MYSQL_DATABASE`
  - `MYSQL_USERNAME`
  - `MYSQL_PASSWORD`
- 在 `docker-compose.yml` 增加 MySQL 服务
- 用 Repository/Mapper 替换 `DemoDataService`

## 8. 脚本位置

可直接执行的初始化脚本已放在：

- [backend/src/main/resources/db/mysql/init.sql](/Users/lby/project/code/IWOA（Intelligent Work Order Assistant）/backend/src/main/resources/db/mysql/init.sql)

设计说明文档在：

- [docs/mysql-design.md](/Users/lby/project/code/IWOA（Intelligent Work Order Assistant）/docs/mysql-design.md)

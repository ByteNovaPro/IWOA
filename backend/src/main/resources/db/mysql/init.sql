CREATE DATABASE IF NOT EXISTS iwoa
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE iwoa;

CREATE TABLE IF NOT EXISTS tickets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  ticket_no VARCHAR(32) NOT NULL COMMENT '业务工单号，例如 T-1001',
  title VARCHAR(200) NOT NULL COMMENT '工单标题',
  status VARCHAR(32) NOT NULL COMMENT '工单状态：OPEN/PENDING/RESOLVED/CLOSED',
  priority VARCHAR(32) NOT NULL COMMENT '优先级：LOW/MEDIUM/HIGH/URGENT',
  requester VARCHAR(64) NOT NULL COMMENT '提单人标识',
  assignee VARCHAR(64) DEFAULT NULL COMMENT '当前处理人标识',
  summary TEXT DEFAULT NULL COMMENT '工单摘要',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_tickets_ticket_no (ticket_no),
  KEY idx_tickets_status (status),
  KEY idx_tickets_assignee (assignee),
  KEY idx_tickets_requester (requester),
  KEY idx_tickets_created_at (created_at)
) ENGINE=InnoDB COMMENT='工单主表';

CREATE TABLE IF NOT EXISTS ticket_comments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  ticket_id BIGINT UNSIGNED NOT NULL COMMENT '关联 tickets.id',
  comment_text TEXT NOT NULL COMMENT '评论内容',
  comment_source VARCHAR(32) NOT NULL DEFAULT 'AGENT' COMMENT '评论来源：AGENT/USER/SYSTEM',
  created_by VARCHAR(64) DEFAULT NULL COMMENT '评论创建人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
  PRIMARY KEY (id),
  KEY idx_ticket_comments_ticket_id (ticket_id),
  KEY idx_ticket_comments_created_at (created_at),
  CONSTRAINT fk_ticket_comments_ticket_id
    FOREIGN KEY (ticket_id) REFERENCES tickets (id)
    ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='工单评论表';

CREATE TABLE IF NOT EXISTS ticket_assignment_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  ticket_id BIGINT UNSIGNED NOT NULL COMMENT '关联 tickets.id',
  previous_assignee VARCHAR(64) DEFAULT NULL COMMENT '原处理人',
  new_assignee VARCHAR(64) NOT NULL COMMENT '新处理人',
  changed_by VARCHAR(64) DEFAULT NULL COMMENT '操作人',
  changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
  PRIMARY KEY (id),
  KEY idx_ticket_assignment_history_ticket_id (ticket_id),
  KEY idx_ticket_assignment_history_changed_at (changed_at),
  CONSTRAINT fk_ticket_assignment_history_ticket_id
    FOREIGN KEY (ticket_id) REFERENCES tickets (id)
    ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='工单指派历史表';

CREATE TABLE IF NOT EXISTS orders (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  order_no VARCHAR(32) NOT NULL COMMENT '业务订单号，例如 O-9001',
  customer_name VARCHAR(100) NOT NULL COMMENT '客户名称',
  status VARCHAR(32) NOT NULL COMMENT '订单状态：CREATED/PAID/DELIVERED/COMPLETED/CANCELLED/REFUNDED',
  amount DECIMAL(10,2) NOT NULL COMMENT '订单金额',
  paid TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已支付',
  delivered TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发货/签收',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_orders_order_no (order_no),
  KEY idx_orders_status (status),
  KEY idx_orders_customer_name (customer_name),
  KEY idx_orders_created_at (created_at)
) ENGINE=InnoDB COMMENT='订单主表';

CREATE TABLE IF NOT EXISTS refund_checks (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  order_id BIGINT UNSIGNED NOT NULL COMMENT '关联 orders.id',
  reason VARCHAR(255) NOT NULL COMMENT '退款原因',
  eligible TINYINT(1) NOT NULL COMMENT '是否通过初审',
  message VARCHAR(500) NOT NULL COMMENT '校验结果说明',
  checked_by VARCHAR(64) DEFAULT 'agent' COMMENT '触发校验的主体',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '校验时间',
  PRIMARY KEY (id),
  KEY idx_refund_checks_order_id (order_id),
  KEY idx_refund_checks_created_at (created_at),
  CONSTRAINT fk_refund_checks_order_id
    FOREIGN KEY (order_id) REFERENCES orders (id)
    ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='退款初审记录表';

INSERT INTO tickets (ticket_no, title, status, priority, requester, assignee, summary, created_at, updated_at)
VALUES
  ('T-1001', '支付失败后用户重复扣款', 'OPEN', 'HIGH', 'customer_a', 'zhangsan', '用户反馈支付页面报错，但银行卡被重复扣款。', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 3 HOUR),
  ('T-1002', '订单发货后物流长时间未更新', 'PENDING', 'MEDIUM', 'customer_b', 'lisi', '物流信息 48 小时未更新，客户要求尽快确认。', NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 6 HOUR)
ON DUPLICATE KEY UPDATE
  title = VALUES(title),
  status = VALUES(status),
  priority = VALUES(priority),
  requester = VALUES(requester),
  assignee = VALUES(assignee),
  summary = VALUES(summary),
  updated_at = VALUES(updated_at);

INSERT INTO ticket_comments (ticket_id, comment_text, comment_source, created_by, created_at)
SELECT t.id, c.comment_text, c.comment_source, c.created_by, c.created_at
FROM (
  SELECT 'T-1001' AS ticket_no, '客服已确认用户提供两笔银行扣款截图' AS comment_text, 'USER' AS comment_source, 'customer_a' AS created_by, NOW() - INTERVAL 1 DAY AS created_at
  UNION ALL
  SELECT 'T-1001', '技术支持怀疑是支付回调重试导致', 'AGENT', 'agent', NOW() - INTERVAL 12 HOUR
  UNION ALL
  SELECT 'T-1002', '已联系物流供应商核查异常节点', 'AGENT', 'agent', NOW() - INTERVAL 8 HOUR
) c
JOIN tickets t ON t.ticket_no = c.ticket_no
WHERE NOT EXISTS (
  SELECT 1
  FROM ticket_comments tc
  WHERE tc.ticket_id = t.id
    AND tc.comment_text = c.comment_text
);

INSERT INTO ticket_assignment_history (ticket_id, previous_assignee, new_assignee, changed_by, changed_at)
SELECT t.id, NULL, t.assignee, 'system', t.created_at
FROM tickets t
WHERE t.assignee IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM ticket_assignment_history tah
    WHERE tah.ticket_id = t.id
  );

INSERT INTO orders (order_no, customer_name, status, amount, paid, delivered, created_at, updated_at)
VALUES
  ('O-9001', '客户甲', 'PAID', 299.00, 1, 0, NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 3 DAY),
  ('O-9002', '客户乙', 'DELIVERED', 1599.00, 1, 1, NOW() - INTERVAL 10 DAY, NOW() - INTERVAL 10 DAY)
ON DUPLICATE KEY UPDATE
  customer_name = VALUES(customer_name),
  status = VALUES(status),
  amount = VALUES(amount),
  paid = VALUES(paid),
  delivered = VALUES(delivered),
  updated_at = VALUES(updated_at);

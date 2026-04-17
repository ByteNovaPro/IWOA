package com.iwoa.backend.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Optional;

@Repository
public class OrderRepository {

    private static final RowMapper<OrderRecord> ORDER_ROW_MAPPER = OrderRepository::mapOrder;

    private final JdbcTemplate jdbcTemplate;

    public OrderRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<OrderRecord> findByOrderNo(String orderNo) {
        return jdbcTemplate.query(
                """
                SELECT id, order_no, customer_name, status, amount, delivered, paid, created_at
                FROM orders
                WHERE order_no = ?
                """,
                ORDER_ROW_MAPPER,
                orderNo
        ).stream().findFirst();
    }

    public void saveRefundCheck(long orderId, String reason, boolean eligible, String message, String checkedBy) {
        jdbcTemplate.update(
                """
                INSERT INTO refund_checks (order_id, reason, eligible, message, checked_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                orderId,
                reason,
                eligible,
                message,
                checkedBy
        );
    }

    private static OrderRecord mapOrder(ResultSet rs, int rowNum) throws SQLException {
        return new OrderRecord(
                rs.getLong("id"),
                rs.getString("order_no"),
                rs.getString("customer_name"),
                rs.getString("status"),
                rs.getBigDecimal("amount"),
                rs.getBoolean("delivered"),
                rs.getBoolean("paid"),
                toOffsetDateTime(rs.getTimestamp("created_at"))
        );
    }

    private static OffsetDateTime toOffsetDateTime(Timestamp timestamp) {
        return timestamp.toLocalDateTime().atOffset(ZoneOffset.UTC);
    }
}

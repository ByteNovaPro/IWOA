package com.iwoa.backend.repository;

import com.iwoa.backend.model.Order;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

public record OrderRecord(
        Long dbId,
        String orderNo,
        String customerName,
        String status,
        BigDecimal amount,
        boolean delivered,
        boolean paid,
        OffsetDateTime createdAt
) {

    public Order toOrder() {
        return new Order(orderNo, customerName, status, amount, delivered, paid, createdAt);
    }
}

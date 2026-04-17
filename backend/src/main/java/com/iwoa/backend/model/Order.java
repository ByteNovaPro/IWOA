package com.iwoa.backend.model;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

public class Order {

    private String id;
    private String customerName;
    private String status;
    private BigDecimal amount;
    private boolean delivered;
    private boolean paid;
    private OffsetDateTime createdAt;

    public Order() {
    }

    public Order(String id, String customerName, String status, BigDecimal amount,
                 boolean delivered, boolean paid, OffsetDateTime createdAt) {
        this.id = id;
        this.customerName = customerName;
        this.status = status;
        this.amount = amount;
        this.delivered = delivered;
        this.paid = paid;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getCustomerName() {
        return customerName;
    }

    public void setCustomerName(String customerName) {
        this.customerName = customerName;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public boolean isDelivered() {
        return delivered;
    }

    public void setDelivered(boolean delivered) {
        this.delivered = delivered;
    }

    public boolean isPaid() {
        return paid;
    }

    public void setPaid(boolean paid) {
        this.paid = paid;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }
}

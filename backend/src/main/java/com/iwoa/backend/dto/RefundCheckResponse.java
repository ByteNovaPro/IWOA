package com.iwoa.backend.dto;

public record RefundCheckResponse(String orderId, boolean eligible, String message) {
}

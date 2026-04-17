package com.iwoa.backend.dto;

import jakarta.validation.constraints.NotBlank;

public record RefundCheckRequest(@NotBlank String reason) {
}

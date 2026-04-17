package com.iwoa.backend.dto;

import jakarta.validation.constraints.NotBlank;

public record AssignRequest(@NotBlank String assignee) {
}

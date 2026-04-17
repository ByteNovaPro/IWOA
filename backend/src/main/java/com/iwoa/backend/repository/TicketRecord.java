package com.iwoa.backend.repository;

import com.iwoa.backend.model.Ticket;

import java.time.OffsetDateTime;
import java.util.List;

public record TicketRecord(
        Long dbId,
        String ticketNo,
        String title,
        String status,
        String priority,
        String assignee,
        String requester,
        String summary,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {

    public Ticket toTicket(List<String> comments) {
        return new Ticket(ticketNo, title, status, priority, assignee, requester, summary, createdAt, updatedAt, comments);
    }
}

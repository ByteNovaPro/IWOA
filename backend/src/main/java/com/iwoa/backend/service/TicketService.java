package com.iwoa.backend.service;

import com.iwoa.backend.model.Ticket;
import com.iwoa.backend.repository.TicketRecord;
import com.iwoa.backend.repository.TicketRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.time.OffsetDateTime;

@Service
public class TicketService {

    private final TicketRepository ticketRepository;

    public TicketService(TicketRepository ticketRepository) {
        this.ticketRepository = ticketRepository;
    }

    public Ticket getTicket(String id) {
        TicketRecord ticketRecord = getTicketRecord(id);
        return ticketRecord.toTicket(new ArrayList<>(ticketRepository.findCommentsByTicketId(ticketRecord.dbId())));
    }

    @Transactional
    public Ticket addComment(String id, String comment) {
        TicketRecord ticketRecord = getTicketRecord(id);
        OffsetDateTime now = OffsetDateTime.now();
        ticketRepository.addComment(ticketRecord.dbId(), comment, "AGENT", "agent", now);
        return getTicket(id);
    }

    @Transactional
    public Ticket assign(String id, String assignee) {
        TicketRecord ticketRecord = getTicketRecord(id);
        OffsetDateTime now = OffsetDateTime.now();
        ticketRepository.assign(ticketRecord.dbId(), ticketRecord.assignee(), assignee, "agent", now);
        return getTicket(id);
    }

    private TicketRecord getTicketRecord(String id) {
        return ticketRepository.findByTicketNo(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Ticket not found: " + id));
    }
}

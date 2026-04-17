package com.iwoa.backend.controller;

import com.iwoa.backend.dto.AssignRequest;
import com.iwoa.backend.dto.CommentRequest;
import com.iwoa.backend.model.Ticket;
import com.iwoa.backend.service.TicketService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/tickets")
public class TicketController {

    private final TicketService ticketService;

    public TicketController(TicketService ticketService) {
        this.ticketService = ticketService;
    }

    @GetMapping("/{id}")
    public Ticket getTicket(@PathVariable String id) {
        return ticketService.getTicket(id);
    }

    @PostMapping("/{id}/comment")
    public Ticket addComment(@PathVariable String id, @Valid @RequestBody CommentRequest request) {
        return ticketService.addComment(id, request.comment());
    }

    @PostMapping("/{id}/assign")
    public Ticket assign(@PathVariable String id, @Valid @RequestBody AssignRequest request) {
        return ticketService.assign(id, request.assignee());
    }
}

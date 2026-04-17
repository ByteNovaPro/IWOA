package com.iwoa.backend.controller;

import com.iwoa.backend.dto.RefundCheckRequest;
import com.iwoa.backend.dto.RefundCheckResponse;
import com.iwoa.backend.model.Order;
import com.iwoa.backend.service.OrderService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{id}")
    public Order getOrder(@PathVariable String id) {
        return orderService.getOrder(id);
    }

    @PostMapping("/{id}/refund-check")
    public RefundCheckResponse refundCheck(@PathVariable String id,
                                           @Valid @RequestBody RefundCheckRequest request) {
        return orderService.refundCheck(id, request.reason());
    }
}

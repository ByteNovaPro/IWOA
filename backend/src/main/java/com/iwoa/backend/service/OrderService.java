package com.iwoa.backend.service;

import com.iwoa.backend.dto.RefundCheckResponse;
import com.iwoa.backend.model.Order;
import com.iwoa.backend.repository.OrderRecord;
import com.iwoa.backend.repository.OrderRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class OrderService {

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public Order getOrder(String id) {
        return getOrderRecord(id).toOrder();
    }

    @Transactional
    public RefundCheckResponse refundCheck(String id, String reason) {
        OrderRecord orderRecord = getOrderRecord(id);
        Order order = orderRecord.toOrder();
        RefundCheckResponse response;

        if (!order.isPaid()) {
            response = new RefundCheckResponse(id, false, "订单未支付，不能发起退款流程。");
        } else if (order.isDelivered()) {
            response = new RefundCheckResponse(id, false, "订单已发货或已签收，需要转人工审核退款。原因：" + reason);
        } else {
            response = new RefundCheckResponse(id, true, "订单符合自动退款初审条件，可进入后续退款流程。原因：" + reason);
        }

        orderRepository.saveRefundCheck(orderRecord.dbId(), reason, response.eligible(), response.message(), "agent");
        return response;
    }

    private OrderRecord getOrderRecord(String id) {
        return orderRepository.findByOrderNo(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Order not found: " + id));
    }
}

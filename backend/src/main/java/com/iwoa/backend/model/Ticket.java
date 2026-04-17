package com.iwoa.backend.model;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

public class Ticket {

    private String id;
    private String title;
    private String status;
    private String priority;
    private String assignee;
    private String requester;
    private String summary;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private List<String> comments = new ArrayList<>();

    public Ticket() {
    }

    public Ticket(String id, String title, String status, String priority, String assignee,
                  String requester, String summary, OffsetDateTime createdAt,
                  OffsetDateTime updatedAt, List<String> comments) {
        this.id = id;
        this.title = title;
        this.status = status;
        this.priority = priority;
        this.assignee = assignee;
        this.requester = requester;
        this.summary = summary;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.comments = comments;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public String getAssignee() {
        return assignee;
    }

    public void setAssignee(String assignee) {
        this.assignee = assignee;
    }

    public String getRequester() {
        return requester;
    }

    public void setRequester(String requester) {
        this.requester = requester;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public OffsetDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(OffsetDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public List<String> getComments() {
        return comments;
    }

    public void setComments(List<String> comments) {
        this.comments = comments;
    }
}

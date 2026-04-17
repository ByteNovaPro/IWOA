package com.iwoa.backend.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

@Repository
public class TicketRepository {

    private static final RowMapper<TicketRecord> TICKET_ROW_MAPPER = TicketRepository::mapTicket;

    private final JdbcTemplate jdbcTemplate;

    public TicketRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<TicketRecord> findByTicketNo(String ticketNo) {
        return jdbcTemplate.query(
                """
                SELECT id, ticket_no, title, status, priority, assignee, requester, summary, created_at, updated_at
                FROM tickets
                WHERE ticket_no = ?
                """,
                TICKET_ROW_MAPPER,
                ticketNo
        ).stream().findFirst();
    }

    public List<String> findCommentsByTicketId(long ticketId) {
        return jdbcTemplate.queryForList(
                """
                SELECT comment_text
                FROM ticket_comments
                WHERE ticket_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                String.class,
                ticketId
        );
    }

    public void addComment(long ticketId, String comment, String commentSource, String createdBy, OffsetDateTime updatedAt) {
        jdbcTemplate.update(
                """
                INSERT INTO ticket_comments (ticket_id, comment_text, comment_source, created_by)
                VALUES (?, ?, ?, ?)
                """,
                ticketId,
                comment,
                commentSource,
                createdBy
        );
        touchTicket(ticketId, updatedAt);
    }

    public void assign(long ticketId, String previousAssignee, String newAssignee, String changedBy, OffsetDateTime updatedAt) {
        jdbcTemplate.update(
                """
                INSERT INTO ticket_assignment_history (ticket_id, previous_assignee, new_assignee, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ticketId,
                previousAssignee,
                newAssignee,
                changedBy,
                Timestamp.from(updatedAt.toInstant())
        );
        jdbcTemplate.update(
                """
                UPDATE tickets
                SET assignee = ?, updated_at = ?
                WHERE id = ?
                """,
                newAssignee,
                Timestamp.from(updatedAt.toInstant()),
                ticketId
        );
    }

    private void touchTicket(long ticketId, OffsetDateTime updatedAt) {
        jdbcTemplate.update(
                """
                UPDATE tickets
                SET updated_at = ?
                WHERE id = ?
                """,
                Timestamp.from(updatedAt.toInstant()),
                ticketId
        );
    }

    private static TicketRecord mapTicket(ResultSet rs, int rowNum) throws SQLException {
        return new TicketRecord(
                rs.getLong("id"),
                rs.getString("ticket_no"),
                rs.getString("title"),
                rs.getString("status"),
                rs.getString("priority"),
                rs.getString("assignee"),
                rs.getString("requester"),
                rs.getString("summary"),
                toOffsetDateTime(rs.getTimestamp("created_at")),
                toOffsetDateTime(rs.getTimestamp("updated_at"))
        );
    }

    private static OffsetDateTime toOffsetDateTime(Timestamp timestamp) {
        return timestamp.toLocalDateTime().atOffset(ZoneOffset.UTC);
    }
}

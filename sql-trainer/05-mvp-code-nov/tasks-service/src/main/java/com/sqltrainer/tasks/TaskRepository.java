package com.sqltrainer.tasks;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;

@Repository
public class TaskRepository {

    private final JdbcTemplate jdbc;

    public TaskRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Список активных задач.
     */
    public List<Map<String, Object>> findAllActive() {
        String sql = """
            select code, title, description, difficulty, is_active
            from tasks.task
            where is_active = true
            order by code
            """;
        return jdbc.queryForList(sql);
    }

    /**
     * Одна задача по коду.
     */
    public Map<String, Object> findTaskAsMap(String code) {
        String sql = """
            select code, title, description, difficulty, is_active, created_at, updated_at
            from tasks.task
            where code = ?
            """;
        List<Map<String, Object>> list = jdbc.queryForList(sql, code);
        return list.isEmpty() ? null : list.get(0);
    }

    /**
     * Обязательные поля.
     */
    public List<Map<String, Object>> findRequiredFieldsAsMap(String code) {
        String sql = """
            select field_name,
                   position_ordinal
            from tasks.task_required_field
            where task_code = ?
            order by position_ordinal nulls last, field_name
            """;
        return jdbc.queryForList(sql, code);
    }

    /**
     * Эталонный ответ (всё, что есть).
     */
    public Map<String, Object> findAnswerAsMap(String code) {
        String sql = """
            select task_code,
                   answer_hash,
                   hash_algo,
                   request,
                   result,
                   updated_at
            from tasks.task_answer
            where task_code = ?
            """;
        List<Map<String, Object>> list = jdbc.queryForList(sql, code);
        return list.isEmpty() ? null : list.get(0);
    }
}

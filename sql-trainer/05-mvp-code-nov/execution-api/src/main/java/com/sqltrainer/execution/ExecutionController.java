package com.sqltrainer.execution;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.sql.SQLException;
import java.util.Date;
import java.util.Map;
import java.util.Objects;

@RestController
@RequestMapping("/exec")
public class ExecutionController {

    private final ExecutionService executionService;

    public ExecutionController(ExecutionService executionService) {
        this.executionService = executionService;
    }

    @PostMapping("/run")
    public ResponseEntity<?> run(@RequestBody Map<String, Object> body) {
        String sql = Objects.toString(body.get("sql"), "").trim();

        try {
            Map<String, Object> result = executionService.execute(sql);
            return ResponseEntity.ok(result);
        }
        catch (ExecutionService.QueueFullException qfe) {
            return error(HttpStatus.TOO_MANY_REQUESTS, qfe.getMessage());
        }
        catch (ExecutionService.ExecTimeoutException ete) {
            return error(HttpStatus.REQUEST_TIMEOUT, ete.getMessage());
        }
        catch (SQLException e) {
            return handleSqlException(e);
        }
        catch (IllegalArgumentException iae) {
            return error(HttpStatus.BAD_REQUEST, iae.getMessage());
        }
        catch (Exception e) {
            return error(HttpStatus.INTERNAL_SERVER_ERROR, "Execution error: " + e.getMessage());
        }
    }

    @PostMapping("/compare")
    public ResponseEntity<?> compare(@RequestBody Map<String, Object> body) {
        String refSql = Objects.toString(body.get("refSql"), "").trim();
        String stuSql = Objects.toString(body.get("stuSql"), "").trim();

        if (refSql.isEmpty() || stuSql.isEmpty()) {
            return error(HttpStatus.BAD_REQUEST, "refSql and stuSql are required");
        }

        String finalSql = buildCompareSql(refSql, stuSql);

        try {
            Map<String, Object> result = executionService.executeJsonReturning(finalSql);
            return ResponseEntity.ok(result);
        }
        catch (ExecutionService.QueueFullException qfe) {
            return error(HttpStatus.TOO_MANY_REQUESTS, qfe.getMessage());
        }
        catch (ExecutionService.ExecTimeoutException ete) {
            return error(HttpStatus.REQUEST_TIMEOUT, ete.getMessage());
        }
        catch (SQLException e) {
            return handleSqlException(e);
        }
        catch (Exception e) {
            return error(HttpStatus.INTERNAL_SERVER_ERROR, "Execution error: " + e.getMessage());
        }
    }

	private String buildCompareSql(String refSql, String stuSql) {
		return """
				WITH
				-- Эталон (как есть)
				ref AS (
				  %s
				),
				-- Запрос студента (как есть)
				stu AS (
				  %s
				),
				-- превращаем каждую строку в jsonb
				ref_json AS (
				  SELECT to_jsonb(row_to_json(r)) AS j FROM ref r
				),
				stu_json AS (
				  SELECT to_jsonb(row_to_json(s)) AS j FROM stu s
				),
				-- булев флаг: мультимножества jsonb совпадают?
				ok AS (
				  SELECT NOT EXISTS (
					(SELECT j FROM ref_json EXCEPT ALL SELECT j FROM stu_json)
					UNION ALL
					(SELECT j FROM stu_json EXCEPT ALL SELECT j FROM ref_json)
				  ) AS ok
				),
				-- первая строка студента → достаём имена колонок
				one AS (SELECT * FROM stu LIMIT 1),
				cols AS (
				  SELECT COALESCE(
					(SELECT json_agg(j.key ORDER BY j.ord)
					 FROM one o,
						  LATERAL json_each(row_to_json(o)) WITH ORDINALITY AS j(key, val, ord)),
					'[]'::json
				  ) AS columns
				),
				-- строки студента как массив массивов
				rows AS (
				  SELECT COALESCE(
					json_agg(
					  (SELECT json_agg(e.value ORDER BY e.ord)
					   FROM json_each(row_to_json(s)) WITH ORDINALITY AS e(key, value, ord))
					),
					'[]'::json
				  ) AS rows
				  FROM stu s
				)
				SELECT json_build_object(
				  'result',  (SELECT ok      FROM ok),
				  'columns', (SELECT columns FROM cols),
				  'rows',    (SELECT rows    FROM rows)
				) AS result;
				""".formatted(refSql, stuSql);
	}

    private ResponseEntity<Map<String, Object>> handleSqlException(SQLException e) {
        String sqlState = e.getSQLState();
        String msg = e.getMessage();

        if ("57014".equals(sqlState)) {
            return error(HttpStatus.REQUEST_TIMEOUT, "Query cancelled by statement_timeout: " + msg);
        }
        if ("42501".equals(sqlState)) {
            return error(HttpStatus.FORBIDDEN, "Insufficient privileges: " + msg);
        }
        if ("42P01".equals(sqlState)) {
            return error(HttpStatus.NOT_FOUND, "Table does not exist: " + msg);
        }
        if ("42601".equals(sqlState)) {
            return error(HttpStatus.BAD_REQUEST, "SQL syntax error: " + msg);
        }
        return error(HttpStatus.INTERNAL_SERVER_ERROR, "SQL error: " + msg);
    }

    private ResponseEntity<Map<String, Object>> error(HttpStatus status, String message) {
        Map<String, Object> body = new java.util.LinkedHashMap<>();
        body.put("status", status.value());
        body.put("error", status.getReasonPhrase());
        body.put("message", message);
        body.put("timestamp", new Date());
        return ResponseEntity.status(status).body(body);
    }
}

package com.sqltrainer.execution;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.sql.*;
import java.util.*;
import java.util.concurrent.*;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class ExecutionService {

    private final DataSource dataSource;
    private final int autoLimit;
    private final boolean allowOnlySelect;
    private final ThreadPoolExecutor executor;
    private final long timeoutMs;

    public ExecutionService(
            DataSource dataSource,
            @Value("${execution.auto-limit:200}") int autoLimit,
            @Value("${execution.allow-only-select:true}") boolean allowOnlySelect,
            @Value("${execution.timeout-ms:1000}") long timeoutMs
    ) {
        this.dataSource = dataSource;
        this.autoLimit = autoLimit;
        this.allowOnlySelect = allowOnlySelect;
        this.timeoutMs = timeoutMs;

        int slots = 4;
        int queue = 16;

        this.executor = new ThreadPoolExecutor(
                slots,
                slots,
                0L, TimeUnit.MILLISECONDS,
                new ArrayBlockingQueue<>(queue),
                new ThreadPoolExecutor.AbortPolicy()
        );
    }

    // ===== обычный exec =====
    public Map<String, Object> execute(String sql) throws Exception {
        String preparedSql = prepareSql(sql);

        Callable<Map<String, Object>> task = () -> runQuery(preparedSql);

        Future<Map<String, Object>> future;
        try {
            future = executor.submit(task);
        } catch (RejectedExecutionException ex) {
            throw new QueueFullException("Execution queue is full");
        }

        try {
            return future.get(timeoutMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException te) {
            future.cancel(true);
            throw new ExecTimeoutException("Execution timed out after " + timeoutMs + "ms");
        }
    }

    // ===== exec, который ждёт json из БД (для /exec/compare) =====
    public Map<String, Object> executeJsonReturning(String sql) throws Exception {
        Callable<Map<String, Object>> task = () -> runJsonReturningQuery(sql);

        Future<Map<String, Object>> future;
        try {
            future = executor.submit(task);
        } catch (RejectedExecutionException ex) {
            throw new QueueFullException("Execution queue is full");
        }

        try {
            return future.get(timeoutMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException te) {
            future.cancel(true);
            throw new ExecTimeoutException("Execution timed out after " + timeoutMs + "ms");
        }
    }

    // ===== внутренности =====

    private String prepareSql(String sql) {
        if (sql == null || sql.trim().isEmpty()) {
            throw new IllegalArgumentException("SQL is empty");
        }
        sql = sql.trim();
        String low = sql.toLowerCase();

        if (allowOnlySelect) {
            boolean isSelect = low.startsWith("select");
            boolean isWith = low.startsWith("with");
            if (!isSelect && !isWith) {
                throw new IllegalArgumentException("Only SELECT / WITH statements are allowed");
            }
        }

        if (!low.contains(" limit ")) {
            sql = sql + " limit " + autoLimit;
        }
        return sql;
    }

    private Map<String, Object> runQuery(String sql) throws SQLException {
        List<String> columns = new ArrayList<>();
        List<List<Object>> rows = new ArrayList<>();

        long started = System.currentTimeMillis();

        try (Connection conn = dataSource.getConnection()) {

            // ВАЖНО: без параметра
            try (Statement st = conn.createStatement()) {
                st.execute("SET LOCAL statement_timeout = " + this.timeoutMs);
            }

            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                ps.setQueryTimeout((int) Math.ceil(this.timeoutMs / 1000.0));

                try (ResultSet rs = ps.executeQuery()) {
                    ResultSetMetaData md = rs.getMetaData();
                    int colCount = md.getColumnCount();
                    for (int i = 1; i <= colCount; i++) {
                        columns.add(md.getColumnLabel(i));
                    }
                    while (rs.next()) {
                        List<Object> row = new ArrayList<>();
                        for (int i = 1; i <= colCount; i++) {
                            row.add(rs.getObject(i));
                        }
                        rows.add(row);
                    }
                }
            }
        }

        long duration = System.currentTimeMillis() - started;

        Map<String, Object> resp = new HashMap<>();
        resp.put("columns", columns);
        resp.put("rows", rows);
        resp.put("truncated", false);
        resp.put("durationMs", duration);
        return resp;
    }

    private Map<String, Object> runJsonReturningQuery(String sql) throws Exception {
        long started = System.currentTimeMillis();

        try (Connection conn = dataSource.getConnection()) {

            // тоже БЕЗ параметра
            try (Statement st = conn.createStatement()) {
                st.execute("SET LOCAL statement_timeout = " + this.timeoutMs);
            }

            try (PreparedStatement ps = conn.prepareStatement(sql);
                 ResultSet rs = ps.executeQuery()) {

                if (!rs.next()) {
                    throw new SQLException("Comparison query returned no rows");
                }

                Object val = rs.getObject(1);
                if (val == null) {
                    throw new SQLException("Comparison query returned null");
                }

                String jsonStr = val.toString();
                ObjectMapper om = new ObjectMapper();
                @SuppressWarnings("unchecked")
                Map<String, Object> parsed = om.readValue(jsonStr, Map.class);

                long duration = System.currentTimeMillis() - started;
                parsed.putIfAbsent("durationMs", duration);
                return parsed;
            }
        }
    }

    // ===== свои исключения =====
    public static class QueueFullException extends RuntimeException {
        public QueueFullException(String msg) { super(msg); }
    }

    public static class ExecTimeoutException extends RuntimeException {
        public ExecTimeoutException(String msg) { super(msg); }
    }
}

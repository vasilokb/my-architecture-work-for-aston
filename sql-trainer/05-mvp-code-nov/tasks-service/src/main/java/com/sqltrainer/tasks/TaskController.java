package com.sqltrainer.tasks;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

@RestController
@RequestMapping("/tasks")
public class TaskController {

    private final TaskRepository repo;
    private final ObjectMapper mapper;

    public TaskController(TaskRepository repo) {
        this.repo = repo;
        // настраиваем ObjectMapper на детерминированную сериализацию
        ObjectMapper om = new ObjectMapper();
        om.configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
        this.mapper = om;
    }

    /**
     * GET /tasks
     * список задач
     */
    @GetMapping
    public List<Map<String, Object>> list() {
        return repo.findAllActive();
    }

    /**
     * GET /tasks/{code}
     * задача + обязательные поля
     */
    @GetMapping("/{code}")
    public ResponseEntity<?> getByCode(@PathVariable String code) {
        Map<String, Object> task = repo.findTaskAsMap(code);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }

        List<Map<String, Object>> fields = repo.findRequiredFieldsAsMap(code);

        Map<String, Object> result = new HashMap<>(task);
        result.put("required_fields", fields);

        return ResponseEntity.ok(result);
    }

    /**
     * GET /tasks/{code}/answer
     * показать эталонный ответ целиком (для админа / подсказки)
     */
    @GetMapping("/{code}/answer")
    public ResponseEntity<?> getAnswer(@PathVariable String code) {
        Map<String, Object> answer = repo.findAnswerAsMap(code);
        if (answer == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(answer);
    }

    /**
     * POST /tasks/{code}/verify
     *
     * progress присылает:
     * {
     *   "student_result": [ ... ]
     * }
     *
     * tasks-service сам:
     *  - достаёт из БД hash_algo и answer_hash и result
     *  - сериализует свой etalon result и student_result
     *  - считает SHA-256
     *  - сравнивает
     */
    @PostMapping("/{code}/verify")
    public ResponseEntity<?> verify(@PathVariable String code,
                                    @RequestBody Map<String, Object> body) {
        Map<String, Object> answer = repo.findAnswerAsMap(code);
        if (answer == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of(
                            "status", 404,
                            "message", "No answer stored for task " + code
                    ));
        }

        Object studentResultRaw = body.get("student_result");
        if (studentResultRaw == null) {
            return ResponseEntity.badRequest()
                    .body(Map.of(
                            "status", 400,
                            "message", "student_result is required"
                    ));
        }

        String expectedHash = (String) answer.get("answer_hash");
        String hashAlgo = (String) answer.get("hash_algo");
        Object etalonResultRaw = answer.get("result"); // это колонка jsonb в твоей таблице

        if (hashAlgo == null || !hashAlgo.equalsIgnoreCase("SHA256")) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of(
                            "status", 400,
                            "message", "Unsupported hash algo in task_answer: " + hashAlgo
                    ));
        }

        try {
            // сериализуем оба в детерминированный JSON
            byte[] etalonJson = serializeStable(etalonResultRaw);
            byte[] studentJson = serializeStable(studentResultRaw);

            String etalonComputed = sha256Hex(etalonJson);
            String studentComputed = sha256Hex(studentJson);

            boolean match;
            if (expectedHash != null && !expectedHash.isBlank()) {
                // если в БД лежит "канонический" хэш — сверяем и с ним тоже
                match = expectedHash.equalsIgnoreCase(studentComputed);
            } else {
                // если по какой-то причине в БД нет хэша — сверяем наш расчётный и студентский
                match = etalonComputed.equalsIgnoreCase(studentComputed);
            }

            Map<String, Object> resp = new LinkedHashMap<>();
            resp.put("task_code", code);
            resp.put("hash_algo", "SHA256");
            resp.put("correct", match);
            resp.put("expected_hash", expectedHash != null ? expectedHash : etalonComputed);
            resp.put("actual_hash", studentComputed);

            return ResponseEntity.ok(resp);

        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of(
                            "status", 500,
                            "message", "Verification failed: " + e.getMessage()
                    ));
        }
    }

    private byte[] serializeStable(Object obj) throws JsonProcessingException {
        // Jackson сам превращает LinkedHashMap/List в JSON; мы включили упорядочивание ключей
        String json = mapper.writeValueAsString(obj);
        return json.getBytes(StandardCharsets.UTF_8);
    }

    private String sha256Hex(byte[] data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] digest = md.digest(data);
        StringBuilder sb = new StringBuilder(digest.length * 2);
        for (byte b : digest) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}

package com.sqltrainer.tasks;

public record TaskDto(
        String code,
        String title,
        String description,
        Integer difficulty,
        Boolean isActive
) {}

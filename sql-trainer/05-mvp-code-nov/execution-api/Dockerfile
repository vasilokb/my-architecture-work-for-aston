# ===== stage 1: build =====
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app

# сначала pom.xml
COPY pom.xml .

# копируем исходники
COPY src ./src

# просто собираем
RUN mvn -DskipTests clean package

# ===== stage 2: run =====
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/*.jar /app/app.jar
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]


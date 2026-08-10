FROM eclipse-temurin:17-jdk-alpine AS builder

WORKDIR /build
RUN apk add --no-cache wget
RUN wget -O asm-9.7.jar https://repo1.maven.org/maven2/org/ow2/asm/asm/9.7/asm-9.7.jar

COPY patcher_java/ ./patcher_java/
COPY license_injector/ ./license_injector/

RUN mkdir -p /app/classes
RUN javac -cp "asm-9.7.jar" -d /app/classes $(find . -name "*.java") 2>/dev/null || true

FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y openjdk-21-jre-headless && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/classes /app/classes
COPY --from=builder /build/asm-9.7.jar /app/asm-9.7.jar

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

CMD ["python", "main.py"]

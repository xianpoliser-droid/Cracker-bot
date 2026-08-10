FROM eclipse-temurin:17-jdk-alpine AS builder

WORKDIR /build
RUN apk add --no-cache wget
RUN wget -O asm-9.7.jar https://repo1.maven.org/maven2/org/ow2/asm/asm/9.7/asm-9.7.jar

# Copy all Java source
COPY patcher_java/ ./patcher_java/
COPY license_injector/ ./license_injector/

# Compile patchers
RUN mkdir -p /app/patcher_java /app/license_injector /app/classes
RUN javac -cp "asm-9.7.jar" -d /app/classes $(find . -name "*.java")

# Build JARs
RUN echo "Main-Class: license_injector.LicenseInjector" > manifest.mf && \
    jar cfm /app/LicenseInjector.jar manifest.mf -C /app/classes license_injector && \
    jar cf /app/patcher_java.jar -C /app/classes com/aetheria/patchers

FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y openjdk-17-jre-headless && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/LicenseInjector.jar /app/license_injector/
COPY --from=builder /app/patcher_java.jar /app/patcher_java/
COPY --from=builder /build/asm-9.7.jar /app/asm-9.7.jar
COPY --from=builder /build/patcher_java/ /app/patcher_java/
COPY --from=builder /build/license_injector/ /app/license_injector/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

CMD ["python", "main.py"]

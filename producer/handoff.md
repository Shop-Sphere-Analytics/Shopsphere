# Producer Subsystem Handoff Documentation

## Overview
The Producer subsystem generates live e-commerce streaming data (`orders`, `clicks`, `sessions`) and publishes JSON payloads to Kafka.

## Connection Details
* **Broker Endpoint:** `localhost:9092`
* **Docker Compose Location:** `producer/docker-compose.yml` (v7.5.0 images)
* **Active Topics:**
  * `orders`
  * `clicks`
  * `sessions`

## Execution Instructions
1. Ensure Docker Desktop is running.
2. Start Kafka and ZooKeeper:
   ```powershell
   cd producer
   docker compose up -d
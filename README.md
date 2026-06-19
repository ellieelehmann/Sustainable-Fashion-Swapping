# Sustainable Fashion Swapping

A microservices-based platform that lets users post and swap secondhand clothing within their community — encouraging sustainable consumption through item exchange instead of disposal.

## System Overview

The system is split into three independent services, each with its own health check endpoint, orchestrated together with Docker Compose behind an NGINX API gateway.

| Service | Responsibility |
|---|---|
| **user-service** | User registration and profile management |
| **item-service** | Listing, searching, and removing clothing items available for swap |
| **swap-service** | Creating and tracking swap requests between users |

## Tech Stack

- **Backend framework:** FastAPI (async Python)
- **Containerization:** Docker, Docker Compose
- **API Gateway:** NGINX
- **Caching / health data:** Redis
- **Validation / models:** Pydantic
- **Language:** Python

## Architecture

### user-service
Handles user registration and profile data.

**Data model:** name, email, location, item preference

| Method | Endpoint | Description |
|--------|----------|--------------|
| `POST` | `/users` | Create a user profile |
| `GET` | `/users/{user_id}` | Get details for a specific user |
| `GET` | `/health` | Service health check |

### item-service
Manages clothing items available for exchange.

**Data model:** item name, description, category, size, condition, image URL

| Method | Endpoint | Description |
|--------|----------|--------------|
| `POST` | `/items` | List a new clothing item for swap |
| `GET` | `/items` | Search available items |
| `DELETE` | `/items/{item_id}` | Remove a listed item |
| `GET` | `/health` | Service health check |

### swap-service
Manages swap requests between users.

**Data model:** requester ID, item requested, item offered, status

| Method | Endpoint | Description |
|--------|----------|--------------|
| `POST` | `/swaps` | Create a new swap request |
| `GET` | `/swaps/{id}` | Check the status of a swap |
| `PUT` | `/swaps/{id}/complete` | Mark a swap as completed |
| `GET` | `/health` | Service health check |

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- Python 3.x (for local development outside containers)

### Installation

```bash
git clone https://github.com/ellieelehmann/Sustainable-Fashion-Swapping.git
cd Sustainable-Fashion-Swapping
```

### Build and Run

```bash
docker-compose up -d --build
```

Verify all containers are running:

```bash
docker ps
```

### Tearing Down

```bash
docker-compose down -v
docker container prune -f
docker volume prune -f
```

## API Documentation

### Health Check Endpoints

**user-service**
```bash
curl http://localhost:8000/health
```
```json
{
  "service": "user-service",
  "status": "healthy",
  "dependencies": {}
}
```

**item-service**
```bash
curl http://localhost:8001/health
```
```json
{
  "service": "item-service",
  "status": "healthy",
  "dependencies": {
    "user-service": {
      "status": "healthy",
      "response_time_ms": 13.4
    }
  }
}
```

**swap-service**
```bash
curl http://localhost:8002/health
```
```json
{
  "service": "swap-service",
  "status": "healthy",
  "dependencies": {
    "item-service": {
      "status": "healthy",
      "response_time_ms": 22.5
    }
  }
}
```

## Testing

Manual service health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## Project Structure

```
Sustainable-Fashion-Swapping/
├── item-service/
│   ├── app/
│   │   ├── main.py         # FastAPI entry point for the item service
│   │   └── models.py       # Pydantic models and data schemas
│   ├── Dockerfile          # Builds the item service container
│   └── requirements.txt
│
├── swap-service/
│   ├── app/
│   │   ├── main.py         # FastAPI entry point for the swap service
│   │   └── models.py       # Pydantic models for swap logic
│   ├── Dockerfile          # Builds the swap service container
│   └── requirements.txt
│
├── user-service/
│   ├── app/
│   │   ├── main.py         # FastAPI entry point for the user service
│   │   └── models.py       # Pydantic models for user data
│   ├── Dockerfile          # Builds the user service container
│   └── requirements.txt
│
├── docker-compose.yml          # Orchestrates all three microservices
├── architecture-diagram.png    # Visual overview of the system architecture
├── CODE_PROVENANCE.md          # AI usage disclosure
├── README.md                   # Project documentation (this file)
└── System Architecture Document.pdf   # Detailed system design report
```


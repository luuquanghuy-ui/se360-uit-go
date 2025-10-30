# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UIT-Go is a ride-hailing platform built with a microservices architecture using FastAPI and Python. The system consists of 5 independent services that communicate via HTTP REST APIs and WebSocket connections for real-time features.

**Core Architecture Pattern**: Each service is a standalone FastAPI application with its own database (MongoDB or PostgreSQL) and dependencies. Services communicate internally using Docker network DNS names (e.g., `http://userservice:8000`).

## Development Commands

### Running the Entire System

```bash
# Start all services with Docker Compose (recommended)
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Rebuild a specific service after code changes
docker-compose up -d --build [service_name]
```

### Running Individual Services Locally

Each service can be run independently for development:

```bash
# Navigate to service directory
cd UserService  # or TripService, DriverService, LocationService, PaymentService

# Install dependencies
pip install -r requirements.txt

# Run service (from service directory)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Services run on these ports when accessed from localhost:
# UserService: 8000
# LocationService: 8001
# TripService: 8002
# DriverService: 8003
# PaymentService: 8004
```

### Database Commands

```bash
# Access MongoDB shell
docker exec -it uitgo-mongodb mongosh -u admin -p secret

# Access Redis CLI
docker exec -it uitgo-redis redis-cli

# Access PostgreSQL
docker exec -it uitgo-postgres psql -U admin -d mydb
```

## Service Architecture

### Service Responsibilities

- **UserService** (FastAPI + PostgreSQL): User authentication, JWT token issuance (both user tokens and service-to-service tokens), user profile management
- **TripService** (FastAPI + MongoDB): Trip lifecycle management, matching logic, orchestrates calls to other services, integrates with Mapbox API for routing
- **DriverService** (FastAPI + MongoDB): Driver profiles, driver wallet management, internal driver info endpoints protected by service tokens
- **LocationService** (FastAPI + Redis + WebSocket): Real-time driver location tracking using Redis GEO indexes, WebSocket connections for live updates, notification dispatch to drivers/passengers
- **PaymentService** (FastAPI + MongoDB): User wallet management, VNPay payment integration, payment processing and callbacks

### Inter-Service Communication Patterns

**Service-to-Service Authentication**:
- TripService needs to call protected DriverService endpoints (`/drivers/internal/{id}`)
- Flow: TripService requests service token from UserService using client credentials (MY_CLIENT_ID/MY_CLIENT_SECRET) → UserService returns JWT with `type=service` → TripService uses this token to authenticate with DriverService
- DriverService validates service tokens using the same SECRET_KEY as UserService

**Key Communication Flows**:

1. **Trip Creation Flow**:
   - TripService → Mapbox API (route calculation)
   - TripService → LocationService GET `/drivers/nearby` (find available drivers)
   - TripService → LocationService POST `/notify/drivers` (send trip offers via WebSocket)

2. **Driver Assignment Flow**:
   - TripService → UserService POST `/auth/token` (get service token)
   - TripService → DriverService GET `/drivers/internal/{id}` (fetch driver details with service token)
   - TripService → LocationService POST `/notify/trip/{id}/passenger` (notify passenger)

3. **Payment Flow**:
   - TripService → PaymentService POST `/process-payment` (initiate E-Wallet payment)
   - User → VNPay (external redirect)
   - VNPay → PaymentService GET `/payment-return` (callback)

### WebSocket Architecture

LocationService handles all WebSocket connections:

- `/ws/driver/{driver_id}/location`: Driver app sends location updates; LocationService stores in Redis GEO and can push notifications to driver
- `/ws/trip/{trip_id}/{user_type}`: Both passenger and driver connect to this room for real-time trip updates (location sharing, status changes)

## Environment Setup

**Required**: Copy `docs/ENV.sample` to `.env` in the project root before running.

**Critical Environment Variables**:

- `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`: Database credentials
- `JWT_SECRET_KEY`: Must be identical for UserService and DriverService (shared for service token validation)
- `TRIPSVC_CLIENT_ID`, `TRIPSVC_CLIENT_SECRET`: TripService credentials for obtaining service tokens
- `MAPBOX_ACCESS_TOKEN`: Required for TripService routing features
- `VNP_TMN_CODE`, `VNP_HASH_SECRET`: VNPay integration credentials
- `BASE_URL`: Public-facing URL for PaymentService (use ngrok HTTPS URL in development for VNPay callbacks)

**Internal Service URLs** (in docker-compose.yml):
- Services communicate using internal Docker network names: `http://userservice:8000`, `http://locationservice:8000`, etc.
- External access uses localhost ports: `http://localhost:8000`, `http://localhost:8001`, etc.

## Code Organization

Each service follows this structure:
```
ServiceName/
├── main.py          # FastAPI app, routers, endpoints
├── models.py        # Database models (SQLAlchemy or Pydantic/Motor)
├── schemas.py       # Pydantic schemas for request/response validation
├── database.py      # Database connection setup
├── crud.py          # Database operations (if applicable)
├── auth.py          # Authentication logic (UserService only)
├── requirements.txt # Python dependencies
└── Dockerfile       # Container build instructions
```

## Deployment

**Docker Compose** (Local/Development):
- Defined in `docker-compose.yml`
- Creates `uitgo-net` bridge network for service communication
- Persists data in named volumes: `mongodb_data`, `redis_data`, `postgres_data`

**Kubernetes** (k8s/ directory):
- Individual YAML manifests for each service deployment
- Requires external database setup or StatefulSets

**Terraform** (terraform/ directory):
- Infrastructure as Code for Azure deployment
- Includes ACR (Azure Container Registry) setup
- Variables defined in `variables.tf`

## Key Technical Decisions

1. **Database per Service**: Each service has isolated database (uitgo_users, uitgo_trips, uitgo_drivers, uitgo_payments) following microservices best practices
2. **Redis for Geospatial**: LocationService uses Redis GEOSEARCH for efficient nearby driver queries
3. **JWT Service Tokens**: Internal service authentication uses JWT tokens with `type=service` claim (not OAuth2 client credentials grant)
4. **WebSocket Centralization**: All real-time communication routed through LocationService to avoid connection sprawl
5. **External API Dependencies**: Mapbox for routing/geocoding, VNPay for payments (sandbox mode by default)

## Important Considerations

- **Token Expiry**: Current JWT tokens expire in 30 minutes (ACCESS_TOKEN_EXPIRE_MINUTES)
- **Service Token Security**: Consider adding `aud` (audience) claim to service tokens and validating it at DriverService to prevent token misuse
- **VNPay Callback URL**: PaymentService reads `BASE_URL` from environment (not `NGROK_API_URL`); ensure this is set to publicly accessible HTTPS URL
- **Database Auth**: MongoDB connection strings use `authSource=admin` parameter
- **CORS**: Services may need CORS configuration for frontend integration

## Common Development Tasks

### Adding a New Endpoint

1. Define Pydantic schema in `schemas.py`
2. Add route handler in `main.py` with appropriate HTTP method decorator
3. Implement business logic (call database via `crud.py` or external services)
4. Update inter-service dependencies if endpoint is called by other services

### Modifying Database Schema

**MongoDB services** (Trip/Driver/Payment):
- Pydantic models in `models.py` are schema-less; no migrations needed
- Update model class and schema definitions

**PostgreSQL services** (User):
- Requires Alembic migrations (not currently configured)
- Consider adding Alembic for production use

### Testing Service Communication

```bash
# Get a user JWT token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# Test internal service-to-service flow (requires service running)
# Check TripService logs when creating trip to see service token acquisition
```

### Debugging WebSocket Connections

```bash
# Monitor Redis keys for connected drivers
docker exec -it uitgo-redis redis-cli KEYS "driver:*"

# Check location data
docker exec -it uitgo-redis redis-cli GEORADIUS drivers:locations 106.6297 10.8231 5 km
```

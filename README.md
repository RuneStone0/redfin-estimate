# Redfin Estimate API

API for fetching property estimates from Redfin. This service exposes a REST API endpoint that queries Redfin's property estimate service and returns clean JSON data.

## Features

- FastAPI-based REST API
- Handles Redfin's malformed JSON response format
- Docker containerized for easy deployment
- Automatic OpenAPI documentation
- Health check endpoint

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+ with pip

## Quick Start with Docker

### Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Using Docker directly

```bash
# Build the image
docker build -t redfin-estimate-api .

# Run the container
docker run -p 8000:8000 redfin-estimate-api
```

## Local Development

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Get Property Details

**Endpoint:** `GET /api/property`

**Query Parameters:**
- `propertyId` (required): Redfin property ID (integer)

**Example Request:**
```bash
curl "http://localhost:8000/api/property?propertyId=109913415"
```

**Example Response:**
```json
{
  "status": {
    "displayValue": "Off Market"
  },
  "priceInfo": {
    "label": "Last Sold Price",
    "displayLevel": 1
  },
  "sqFt": {
    "displayLevel": 1,
    "value": 1756
  },
  "pricePerSqFt": 192,
  "streetAddress": {
    "streetNumber": "16401",
    "streetName": "Fetching",
    "streetType": "Ave",
    "assembledAddress": "16401 Fetching Ave"
  },
  "latLong": {
    "latitude": 30.2984002,
    "longitude": -97.5556566
  },
  "beds": 3,
  "baths": 2.0,
  "yearBuilt": 2020,
  "city": "Manor",
  "state": "TX",
  "zip": "78653",
  "lotSize": 5998,
  "avmInfo": {
    "propertyId": 109913415,
    "predictedValue": 336885.28
  }
}
```

### Get Property Value

**Endpoint:** `GET /api/property/value`

**Query Parameters:**
- `propertyId` (required): Redfin property ID (integer)

**Example Request:**
```bash
curl "http://localhost:8000/api/property/value?propertyId=109913415"
```

**Example Response:**
```json
{
  "predictedValue": 336885.28
}
```

### Health Check

**Endpoint:** `GET /health`

Returns the health status of the API.

**Example Request:**
```bash
curl http://localhost:8000/health
```

**Example Response:**
```json
{
  "status": "healthy"
}
```

### Root Endpoint

**Endpoint:** `GET /`

Returns API information and available endpoints.

## OpenAPI Documentation

FastAPI automatically generates interactive OpenAPI documentation. Once the server is running, access:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Project Structure

```
redfin-estimate/
├── app/
│   └── main.py          # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker container definition
├── docker-compose.yml  # Docker Compose configuration
├── .dockerignore       # Docker ignore patterns
├── .gitignore         # Git ignore patterns
└── README.md          # This file
```

## How It Works

1. The API receives a `propertyId` query parameter
2. It makes an HTTP request to Redfin's property estimate endpoint
3. Redfin returns a malformed JSON response starting with `{}&&`
4. The API parses and cleans the response by removing the `{}&&` prefix
5. The cleaned JSON payload is returned to the client

## Error Handling

The API handles various error scenarios:

- **400 Bad Request:** Invalid property ID or malformed request
- **503 Service Unavailable:** Unable to connect to Redfin API
- **500 Internal Server Error:** JSON parsing errors or unexpected issues

## Development

### Running Tests

```bash
# Install test dependencies (if any)
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Style

This project follows PEP 8 style guidelines. Consider using `black` for code formatting:

```bash
pip install black
black app/
```

## License

This project is provided as-is for educational and development purposes.

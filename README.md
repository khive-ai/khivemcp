# AutoMCP

A lightweight implementation of the Model Context Protocol (MCP) with a modern web interface.

## Features

- **Service Groups**: Organize operations into logical groups
- **Configuration-Driven**: Easy service deployment via YAML/JSON configs
- **Modern Web Interface**: FastAPI backend with Streamlit frontend
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Development Tools**: Comprehensive development and testing utilities

## Installation

### Using pip

```bash
pip install automcp
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/automcp
cd automcp

# Setup development environment
./scripts/dev.sh setup
```

## Usage

### Running a Service

1. Create a service configuration (e.g., `service.yaml`):
```yaml
name: my-service
description: Example service
groups:
  "mypackage.groups:MyGroup":
    name: my-group
    config:
      setting: value
```

2. Run the service:
```bash
automcp run service.yaml
```

### Using the Web Interface

1. Start the API server:
```bash
./scripts/dev.sh api
```

2. Start the frontend:
```bash
./scripts/dev.sh frontend
```

3. Visit http://localhost:8501 in your browser

## Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Individual Services

```bash
# Build image
docker build -t automcp .

# Run API server
docker run -p 8000:8000 automcp

# Run frontend
docker run -p 8501:8501 automcp streamlit run automcp/api/frontend.py
```

## Development

### Directory Structure

```
automcp/
├── core/           # Core implementation
├── api/            # FastAPI and Streamlit apps
├── schemas/        # Data models
├── services/       # Service implementations
└── utils/          # Utility functions

scripts/            # Development scripts
tests/              # Test suite
examples/           # Example services
docs/               # Documentation
```

### Development Commands

```bash
# Setup environment
./scripts/dev.sh setup

# Run tests
./scripts/dev.sh test

# Run linters
./scripts/dev.sh lint

# Start services
./scripts/dev.sh all

# Clean environment
./scripts/dev.sh clean
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=automcp

# Run specific test
pytest tests/test_specific.py
```

## Configuration

### Service Configuration

```yaml
name: service-name
description: Service description
groups:
  "module.path:GroupClass":
    name: group-name
    packages:
      - package1
    config:
      setting: value
```

### Group Configuration

```json
{
  "name": "group-name",
  "description": "Group description",
  "config": {
    "setting": "value"
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

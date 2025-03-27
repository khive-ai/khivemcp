#!/bin/bash
set -e

# Function to display help message
show_help() {
    echo "AutoMCP Development Script"
    echo
    echo "Usage: ./scripts/dev.sh [command]"
    echo
    echo "Commands:"
    echo "  setup      Setup development environment"
    echo "  test       Run tests"
    echo "  lint       Run linters"
    echo "  api        Start API server"
    echo "  frontend   Start frontend"
    echo "  all        Start all services"
    echo "  clean      Clean development environment"
    echo "  help       Show this help message"
}

# Function to setup development environment
setup() {
    echo "Setting up development environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements-dev.txt
    
    # Install pre-commit hooks
    pre-commit install
    
    echo "Development environment setup complete!"
}

# Function to run tests
run_tests() {
    echo "Running tests..."
    pytest tests/ -v --cov=automcp
}

# Function to run linters
run_lint() {
    echo "Running linters..."
    black .
    isort .
    ruff check .
    mypy automcp/
}

# Function to start API server
start_api() {
    echo "Starting API server..."
    uvicorn automcp.api.server:app --reload --host 0.0.0.0 --port 8000
}

# Function to start frontend
start_frontend() {
    echo "Starting frontend..."
    streamlit run automcp/api/frontend.py
}

# Function to start all services
start_all() {
    echo "Starting all services..."
    docker-compose up --build
}

# Function to clean development environment
clean() {
    echo "Cleaning development environment..."
    
    # Remove virtual environment
    rm -rf venv
    
    # Remove Python cache files
    find . -type d -name "__pycache__" -exec rm -r {} +
    find . -type f -name "*.pyc" -delete
    
    # Remove test cache
    rm -rf .pytest_cache
    rm -rf .coverage
    
    # Remove build artifacts
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info
    
    echo "Clean complete!"
}

# Main script logic
case "$1" in
    "setup")
        setup
        ;;
    "test")
        run_tests
        ;;
    "lint")
        run_lint
        ;;
    "api")
        start_api
        ;;
    "frontend")
        start_frontend
        ;;
    "all")
        start_all
        ;;
    "clean")
        clean
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './scripts/dev.sh help' for usage information"
        exit 1
        ;;
esac

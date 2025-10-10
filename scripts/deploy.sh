#!/bin/bash
# Deployment script for Data Extraction Pipeline

set -e  # Exit on any error

echo "🚀 Starting Data Extraction Pipeline deployment..."

# Configuration
PROJECT_NAME="data-extraction-pipeline"
DOCKER_IMAGE="$PROJECT_NAME:latest"
COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Prerequisites check passed ✅"
}

# Validate configuration
validate_config() {
    print_status "Validating configuration..."
    
    if [ ! -f "config.yaml" ]; then
        print_error "config.yaml not found. Please create configuration file."
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Using default configuration."
        if [ -f ".env.example" ]; then
            print_status "Copying .env.example to .env"
            cp .env.example .env
        fi
    fi
    
    print_status "Configuration validation completed ✅"
}

# Build Docker image
build_image() {
    print_status "Building Docker image..."
    
    docker build -t $DOCKER_IMAGE . || {
        print_error "Failed to build Docker image"
        exit 1
    }
    
    print_status "Docker image built successfully ✅"
}

# Deploy with Docker Compose
deploy_compose() {
    print_status "Deploying with Docker Compose..."
    
    # Stop existing containers
    docker-compose -f $COMPOSE_FILE down || true
    
    # Start new containers
    docker-compose -f $COMPOSE_FILE up -d || {
        print_error "Failed to deploy with Docker Compose"
        exit 1
    }
    
    print_status "Docker Compose deployment completed ✅"
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Wait for containers to start
    sleep 10
    
    # Check container status
    if docker-compose -f $COMPOSE_FILE ps | grep -q "Up"; then
        print_status "Containers are running ✅"
    else
        print_error "Some containers failed to start"
        docker-compose -f $COMPOSE_FILE logs
        exit 1
    fi
    
    # Test pipeline functionality
    print_status "Testing pipeline functionality..."
    docker-compose -f $COMPOSE_FILE exec -T pipeline python run_pipeline.py --config config.yaml --validate-only || {
        print_error "Pipeline validation failed"
        exit 1
    }
    
    print_status "Health check completed ✅"
}

# Show deployment status
show_status() {
    print_status "Deployment Status:"
    echo "===================="
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    print_status "To view logs: docker-compose logs -f"
    print_status "To stop: docker-compose down"
    print_status "To restart: docker-compose restart"
}

# Main deployment process
main() {
    echo "🔧 Data Extraction Pipeline Deployment"
    echo "======================================"
    
    check_prerequisites
    validate_config
    build_image
    deploy_compose
    health_check
    show_status
    
    print_status "🎉 Deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "build")
        check_prerequisites
        build_image
        ;;
    "start")
        docker-compose -f $COMPOSE_FILE up -d
        ;;
    "stop")
        docker-compose -f $COMPOSE_FILE down
        ;;
    "restart")
        docker-compose -f $COMPOSE_FILE restart
        ;;
    "logs")
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    "status")
        docker-compose -f $COMPOSE_FILE ps
        ;;
    "test")
        docker-compose -f $COMPOSE_FILE exec pipeline python run_pipeline.py --config config.yaml --mock-mode
        ;;
    *)
        echo "Usage: $0 {deploy|build|start|stop|restart|logs|status|test}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment (default)"
        echo "  build    - Build Docker image only"
        echo "  start    - Start containers"
        echo "  stop     - Stop containers"
        echo "  restart  - Restart containers"
        echo "  logs     - View container logs"
        echo "  status   - Show container status"
        echo "  test     - Run pipeline test"
        exit 1
        ;;
esac
#!/bin/bash
# Setup script for Data Extraction Pipeline development environment

set -e

echo "🔧 Setting up Data Extraction Pipeline development environment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
check_python() {
    print_status "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    print_status "Python version: $python_version"
    
    # Check if version is 3.8 or higher
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_status "Python version check passed ✅"
    else
        print_error "Python 3.8 or higher is required. Current version: $python_version"
        exit 1
    fi
}

# Create virtual environment
setup_venv() {
    print_status "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created ✅"
    else
        print_status "Virtual environment already exists ✅"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    print_status "Pip upgraded ✅"
}

# Install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Dependencies installed ✅"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p data logs test_data
    mkdir -p data/whatsapp data/email
    mkdir -p logs
    
    print_status "Directories created ✅"
}

# Setup configuration files
setup_config() {
    print_status "Setting up configuration files..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "Created .env from .env.example"
            print_warning "Please edit .env file with your actual credentials"
        else
            print_warning ".env.example not found"
        fi
    else
        print_status ".env file already exists ✅"
    fi
    
    if [ ! -f "config.yaml" ]; then
        print_error "config.yaml not found. Please create configuration file."
        exit 1
    else
        print_status "config.yaml found ✅"
    fi
}

# Run tests
run_tests() {
    print_status "Running basic tests..."
    
    # Test configuration validation
    python run_pipeline.py --config config.test.yaml --validate-only
    
    # Run mock extraction test
    python run_pipeline.py --config config.test.yaml --mock-mode
    
    print_status "Basic tests completed ✅"
}

# Main setup process
main() {
    echo "🚀 Data Extraction Pipeline Setup"
    echo "================================="
    
    check_python
    setup_venv
    install_dependencies
    create_directories
    setup_config
    run_tests
    
    print_status "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your API credentials"
    echo "2. Customize config.yaml for your needs"
    echo "3. Run: source venv/bin/activate"
    echo "4. Test: python run_pipeline.py --config config.yaml --validate-only"
}

main
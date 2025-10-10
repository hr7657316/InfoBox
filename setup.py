#!/usr/bin/env python3
"""
Setup script for Data Extraction Pipeline

This script allows the pipeline to be installed as a Python package,
making it easier to deploy and manage dependencies.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8') if (this_directory / "README.md").exists() else ""

# Read requirements from requirements.txt
def read_requirements():
    """Read requirements from requirements.txt file."""
    requirements_file = this_directory / "requirements.txt"
    if not requirements_file.exists():
        return []
    
    requirements = []
    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                # Handle conditional requirements
                if ';' in line:
                    requirements.append(line)
                else:
                    requirements.append(line)
    return requirements

# Package metadata
setup(
    name="data-extraction-pipeline",
    version="1.0.0",
    author="Data Extraction Pipeline Team",
    author_email="pipeline@example.com",
    description="Automated data extraction pipeline for WhatsApp and email sources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/data-extraction-pipeline",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/data-extraction-pipeline/issues",
        "Documentation": "https://github.com/yourusername/data-extraction-pipeline/wiki",
        "Source Code": "https://github.com/yourusername/data-extraction-pipeline",
    },
    
    # Package discovery
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    
    # Include non-Python files
    include_package_data=True,
    package_data={
        "pipeline": [
            "*.yaml",
            "*.yml", 
            "*.json",
            "*.txt",
        ],
    },
    
    # Dependencies
    install_requires=read_requirements(),
    
    # Optional dependencies for enhanced functionality
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "advanced": [
            "pandas>=2.0.0",
            "cryptography>=41.0.0",
        ],
        "all": [
            "pytest>=8.0.0",
            "pytest-cov>=4.0.0", 
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pandas>=2.0.0",
            "cryptography>=41.0.0",
        ],
    },
    
    # Entry points for command-line usage
    entry_points={
        "console_scripts": [
            "data-extraction-pipeline=pipeline.main:main",
            "dep=pipeline.main:main",  # Short alias
        ],
    },
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Package classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Email",
        "Topic :: Communications :: Chat",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Archiving",
        "Topic :: Utilities",
    ],
    
    # Keywords for package discovery
    keywords=[
        "data-extraction",
        "whatsapp",
        "email",
        "automation",
        "pipeline",
        "messaging",
        "api",
        "imap",
        "business-api",
    ],
    
    # License
    license="MIT",
    
    # Zip safety
    zip_safe=False,
)
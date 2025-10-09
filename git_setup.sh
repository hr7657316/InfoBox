#!/bin/bash
# Git setup script for pushing to GitHub

echo "🚀 Setting up Git repository for Integrated Data Extraction System"
echo "=================================================================="

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Add all files to git
echo "📁 Adding files to Git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "🎉 Initial commit: Integrated Data Extraction + Document Processing System

Features:
- 📊 Data Extraction Pipeline (WhatsApp + Email)
- 📄 InfoBox Document Processing with AI
- 🌐 Modern Web Interface
- 🤖 AI Integration (Google Gemini + LangExtract)
- 📧 Smart Email Assignment
- 🧪 Comprehensive Testing Suite
- 🚀 Docker Deployment Support
- 📚 Complete Documentation

Ready for production deployment!"

echo ""
echo "✅ Initial commit created successfully!"
echo ""
echo "🌐 Next steps to push to GitHub:"
echo "1. Create a new repository on GitHub"
echo "2. Copy the repository URL"
echo "3. Run the following commands:"
echo ""
echo "   git remote add origin https://github.com/yourusername/your-repo-name.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "📋 Repository contents:"
git log --oneline -1
echo ""
echo "📊 Files ready for GitHub:"
git ls-files | head -20
if [ $(git ls-files | wc -l) -gt 20 ]; then
    echo "... and $(( $(git ls-files | wc -l) - 20 )) more files"
fi
echo ""
echo "🎯 Repository is ready for GitHub!"
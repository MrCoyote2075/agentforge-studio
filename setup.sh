#!/bin/bash
echo "AgentForge Studio - Quick Setup"
echo "================================"

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please add your Gemini API keys!"
fi

# Install dependencies
pip install -r requirements.txt

# Setup frontend if directory exists
if [ -d "frontend" ]; then
    cd frontend && npm install && cd ..
else
    echo "Frontend directory not found, skipping npm install"
fi

echo ""
echo "Setup complete! Next steps:"
echo "1. Edit .env and add your GEMINI_API_KEY_1 and GEMINI_API_KEY_2"
echo "2. Run backend: cd backend && uvicorn main:app --reload"
echo "3. Run frontend: cd frontend && npm run dev"
echo "4. Open http://localhost:3000"

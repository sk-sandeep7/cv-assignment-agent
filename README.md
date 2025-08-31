# GC Agent - AI Question Generation System

An intelligent question generation and evaluation system built with React frontend and FastAPI backend, powered by Azure OpenAI.

## 🚀 Features

- **AI-Powered Question Generation**: Generate questions based on topics using Azure OpenAI
- **Custom Question Input**: Refine questions with custom input and requirements
- **Evaluation Rubrics**: Generate detailed evaluation criteria for each question
- **Question Management**: Regenerate individual or all questions
- **Interactive UI**: Modern React interface with loading states and modals
- **Fuzzy Topic Matching**: Smart topic matching using difflib

## 📁 Project Structure

```
GC_Agent/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main FastAPI application
│   ├── generate_openai.py  # OpenAI integration
│   ├── evaluation_openai.py # Evaluation rubrics generation
│   ├── get_examples.py     # Few-shot examples
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example       # Environment variables template
│   └── assignments.db     # SQLite database
├── gc-agent/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.jsx       # Main App component
│   │   └── main.jsx      # Entry point
│   ├── package.json      # Node.js dependencies
│   └── vite.config.js    # Vite configuration
└── README.md
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- Azure OpenAI API access

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   ```bash
   # Copy the example file
   copy .env.example .env
   
   # Edit .env with your actual API keys
   ```

6. **Start the backend server**
   ```bash
   uvicorn main:app --reload
   ```

   Backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd gc-agent
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

   Frontend will be available at `http://localhost:5173`

## 🔧 Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```env
AZURE_OPENAI_ENDPOINT=your-azure-endpoint-here
OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_KEY=your-azure-api-key-here
```

## 🧪 Testing

1. Start both backend and frontend servers
2. Navigate to `http://localhost:5173`
3. Enter topics (e.g., "computer vision, image processing")
4. Select number of questions
5. Click "Generate Assignments"

## 🔒 Security Notes

- Never commit `.env` files with real API keys
- Use environment variables for all sensitive data
- Update CORS settings for production deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🐛 Troubleshooting

### Common Issues

1. **"Module not found" errors**: Ensure all dependencies are installed
2. **CORS errors**: Check if backend is running on port 8000
3. **API key errors**: Verify environment variables are set correctly
4. **Database errors**: Ensure SQLite database file exists

### Getting Help

If you encounter issues, please check:
1. All environment variables are set correctly
2. Both servers are running
3. Dependencies are installed
4. API keys have proper permissions

## 🏗️ Built With

- **Frontend**: React 18, Vite, React Router
- **Backend**: FastAPI, Python 3.8+
- **AI**: Azure OpenAI (GPT-4)
- **Database**: SQLite
- **Styling**: CSS3, Custom components

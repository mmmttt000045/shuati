# Quiz Application

A web-based quiz application built with Flask and Vue 3.

## Features

- Multiple choice questions
- True/False questions
- Progress tracking
- Score summary
- Subject-based organization

## Project Structure

```
.
├── app.py              # Flask backend
├── frontend/          # Vue 3 frontend
│   ├── src/
│   │   ├── components/
│   │   ├── router/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── subject/           # Question bank Excel files
└── templates/         # Flask templates
```

## Setup

### Backend (Flask)

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install flask pandas openpyxl
   ```

3. Start the Flask server:
   ```bash
   python app.py
   ```

### Frontend (Vue 3)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Adding Question Banks

1. Create a subject folder in the `subject` directory:
   ```
   subject/
   └── YourSubject/
       └── questions.xlsx
   ```

2. Excel file format:
   - Required columns:
     - 题干 (Question)
     - 答案 (Answer)
     - 题型 (Question Type)
   - For multiple choice questions:
     - A, B, C, D (Options)

## Development

### Backend

- Flask server runs on `http://localhost:5000`
- API endpoints:
  - GET `/api/file_options` - List available question banks
  - POST `/api/start_practice` - Start a practice session
  - GET `/api/practice/question` - Get current question
  - POST `/api/practice/submit` - Submit answer
  - GET `/api/completed_summary` - Get practice summary

### Frontend

- Vue development server runs on `http://localhost:5173`
- API requests are proxied to the Flask backend
- Components:
  - `IndexPage.vue` - Question bank selection
  - `PracticePage.vue` - Quiz interface
  - `CompletedPage.vue` - Practice summary

## License

MIT 
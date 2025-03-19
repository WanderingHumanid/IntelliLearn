# IntelliLearn - AI Assisted Learning Platform

A modern, responsive web application that helps students learn more effectively using AI assistance and community engagement.

## Features

- 🤖 AI-powered chatbot using Llama 3.2
- 💬 Student community forum
- 🎯 Personalized learning roadmaps
- 🏆 Gamification system (levels, streaks, points)
- 📱 Mobile-friendly design
- 🌙 Dark theme with colorful accents

## Prerequisites

- Python 3.8 or higher
- Ollama installed and running locally with Llama 3.2 model
- Git (for cloning the repository)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/intelli-learn.git
cd intelli-learn
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Make sure Ollama is running locally with the Llama 3.2 model:
```bash
ollama run llama2
```

## Configuration

1. Create a `.env` file in the project root:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
```

2. The application will automatically create the SQLite database in the `db` directory when first run.

## Running the Application

1. Start the Flask development server:
```bash
flask run
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
intelli-learn/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md          # Project documentation
├── static/            # Static files (CSS, JS, images)
├── templates/         # HTML templates
├── api/              # API routes and handlers
└── db/               # Database files
```

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [Ollama](https://ollama.ai/) - Local AI model hosting
- [Font Awesome](https://fontawesome.com/) - Icons 
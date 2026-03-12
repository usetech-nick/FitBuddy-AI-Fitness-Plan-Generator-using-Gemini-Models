# 💪 FitBuddy – AI Powered Fitness Plan Generator

FitBuddy is a full-stack AI-powered fitness web application that generates personalized 7-day workout plans based on user fitness goals, age, weight, and preferred workout intensity.

The application uses Google Gemini AI to intelligently create workout schedules and nutrition suggestions tailored to the user's needs.

## 🚀 Features

- 🧠 **AI Generated Workout Plans** — Automatically generates structured 7-day workout routines
- 🎯 **Goal Based Customization**
  - Weight Loss
  - Muscle Gain
  - General Wellness
- 🔄 **Feedback Loop** — Users can regenerate plans if they want a different workout routine
- 🥗 **Daily Nutrition Tips** — AI-generated nutrition suggestions to complement workouts
- 💾 **Database Storage** — Plans and user data stored in SQLite
- 🎨 **Responsive UI** — Clean and simple user interface

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| ORM | SQLAlchemy |
| AI Model | Google Gemini 2.5 Flash |

## 📂 Project Structure
```
FitBuddy/
│
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database setup
│   │
│   ├── routes/
│   │   └── plan.py          # API endpoints
│   │
│   └── services/
│       └── ai_service.py    # Gemini API integration
│
├── templates/               # HTML templates
│
├── static/
│   ├── css/                 # Stylesheets
│   └── js/                  # Frontend scripts
│
├── fitness.db               # SQLite database
├── requirements.txt
└── README.md
```

## ⚙️ Installation & Setup

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/fitbuddy.git
cd fitbuddy
```

**2. Create a virtual environment**
```bash
python -m venv venv
```

Activate it:

- Linux / Mac: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the root directory:
```
GEMINI_API_KEY=your_google_gemini_api_key
```

**5. Run the application**
```bash
uvicorn app.main:app --reload
```

Application will run at `http://127.0.0.1:8000`

## 📊 Example Workflow

1. User enters age, weight, fitness goal, and workout intensity
2. Backend sends request to Gemini API
3. AI generates a 7-day workout plan and nutrition tips
4. Plan is stored in SQLite database
5. User can regenerate the plan if needed

## 🔮 Future Improvements

- User authentication
- Workout progress tracking
- Fitness analytics dashboard
- Mobile optimization
- Integration with fitness wearables

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## 📜 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Nishant Kumar**

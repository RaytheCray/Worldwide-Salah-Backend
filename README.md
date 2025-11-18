# Worldwide Salah - Backend API

Flask REST API for calculating Islamic prayer times, Qibla direction, and Ramadan schedules.

## Features

- Prayer time calculations using astronomical algorithms
- Multiple calculation methods (ISNA, MWL, Egyptian, Karachi, Makkah, Tehran)
- Hanafi and Standard Asr time calculations
- Qibla direction calculation
- Ramadan date and fasting schedule
- Monthly prayer timetables

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/worldwide-salah-backend.git
cd worldwide-salah-backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Get Prayer Times
**POST** `/api/prayer-times`

Request:
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "date": "2025-11-18",
  "method": "ISNA",
  "asr_method": "standard"
}
```

### Get Monthly Prayers
**POST** `/api/monthly-prayers`

Request:
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "year": 2025,
  "month": 11,
  "method": "ISNA",
  "asr_method": "standard"
}
```

### Get Ramadan Schedule
**POST** `/api/ramadan`

Request:
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "year": 2025,
  "method": "ISNA"
}
```

### Get Qibla Direction
**POST** `/api/qibla`

Request:
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

### Get Calculation Methods
**GET** `/api/calculation-methods`

### Health Check
**GET** `/api/health`

## Deployment

### Heroku
```bash
heroku create worldwide-salah-api
git push heroku main
```

### Railway
1. Connect your GitHub repository
2. Deploy automatically

### Render
1. Connect your GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn app:app`

## Environment Variables

- `FLASK_ENV`: development or production
- `PORT`: Server port (default: 5000)
- `HOST`: Server host (default: 0.0.0.0)
- `CORS_ORIGINS`: Allowed CORS origins

## License

MIT License
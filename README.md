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

### Render (recommended)
This repo includes a `render.yaml` Blueprint that creates the API and a PostgreSQL database together.

1. Sign in at https://render.com with GitHub
2. **New → Blueprint**, then select this repository
3. Click **Apply**. Render creates the database, installs dependencies, and starts the API
4. On first start, `init_db.py` creates the tables from `schema.sql` (it skips this on later starts)
5. Your API is live at `https://<service-name>.onrender.com/api/health`

Notes:
- The free web service sleeps after ~15 minutes of inactivity; the first request afterwards takes up to a minute
- Render's free PostgreSQL database expires after 30 days. For a database that doesn't expire, create one on
  Neon (https://neon.tech) and set the service's `DATABASE_URL` environment variable to its connection string

### Other hosts
- Build command: `pip install -r requirements.txt`
- Start command: `python init_db.py && gunicorn app:app --bind 0.0.0.0:$PORT`
- Set `DATABASE_URL` to your PostgreSQL connection string

## Environment Variables

- `FLASK_ENV`: development or production
- `PORT`: Server port (default: 5000)
- `DATABASE_URL`: PostgreSQL connection string (used instead of the `DB_*` variables when set)
- `HOST`: Server host (default: 0.0.0.0)
- `CORS_ORIGINS`: Allowed CORS origins

## License

MIT License
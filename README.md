# 🗓️ Race Scheduler

A full-stack scheduling application with admin/user login, calendar view, and conflict-aware meeting scheduling.

## 🔧 Tech Stack

- Frontend: React, TypeScript, Ant Design, FullCalendar
- Backend: FastAPI, PostgreSQL, SQLAlchemy, JWT
- Auth: JWT token stored in localStorage

## 🚀 Features

- ✅ Login & Register
- ✅ JWT Auth
- ✅ FullCalendar UI
- ✅ Conflict detection on scheduling
- ✅ Role-based access

## 📦 How to Run

### Backend
1. `cd backend`
2. `python -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Create `.env` file
5. Run: `uvicorn app.main:app --reload`

### Frontend
1. `cd race-scheduler`
2. `npm install`
3. `npm start`

## 📬 API Endpoints

- `POST /users/register`
- `POST /users/login`
- `GET /events/`
- `POST /events/`

## 👤 Admin Features (future)
- View all users’ calendars
- Manage events

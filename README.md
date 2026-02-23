# Expense Splitter

A full-stack expense splitting application built with **FastAPI** and **React**. Track shared expenses, split bills equally or with custom amounts, settle debts, and export data — all with a responsive UI that works on desktop and mobile.

## Tech Stack

| Layer      | Technology                                           |
|------------|------------------------------------------------------|
| Backend    | Python, FastAPI, SQLAlchemy, SQLite, Pydantic, JWT   |
| Frontend   | React 19, Vite, CSS (custom, no framework)           |
| Auth       | JWT tokens, PBKDF2-SHA256 password hashing           |
| DevOps     | Docker, Docker Compose, Nginx                        |
| Testing    | Pytest, FastAPI TestClient                           |

## Features

### Core
- **User authentication** — register/login with JWT, auto-persist sessions
- **Group management** — create, edit, delete groups; add/remove members by email
- **Expense tracking** — add, edit, delete expenses with descriptions
- **Expense categories** — food, transport, housing, entertainment, utilities, shopping, health, travel, education, other
- **Split modes** — equal split, only-me, or custom per-person amounts
- **Settlement calculator** — minimal-transfer algorithm to settle debts
- **Settle up** — record payments to mark debts as paid

### Data & Insights
- **Dashboard** — total spending, expense count, your balance, category breakdown bars, per-member spending
- **Search & filter** — search expenses by description, filter by category
- **CSV export** — download all group expenses as a spreadsheet

### UX
- **Responsive design** — mobile-first with tab navigation on small screens
- **Dark/light theme** — toggle with preference saved to localStorage
- **Toast notifications** — success/error feedback with auto-dismiss
- **Confirmation dialogs** — before destructive actions (delete group/expense/member)
- **Loading indicator** — top-of-page progress bar during API calls
- **Error boundary** — graceful crash recovery with reload button
- **Input validation** — max lengths, amount limits, type constraints
- **PWA manifest** — installable on mobile devices

### DevOps
- **Environment config** — API URL configurable via `VITE_API_URL`
- **Docker support** — Dockerfiles for backend and frontend, docker-compose for one-command deploy
- **Backend tests** — 20+ pytest tests covering auth, groups, expenses, settlements, dashboard, CSV export

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 20+

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API runs at http://127.0.0.1:8000. Interactive docs at http://127.0.0.1:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:5173.

### Run Tests

```bash
cd backend
pytest tests/ -v
```

### Docker

```bash
docker-compose up --build
```

Frontend at http://localhost:3000, backend at http://localhost:8000.

## API Endpoints

| Method   | Path                                    | Description             |
|----------|-----------------------------------------|-------------------------|
| POST     | `/api/auth/register`                    | Register a new user     |
| POST     | `/api/auth/login`                       | Login                   |
| GET      | `/api/groups`                           | List your groups        |
| POST     | `/api/groups`                           | Create a group          |
| GET      | `/api/groups/:id`                       | Get group details       |
| PATCH    | `/api/groups/:id`                       | Update group            |
| DELETE   | `/api/groups/:id`                       | Delete group            |
| POST     | `/api/groups/:id/members`               | Add member by email     |
| DELETE   | `/api/groups/:id/members/:uid`          | Remove member           |
| GET      | `/api/expenses?group_id=&search=&category=` | List/search expenses |
| POST     | `/api/expenses`                         | Create expense          |
| GET      | `/api/expenses/:id`                     | Get expense             |
| PATCH    | `/api/expenses/:id`                     | Update expense          |
| DELETE   | `/api/expenses/:id`                     | Delete expense          |
| GET      | `/api/expenses/export?group_id=`        | Export CSV              |
| GET      | `/api/settlements/group/:id`            | Get settlements         |
| POST     | `/api/settlements/pay`                  | Record payment          |
| GET      | `/api/settlements/payments/:id`         | List payments           |
| GET      | `/api/settlements/dashboard/:id`        | Dashboard stats         |

## What This Project Demonstrates

- **Full-stack architecture** — clean separation of concerns between API and UI
- **RESTful API design** — proper HTTP methods, status codes, error handling
- **ORM patterns** — SQLAlchemy models with relationships, association tables
- **Authentication** — JWT with secure password hashing
- **Responsive CSS** — mobile-first design with CSS variables for theming
- **State management** — React hooks for complex multi-panel UI
- **Testing** — comprehensive API test suite with fixtures
- **DevOps readiness** — Docker, environment config, production Nginx setup

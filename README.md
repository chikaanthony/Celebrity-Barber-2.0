# Celebrity Barber - Flask + Firebase App

A Flask web application with Firebase database integration for managing a barber shop.

## Prerequisites

- Python 3.8+
- Node.js (for Firebase CLI)
- Google Account (for Firebase)

## Setup Instructions

### 1. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Enable Authentication:
   - Go to Authentication → Sign-in method
   - Enable Email/Password
4. Enable Firestore Database:
   - Go to Firestore Database → Create database
   - Start in Test mode (or set rules for production)
5. Get Service Account Key:
   - Go to Project Settings → Service accounts
   - Click "Generate new private key"
   - Save as `serviceAccountKey.json` in the project root

### 2. Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your Firebase credentials

3. Place your Firebase service account key as `serviceAccountKey.json`

### 4. Run the Application

```bash
python app.py
```

The app will run at `http://localhost:5000`

## Firebase Firestore Structure

### Users Collection
```
users/{user_id}
  - uid: string
  - email: string
  - full_name: string
  - phone: string
  - referral_code: string
  - is_admin: boolean
  - is_vip: boolean
  - total_spent: number
  - referral_count: number
  - created_at: timestamp
```

### Bookings Collection
```
bookings/{booking_id}
  - user_id: string
  - service: string
  - price: number
  - date: timestamp
  - status: string (pending/completed/cancelled)
```

### Transactions Collection
```
transactions/{transaction_id}
  - user_id: string
  - type: string (income/expense)
  - amount: number
  - description: string
  - date: timestamp
```

### Approvals Collection
```
approvals/{approval_id}
  - user_id: string
  - type: string (booking/vip)
  - amount: number
  - status: string (pending/approved/rejected)
  - created_at: timestamp
```

## API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/signup` - User registration
- `GET /api/logout` - User logout

### User Routes (requires login)
- `GET /api/user/profile` - Get user profile
- `GET /api/user/bookings` - Get user bookings
- `GET /api/user/transactions` - Get user transactions

### Admin Routes (requires admin login)
- `GET /api/admin/users` - Get all users
- `GET /api/admin/analytics` - Get analytics
- `GET /api/admin/pending-approvals` - Get pending approvals

## Project Structure

```
MY APP 2.1/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── serviceAccountKey.json # Firebase service account (you provide this)
├── templates/             # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── clientdashboard.html
│   └── admin.html
└── static/               # CSS and static files
    ├── style.css
    ├── login.css
    ├── admin.css
    └── clientdashboard.css
```

## Creating an Admin User

To create an admin user:

1. Register a new user through the signup page
2. In Firebase Firestore, find the user document
3. Update the `is_admin` field to `true`

## License

MIT

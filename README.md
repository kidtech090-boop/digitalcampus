# SINCET College Digital Notice Board System

A full-featured digital notice board system for SINCET College with department-wise notices, events, results, attendance tracking, and TV display mode.

## Features

- **Multi-role Login**: Principal, HOD (per department), and General Viewer
- **Notice Board**: Create, manage, and display notices with attachments
- **Events**: Track college and department events
- **Results**: Upload and share exam results
- **Attendance**: Mark, view, and export student attendance
- **TV Display**: Full-screen department-wise digital signage
- **QR Codes**: Auto-generated QR codes for notices, events, and results
- **Real-time Updates**: WebSocket-based live content refresh

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open http://localhost:5000

### Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Principal | principalsincet@gmail.com | sincet123 |
| HOD (CSE) | csehodsincet@gmail.com | sincet123 |
| HOD (ECE) | ecehodsincet@gmail.com | sincet123 |
| General | any email | sincet123 |

---

## Deploy to Render.com (FREE - Recommended)

> **Why Render instead of Netlify?** Netlify only hosts static sites and serverless functions. This is a Flask backend app that needs a persistent Python server, database, WebSockets, and file uploads — none of which work on Netlify. **Render.com is free** and supports all of this out of the box.

### Steps:

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Restructured for deployment"
   git push origin main
   ```

2. **Go to [render.com](https://render.com)** and sign up (free)

3. **New → Web Service** → Connect your GitHub repo

4. Render auto-detects the config. Verify these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT wsgi:app`

5. Click **Create Web Service** → Your app will be live in ~2 minutes!

### Environment Variables (optional, set in Render dashboard):

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | auto-generated | Flask session secret |
| `PRINCIPAL_EMAIL` | principalsincet@gmail.com | Principal login email |
| `DEFAULT_PASSWORD` | sincet123 | Default password |

---

## Project Structure

```
├── app.py              # Main Flask application (all routes & models)
├── wsgi.py             # WSGI entry point for production server
├── requirements.txt    # Python dependencies
├── Procfile            # Process definition for Render/Heroku
├── render.yaml         # Render.com auto-deploy blueprint
├── runtime.txt         # Python version specification
├── .gitignore          # Git ignore rules
├── templates/          # Jinja2 HTML templates (28 files)
├── static/
│   ├── images/         # Static images (logo, etc.)
│   ├── uploads/        # User-uploaded content
│   │   ├── notices/
│   │   ├── events/
│   │   ├── results/
│   │   ├── media/
│   │   └── college_ads/
│   └── exports/        # Generated Excel exports
└── instance/           # SQLite database (auto-created)
```

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy, Flask-SocketIO
- **Database**: SQLite (auto-created)
- **Real-time**: WebSocket via SocketIO
- **Server**: Gunicorn with Eventlet workers

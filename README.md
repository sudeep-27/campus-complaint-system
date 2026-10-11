# 🎓 Campus Complaint Management System (CampusVoice)

A full-stack web application to digitize and automate campus grievance redressal for Students, Staff, and Administrators.

---

## 🚀 Features
- **Student Portal**: Register, submit complaints, track status timelines, provide feedback.
- **Admin Dashboard**: View all complaints, assign staff, update statuses, view live analytics.
- **Staff Portal**: View assigned complaints, update resolution status, communicate via comments.
- **Real-Time Updates**: Dashboard stats, donut chart, and table rows update instantly via AJAX without page reload.
- **Notification System**: Automated alerts for every status change.
- **Audit Trail**: Full history log of every complaint transition in `complaint_logs` table.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Jinja2 |
| Database | MySQL 8.0 (InnoDB), SQLite (fallback) |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript (ES6+) |
| Security | Bcrypt, Flask-Session, Parameterized SQL |
| APIs | RESTful API endpoints + AJAX Fetch calls |

---

## 🗄️ Database Features
- 8 Normalized Tables with Foreign Keys
- Multi-table DATABASE VIEW (`v_complaint_details`)
- 2 Automated TRIGGERS (auto-department routing + resolution timestamp)
- 2 STORED PROCEDURES (status update + dashboard summary)
- ON DELETE CASCADE, CHECK Constraints, UNIQUE Constraints

---

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/campus-complaint-system.git
cd campus-complaint-system
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up the MySQL database
- Start your MySQL server (XAMPP or MySQL Service).
- Open your MySQL command line client and run:
```sql
source database/schema.sql
```

### 4. Run the Flask application
```bash
python app.py
```

### 5. Open in browser
```
http://127.0.0.1:5000/
```

---

## 🔑 Default Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@campus.edu | admin123 |
| Student | arjun@student.edu | student123 |
| Staff | ravi@campus.edu | staff123 |

---

## 📁 Project Structure
```
campus-complaint-system/
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── database/
│   ├── schema.sql          # Full database schema (tables, views, triggers)
│   └── campus_complaints.db # SQLite fallback database
├── static/
│   ├── css/                # Custom stylesheets
│   ├── js/dashboard.js     # AJAX & real-time update controllers
│   └── uploads/            # Uploaded complaint attachments
└── templates/              # HTML pages (Jinja2 templates)
```

---

## 👨‍💻 Developed By
Sudeep | DBMS Mini Project | 2026

Project maintained by Sudeep.

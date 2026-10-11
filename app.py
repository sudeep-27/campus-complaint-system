import os
import sqlite3
import datetime
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_session import Session
from werkzeug.utils import secure_filename
import pymysql
from config import Config

# Initialize Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)
app.jinja_env.globals.update(isinstance=isinstance, str=str)

# Configure Flask session (using built-in session for ultimate localhost stability)
# Session(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  DATABASE STORAGE HELPER (MySQL with automatic SQLite Fallback)
# ══════════════════════════════════════════════════════════════
class DatabaseHelper:
    is_sqlite = False
    mysql_failed = False

    @classmethod
    def get_connection(cls):
        if cls.mysql_failed:
            db_dir = os.path.dirname(app.config['SQLITE_PATH'])
            os.makedirs(db_dir, exist_ok=True)
            conn = sqlite3.connect(app.config['SQLITE_PATH'])
            conn.row_factory = sqlite3.Row
            cls.is_sqlite = True
            cls._initialize_sqlite(conn)
            return conn

        try:
            # Try to connect to MySQL
            conn = pymysql.connect(
                host=app.config['DB_HOST'],
                user=app.config['DB_USER'],
                password=app.config['DB_PASSWORD'],
                database=app.config['DB_NAME'],
                port=app.config['DB_PORT'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            cls.is_sqlite = False
            cls._initialize_mysql(conn)
            return conn
        except Exception as e:
            # Cache failure to prevent repeated socket connection timeouts on subsequent calls
            cls.mysql_failed = True
            
            # Automatic Fallback to SQLite
            db_dir = os.path.dirname(app.config['SQLITE_PATH'])
            os.makedirs(db_dir, exist_ok=True)
            
            conn = sqlite3.connect(app.config['SQLITE_PATH'])
            conn.row_factory = sqlite3.Row  # Returns dict-like rows
            cls.is_sqlite = True
            
            # Setup tables if SQLite database is brand new
            cls._initialize_sqlite(conn)
            return conn

    @classmethod
    def _initialize_sqlite(cls, conn):
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            required = ['departments', 'users', 'categories', 'complaints', 'complaint_logs', 'comments', 'feedback', 'notifications']
            
            if not all(t in tables for t in required):
                raise ValueError("Missing tables")
                
            for t in required:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                row = cursor.fetchone()
                if not row or row[0] < 5:
                    raise ValueError(f"Table {t} has less than 5 rows")
                    
            cursor.execute("PRAGMA table_info(categories)")
            columns = [c[1] for c in cursor.fetchall()]
            if 'created_at' not in columns:
                raise ValueError("Missing created_at attribute")
                
            return  # Already seeded with new schema and data
        except Exception:
            pass
            
            # If we are here, database is partially initialized or needs upgrade. Clean up first.
            print("[INFO] Rebuilding SQLite database cleanly for DBMS Review-2...")
            for table in ['notifications', 'feedback', 'comments', 'complaint_logs', 'complaints', 'categories', 'users', 'departments']:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            cursor.execute("DROP VIEW IF EXISTS complaint_summary_view")

        print("[INFO] Initializing SQLite database fallback with schema and seed data...")
        
        # Create Tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT NOT NULL UNIQUE,
            dept_head TEXT,
            contact_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ('student','staff','admin')) DEFAULT 'student',
            roll_number TEXT,
            dept_id INTEGER,
            phone TEXT,
            profile_pic TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_name TEXT NOT NULL UNIQUE,
            description TEXT,
            dept_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','under_review','in_progress','resolved','rejected','closed')) DEFAULT 'pending',
            priority TEXT CHECK(priority IN ('low','medium','high','critical')) DEFAULT 'medium',
            user_id INTEGER NOT NULL,
            cat_id INTEGER,
            dept_id INTEGER,
            assigned_to INTEGER,
            attachment TEXT,
            location TEXT,
            is_anonymous INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (cat_id) REFERENCES categories(cat_id),
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
            FOREIGN KEY (assigned_to) REFERENCES users(user_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaint_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            changed_by INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT,
            remarks TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id),
            FOREIGN KEY (changed_by) REFERENCES users(user_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            remarks TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'general',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")

        # Create View in SQLite
        cursor.execute("""
        CREATE VIEW complaint_summary_view AS
        SELECT 
            c.complaint_id,
            c.title,
            c.status,
            c.priority,
            u.full_name AS student_name,
            s.full_name AS assigned_staff,
            d.dept_name,
            cat.cat_name,
            c.created_at
        FROM complaints c
        LEFT JOIN users u ON c.user_id = u.user_id
        LEFT JOIN users s ON c.assigned_to = s.user_id
        LEFT JOIN departments d ON c.dept_id = d.dept_id
        LEFT JOIN categories cat ON c.cat_id = cat.cat_id
        """)

        # Seed Departments
        departments = [
            ('IT & Infrastructure', 'Dr. Ramesh Kumar', 'it@campus.edu'),
            ('Academic Affairs', 'Prof. Sunita Sharma', 'academic@campus.edu'),
            ('Hostel & Facilities', 'Mr. Anil Verma', 'hostel@campus.edu'),
            ('Library', 'Ms. Priya Nair', 'library@campus.edu'),
            ('Sports & Recreation', 'Mr. Suresh Pillai', 'sports@campus.edu'),
            ('Canteen & Cafeteria', 'Mr. Ravi Das', 'canteen@campus.edu'),
            ('Security', 'Mr. Mohan Singh', 'security@campus.edu'),
            ('Administration', 'Dr. Kavya Menon', 'admin@campus.edu'),
            ('Student', 'General Student Body', 'students@campus.edu')
        ]
        cursor.executemany("INSERT INTO departments (dept_name, dept_head, contact_email) VALUES (?, ?, ?)", departments)

        # Seed Categories
        categories = [
            ('Network / WiFi Issue', 'Internet connectivity problems', 1),
            ('Software / System Issue', 'Lab computers, software access', 1),
            ('Exam Scheduling', 'Issues with exam timetable', 2),
            ('Faculty Concern', 'Academic-related faculty issues', 2),
            ('Hostel Maintenance', 'Room, plumbing, electricity in hostel', 3),
            ('Hostel Food Quality', 'Food served in hostel mess', 3),
            ('Library Book Availability', 'Missing or damaged books', 4),
            ('Library Silence Violation', 'Disturbance in library', 4),
            ('Sports Equipment Damage', 'Damaged or missing sports equipment', 5),
            ('Canteen Hygiene', 'Cleanliness and food safety in canteen', 6),
            ('Canteen Pricing', 'Overcharging in canteen', 6),
            ('Security Concern', 'Safety/security issue on campus', 7),
            ('Lost & Found', 'Lost items on campus', 7),
            ('Administrative Issue', 'Certificate, bonafide, fees related', 8),
            ('Other', 'Issues not covered above', 8)
        ]
        cursor.executemany("INSERT INTO categories (cat_name, description, dept_id) VALUES (?, ?, ?)", categories)

        # Seed Users
        pw_admin = bcrypt.hashpw(b"sudeepadmin@04", bcrypt.gensalt()).decode('utf-8')
        pw_student = bcrypt.hashpw(b"student@123", bcrypt.gensalt()).decode('utf-8')
        pw_staff = bcrypt.hashpw(b"staff@123", bcrypt.gensalt()).decode('utf-8')
        
        users = [
            ('Sudeep', 'sudeep_ad@gmail.com', pw_admin, 'admin', None, None, None),
            ('Amit Sharma', 'amit@student.edu', pw_student, 'student', 'CS2023001', 1, '9876543210'),
            ('Neha Patel', 'neha@student.edu', pw_student, 'student', 'CS2023002', 2, '9876543211'),
            ('Dr. Ramesh Kumar', 'ramesh@campus.edu', pw_staff, 'staff', None, 1, '9876543212'),
            ('Mr. Anil Verma', 'anil@campus.edu', pw_staff, 'staff', None, 3, '9876543213')
        ]
        cursor.executemany("INSERT INTO users (full_name, email, password_hash, role, roll_number, dept_id, phone) VALUES (?, ?, ?, ?, ?, ?, ?)", users)

        # Seed Complaints
        complaints = [
            ('WiFi not working in Lab 3', 'The Wi-Fi network in computer lab 3 is extremely slow and disconnects every few minutes.', 'resolved', 'high', 2, 1, 1, 4, 'Block A, Room 302', 0),
            ('Hostel room fan regulator broken', 'Ceiling fan in hostel block B, room 204 only runs at maximum speed because regulator is broken.', 'in_progress', 'medium', 3, 5, 3, 5, 'Hostel Block B, Room 204', 0),
            ('Library quiet zone noise', 'Some students are repeatedly discussing loudly in the quiet study zone on the second floor.', 'pending', 'low', 2, 8, 4, None, 'Central Library, 2nd Floor', 1),
            ('Unhygienic cafeteria seating', 'The tables in the canteen are not cleaned properly, and there are many flies around.', 'under_review', 'medium', 3, 10, 6, None, 'Main Canteen', 0),
            ('Broken gym dumbbell', 'The 15kg dumbbell in the sports room is broken and loose. It is dangerous to use.', 'resolved', 'medium', 2, 9, 5, 5, 'Campus Gym', 0),
            ('Exam schedule clash', 'Mid-term exams for Cryptography and Machine Learning are scheduled on the same session.', 'resolved', 'critical', 3, 3, 2, 4, 'Main Admin Block', 0),
            ('Lost ID Card in Library', 'I lost my student ID card in the library study section. If found, please return it.', 'resolved', 'low', 2, 13, 7, 4, 'Central Library', 0),
            ('Hostel washroom leak', 'There is a severe water leak in the washroom of hostel block A, first floor.', 'resolved', 'high', 3, 5, 3, 5, 'Hostel Block A', 0)
        ]
        cursor.executemany("""
            INSERT INTO complaints (title, description, status, priority, user_id, cat_id, dept_id, assigned_to, location, is_anonymous)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, complaints)

        # Seed Logs
        logs = [
            (1, 2, None, 'pending', 'Complaint submitted successfully.'),
            (1, 1, 'pending', 'in_progress', 'Assigned to staff officer Dr. Ramesh Kumar.'),
            (1, 4, 'in_progress', 'resolved', 'Replaced access point router in Lab 3. Network verified.'),
            (2, 3, None, 'pending', 'Complaint submitted successfully.'),
            (2, 1, 'pending', 'in_progress', 'Assigned to staff officer Mr. Anil Verma.'),
            (5, 5, 'in_progress', 'resolved', 'Gym equipment repaired and checked for safety.')
        ]
        cursor.executemany("INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks) VALUES (?, ?, ?, ?, ?)", logs)

        # Seed Comments
        comments_list = [
            (1, 2, 'Please fix this urgently, our final lab exams are next week.'),
            (1, 4, 'I am looking into this. I have ordered a new wireless router.'),
            (2, 5, 'I will be visiting the hostel block tomorrow morning to check the regulator.'),
            (4, 1, 'We are raising this issue with the cafeteria contractor.'),
            (5, 5, 'The dumbbell has been welded and is now safe for use.')
        ]
        cursor.executemany("INSERT INTO comments (complaint_id, user_id, comment_text) VALUES (?, ?, ?)", comments_list)

        # Seed Feedbacks
        feedbacks = [
            (1, 2, 5, 'WiFi is super fast now, thank you!'),
            (5, 2, 4, 'Dumbbell repaired. Thanks for the quick response.'),
            (6, 3, 5, 'Thank you for rescheduling! Big relief.'),
            (7, 2, 3, 'Found my card, but security desk was closed for hours.'),
            (8, 3, 5, 'Plumber fixed the leak within 2 hours. Great service!')
        ]
        cursor.executemany("INSERT INTO feedback (complaint_id, user_id, rating, remarks) VALUES (?, ?, ?, ?)", feedbacks)

        # Seed Notifications
        notifications = [
            (2, "✅ Your grievance #1 'WiFi not working in Lab 3' was submitted successfully.", 'submitted', 0),
            (4, "📋 New complaint #1 assigned to you: 'WiFi not working in Lab 3'", 'assigned', 0),
            (3, "⏳ Your grievance #2 'Hostel room fan regulator broken' is now In Progress.", 'status_update', 0),
            (1, "💬 Neha Patel submitted feedback on complaint #8 — Rating: ⭐⭐⭐⭐⭐ (5/5)", 'feedback', 0),
            (2, "✅ Your grievance #5 'Broken gym dumbbell' has been resolved.", 'status_update', 0)
        ]
        cursor.executemany("INSERT INTO notifications (user_id, message, type, is_read) VALUES (?, ?, ?, ?)", notifications)

        conn.commit()

    @classmethod
    def _initialize_mysql(cls, conn):
        cursor = conn.cursor()
        try:
            cursor.execute("SHOW TABLES")
            tables = [list(r.values())[0] if isinstance(r, dict) else r[0] for r in cursor.fetchall()]
            required = ['departments', 'users', 'categories', 'complaints', 'complaint_logs', 'comments', 'feedback', 'notifications']
            
            if not all(t in tables for t in required):
                raise ValueError("Missing tables")
                
            for t in required:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {t}")
                cnt = cursor.fetchone()
                row_cnt = cnt['cnt'] if isinstance(cnt, dict) else cnt[0]
                if row_cnt < 5:
                    raise ValueError(f"Table {t} has less than 5 rows")
            
            cursor.execute("SHOW COLUMNS FROM categories LIKE 'created_at'")
            if not cursor.fetchone():
                raise ValueError("Missing created_at attribute")
                
            return  # Already seeded
        except Exception:
            pass

        print("[INFO] Rebuilding MySQL database cleanly for DBMS Review-2...")
        
        # MySQL tables need to be created in order of dependencies.
        # Dropping existing tables if partially created
        for table in ['notifications', 'feedback', 'comments', 'complaint_logs', 'complaints', 'categories', 'users', 'departments']:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        cursor.execute("DROP VIEW IF EXISTS complaint_summary_view")

        # Create departments table
        cursor.execute("""
        CREATE TABLE departments (
            dept_id INT AUTO_INCREMENT PRIMARY KEY,
            dept_name VARCHAR(100) NOT NULL UNIQUE,
            dept_head VARCHAR(100),
            contact_email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create users table
        cursor.execute("""
        CREATE TABLE users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('student','staff','admin') DEFAULT 'student',
            roll_number VARCHAR(50),
            dept_id INT,
            phone VARCHAR(20),
            profile_pic VARCHAR(255),
            is_active TINYINT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create categories table
        cursor.execute("""
        CREATE TABLE categories (
            cat_id INT AUTO_INCREMENT PRIMARY KEY,
            cat_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            dept_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create complaints table
        cursor.execute("""
        CREATE TABLE complaints (
            complaint_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            status ENUM('pending','under_review','in_progress','resolved','rejected','closed') DEFAULT 'pending',
            priority ENUM('low','medium','high','critical') DEFAULT 'medium',
            user_id INT NOT NULL,
            cat_id INT,
            dept_id INT,
            assigned_to INT,
            attachment VARCHAR(255),
            location VARCHAR(200),
            is_anonymous TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (cat_id) REFERENCES categories(cat_id) ON DELETE SET NULL,
            FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE SET NULL,
            FOREIGN KEY (assigned_to) REFERENCES users(user_id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create complaint_logs table
        cursor.execute("""
        CREATE TABLE complaint_logs (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            complaint_id INT NOT NULL,
            changed_by INT NOT NULL,
            old_status VARCHAR(50),
            new_status VARCHAR(50),
            remarks TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
            FOREIGN KEY (changed_by) REFERENCES users(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create comments table
        cursor.execute("""
        CREATE TABLE comments (
            comment_id INT AUTO_INCREMENT PRIMARY KEY,
            complaint_id INT NOT NULL,
            user_id INT NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create feedback table
        cursor.execute("""
        CREATE TABLE feedback (
            feedback_id INT AUTO_INCREMENT PRIMARY KEY,
            complaint_id INT NOT NULL UNIQUE,
            user_id INT NOT NULL,
            rating INT CHECK(rating BETWEEN 1 AND 5),
            remarks TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create notifications table
        cursor.execute("""
        CREATE TABLE notifications (
            notif_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR(50) DEFAULT 'general',
            is_read TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Create View in MySQL
        cursor.execute("""
        CREATE VIEW complaint_summary_view AS
        SELECT 
            c.complaint_id,
            c.title,
            c.status,
            c.priority,
            u.full_name AS student_name,
            s.full_name AS assigned_staff,
            d.dept_name,
            cat.cat_name,
            c.created_at
        FROM complaints c
        LEFT JOIN users u ON c.user_id = u.user_id
        LEFT JOIN users s ON c.assigned_to = s.user_id
        LEFT JOIN departments d ON c.dept_id = d.dept_id
        LEFT JOIN categories cat ON c.cat_id = cat.cat_id;
        """)

        # Create Trigger in MySQL
        cursor.execute("DROP TRIGGER IF EXISTS before_complaint_update")
        cursor.execute("""
        CREATE TRIGGER before_complaint_update
        BEFORE UPDATE ON complaints
        FOR EACH ROW
        BEGIN
            IF NEW.status = 'resolved' AND OLD.status <> 'resolved' THEN
                SET NEW.resolved_at = NOW();
            ELSEIF NEW.status <> 'resolved' THEN
                SET NEW.resolved_at = NULL;
            END IF;
        END;
        """)

        # Seed Departments
        departments = [
            ('IT & Infrastructure', 'Dr. Ramesh Kumar', 'it@campus.edu'),
            ('Academic Affairs', 'Prof. Sunita Sharma', 'academic@campus.edu'),
            ('Hostel & Facilities', 'Mr. Anil Verma', 'hostel@campus.edu'),
            ('Library', 'Ms. Priya Nair', 'library@campus.edu'),
            ('Sports & Recreation', 'Mr. Suresh Pillai', 'sports@campus.edu'),
            ('Canteen & Cafeteria', 'Mr. Ravi Das', 'canteen@campus.edu'),
            ('Security', 'Mr. Mohan Singh', 'security@campus.edu'),
            ('Administration', 'Dr. Kavya Menon', 'admin@campus.edu'),
            ('Student', 'General Student Body', 'students@campus.edu')
        ]
        cursor.executemany("INSERT INTO departments (dept_name, dept_head, contact_email) VALUES (%s, %s, %s)", departments)

        # Seed Categories
        categories = [
            ('Network / WiFi Issue', 'Internet connectivity problems', 1),
            ('Software / System Issue', 'Lab computers, software access', 1),
            ('Exam Scheduling', 'Issues with exam timetable', 2),
            ('Faculty Concern', 'Academic-related faculty issues', 2),
            ('Hostel Maintenance', 'Room, plumbing, electricity in hostel', 3),
            ('Hostel Food Quality', 'Food served in hostel mess', 3),
            ('Library Book Availability', 'Missing or damaged books', 4),
            ('Library Silence Violation', 'Disturbance in library', 4),
            ('Sports Equipment Damage', 'Damaged or missing sports equipment', 5),
            ('Canteen Hygiene', 'Cleanliness and food safety in canteen', 6),
            ('Canteen Pricing', 'Overcharging in canteen', 6),
            ('Security Concern', 'Safety/security issue on campus', 7),
            ('Lost & Found', 'Lost items on campus', 7),
            ('Administrative Issue', 'Certificate, bonafide, fees related', 8),
            ('Other', 'Issues not covered above', 8)
        ]
        cursor.executemany("INSERT INTO categories (cat_name, description, dept_id) VALUES (%s, %s, %s)", categories)

        # Seed Users
        pw_admin = bcrypt.hashpw(b"sudeepadmin@04", bcrypt.gensalt()).decode('utf-8')
        pw_student = bcrypt.hashpw(b"student@123", bcrypt.gensalt()).decode('utf-8')
        pw_staff = bcrypt.hashpw(b"staff@123", bcrypt.gensalt()).decode('utf-8')
        
        users = [
            ('Sudeep', 'sudeep_ad@gmail.com', pw_admin, 'admin', None, None, None),
            ('Amit Sharma', 'amit@student.edu', pw_student, 'student', 'CS2023001', 1, '9876543210'),
            ('Neha Patel', 'neha@student.edu', pw_student, 'student', 'CS2023002', 2, '9876543211'),
            ('Dr. Ramesh Kumar', 'ramesh@campus.edu', pw_staff, 'staff', None, 1, '9876543212'),
            ('Mr. Anil Verma', 'anil@campus.edu', pw_staff, 'staff', None, 3, '9876543213')
        ]
        cursor.executemany("INSERT INTO users (full_name, email, password_hash, role, roll_number, dept_id, phone) VALUES (%s, %s, %s, %s, %s, %s, %s)", users)

        # Seed Complaints
        complaints = [
            ('WiFi not working in Lab 3', 'The Wi-Fi network in computer lab 3 is extremely slow and disconnects every few minutes.', 'resolved', 'high', 2, 1, 1, 4, 'Block A, Room 302', 0),
            ('Hostel room fan regulator broken', 'Ceiling fan in hostel block B, room 204 only runs at maximum speed because regulator is broken.', 'in_progress', 'medium', 3, 5, 3, 5, 'Hostel Block B, Room 204', 0),
            ('Library quiet zone noise', 'Some students are repeatedly discussing loudly in the quiet study zone on the second floor.', 'pending', 'low', 2, 8, 4, None, 'Central Library, 2nd Floor', 1),
            ('Unhygienic cafeteria seating', 'The tables in the canteen are not cleaned properly, and there are many flies around.', 'under_review', 'medium', 3, 10, 6, None, 'Main Canteen', 0),
            ('Broken gym dumbbell', 'The 15kg dumbbell in the sports room is broken and loose. It is dangerous to use.', 'resolved', 'medium', 2, 9, 5, 5, 'Campus Gym', 0),
            ('Exam schedule clash', 'Mid-term exams for Cryptography and Machine Learning are scheduled on the same session.', 'resolved', 'critical', 3, 3, 2, 4, 'Main Admin Block', 0),
            ('Lost ID Card in Library', 'I lost my student ID card in the library study section. If found, please return it.', 'resolved', 'low', 2, 13, 7, 4, 'Central Library', 0),
            ('Hostel washroom leak', 'There is a severe water leak in the washroom of hostel block A, first floor.', 'resolved', 'high', 3, 5, 3, 5, 'Hostel Block A', 0)
        ]
        cursor.executemany("""
            INSERT INTO complaints (title, description, status, priority, user_id, cat_id, dept_id, assigned_to, location, is_anonymous)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, complaints)

        # Seed Logs
        logs = [
            (1, 2, None, 'pending', 'Complaint submitted successfully.'),
            (1, 1, 'pending', 'in_progress', 'Assigned to staff officer Dr. Ramesh Kumar.'),
            (1, 4, 'in_progress', 'resolved', 'Replaced access point router in Lab 3. Network verified.'),
            (2, 3, None, 'pending', 'Complaint submitted successfully.'),
            (2, 1, 'pending', 'in_progress', 'Assigned to staff officer Mr. Anil Verma.'),
            (5, 5, 'in_progress', 'resolved', 'Gym equipment repaired and checked for safety.')
        ]
        cursor.executemany("INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks) VALUES (%s, %s, %s, %s, %s)", logs)

        # Seed Comments
        comments_list = [
            (1, 2, 'Please fix this urgently, our final lab exams are next week.'),
            (1, 4, 'I am looking into this. I have ordered a new wireless router.'),
            (2, 5, 'I will be visiting the hostel block tomorrow morning to check the regulator.'),
            (4, 1, 'We are raising this issue with the cafeteria contractor.'),
            (5, 5, 'The dumbbell has been welded and is now safe for use.')
        ]
        cursor.executemany("INSERT INTO comments (complaint_id, user_id, comment_text) VALUES (%s, %s, %s)", comments_list)

        # Seed Feedbacks
        feedbacks = [
            (1, 2, 5, 'WiFi is super fast now, thank you!'),
            (5, 2, 4, 'Dumbbell repaired. Thanks for the quick response.'),
            (6, 3, 5, 'Thank you for rescheduling! Big relief.'),
            (7, 2, 3, 'Found my card, but security desk was closed for hours.'),
            (8, 3, 5, 'Plumber fixed the leak within 2 hours. Great service!')
        ]
        cursor.executemany("INSERT INTO feedback (complaint_id, user_id, rating, remarks) VALUES (%s, %s, %s, %s)", feedbacks)

        # Seed Notifications
        notifications = [
            (2, "✅ Your grievance #1 'WiFi not working in Lab 3' was submitted successfully.", 'submitted', 0),
            (4, "📋 New complaint #1 assigned to you: 'WiFi not working in Lab 3'", 'assigned', 0),
            (3, "⏳ Your grievance #2 'Hostel room fan regulator broken' is now In Progress.", 'status_update', 0),
            (1, "💬 Neha Patel submitted feedback on complaint #8 — Rating: ⭐⭐⭐⭐⭐ (5/5)", 'feedback', 0),
            (2, "✅ Your grievance #5 'Broken gym dumbbell' has been resolved.", 'status_update', 0)
        ]
        cursor.executemany("INSERT INTO notifications (user_id, message, type, is_read) VALUES (%s, %s, %s, %s)", notifications)

    @classmethod
    def query(cls, sql, params=(), one=False):
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            # Simple conversion from MySQL %s to SQLite ? placeholder if fallback is active
            if cls.is_sqlite:
                sql = sql.replace('%s', '?')
            
            cursor.execute(sql, params)
            if sql.strip().upper().startswith('SELECT') or 'RETURNING' in sql.upper():
                rows = cursor.fetchall()
                if cls.is_sqlite:
                    # Convert SQLite Rows to ordinary dicts
                    rows = [dict(row) for row in rows]
                else:
                    # PyMySQL DictCursor already returns dicts
                    pass
                return (rows[0] if rows else None) if one else rows
            else:
                if not cls.is_sqlite:
                    conn.commit()
                else:
                    conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[ERROR] Database query failed: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ══════════════════════════════════════════════════════════════
#  ROUTINGS & FLASK ENDPOINTS
# ══════════════════════════════════════════════════════════════

# 1. Landing Page
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

# 2. Student Login (GET & POST)
@app.route('/login', methods=['GET', 'POST'])
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Accept JSON (AJAX) or Form encoded
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        user = DatabaseHelper.query("SELECT * FROM users WHERE email = %s", (email,), one=True)
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['email'] = user['email']
            session['roll_number'] = user.get('roll_number')
            session['phone'] = user.get('phone')
            
            if user['role'] == 'admin':
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
                return redirect(url_for('admin_dashboard'))
                
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid email or password.'})
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')

# 3. Student Registration
@app.route('/register', methods=['GET', 'POST'])
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        full_name = data.get('fullName')
        email = data.get('email')
        roll_number = data.get('rollNumber')
        phone = data.get('phone')
        dept_id = data.get('department')
        password = data.get('password')
        
        # Check if email already registered
        existing = DatabaseHelper.query("SELECT * FROM users WHERE email = %s", (email,), one=True)
        if existing:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email address already registered.'})
            flash('Email address already registered.', 'error')
            return render_template('register.html')
            
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            DatabaseHelper.query(
                "INSERT INTO users (full_name, email, password_hash, role, roll_number, dept_id, phone) VALUES (%s, %s, %s, 'student', %s, %s, %s)",
                (full_name, email, hashed_pw, roll_number, dept_id, phone)
            )
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('login')})
            return redirect(url_for('login'))
        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'})
            flash(f'Registration failed: {str(e)}', 'error')
            
    return render_template('register.html')

# 4. Admin Login (GET & POST)
@app.route('/admin/login', methods=['GET', 'POST'])
@app.route('/admin_login.html', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        user = DatabaseHelper.query("SELECT * FROM users WHERE email = %s AND role = 'admin'", (email,), one=True)
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role'] = 'admin'
            session['email'] = user['email']
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
            return redirect(url_for('admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Restricted Admin Access: Invalid Credentials.'})
            flash('Invalid Admin Credentials.', 'error')
            
    return render_template('admin_login.html')

# 5. User Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 6. Student Dashboard
@app.route('/dashboard')
@app.route('/dashboard.html')
def dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    u_id = session['user_id']
    
    # Retrieve dynamic statistics widgets
    total = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s", (u_id,), one=True)['count']
    resolved = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s AND status = 'resolved'", (u_id,), one=True)['count']
    pending = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s AND status = 'pending'", (u_id,), one=True)['count']
    in_progress = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s AND status = 'in_progress'", (u_id,), one=True)['count']
    
    # Get last 5 complaints
    complaints = DatabaseHelper.query("""
        SELECT c.*, cat.cat_name, d.dept_name 
        FROM complaints c
        LEFT JOIN categories cat ON c.cat_id = cat.cat_id
        LEFT JOIN departments d ON c.dept_id = d.dept_id
        WHERE c.user_id = %s
        ORDER BY c.complaint_id DESC LIMIT 5
    """, (u_id,))
    
    # Get unread notifications
    notifications = DatabaseHelper.query("SELECT * FROM notifications WHERE user_id = %s ORDER BY notif_id DESC LIMIT 3", (u_id,))
    
    # Check total unread notifications count
    unread_notif_count = DatabaseHelper.query("SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = 0", (u_id,), one=True)['count']
    
    # Render Dashboard passing actual SQL values
    return render_template('dashboard.html', 
                           total=total, 
                           resolved=resolved, 
                           pending=pending, 
                           in_progress=in_progress, 
                           complaints=complaints, 
                           notifications=notifications,
                           unread_count=unread_notif_count)

# 7. Submit Complaint
@app.route('/complaint', methods=['GET', 'POST'])
@app.route('/complaint.html', methods=['GET', 'POST'])
def submit_complaint():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        cat_id = request.form.get('category')
        priority = request.form.get('priority') or 'medium'
        location = request.form.get('location')
        description = request.form.get('description')
        is_anonymous = 1 if request.form.get('anonymous') == '1' else 0
        u_id = session['user_id']
        
        # Attachment Handling
        filename = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{u_id}_{int(datetime.datetime.now().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Auto routing triggers matching categories
        cat = DatabaseHelper.query("SELECT dept_id FROM categories WHERE cat_id = %s", (cat_id,), one=True)
        dept_id = cat['dept_id'] if cat else None
        
        try:
            c_id = DatabaseHelper.query("""
                INSERT INTO complaints (title, description, status, priority, user_id, cat_id, dept_id, location, is_anonymous, attachment)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s, %s, %s)
            """, (title, description, priority, u_id, cat_id, dept_id, location, is_anonymous, filename))
            
            # Log insertion
            DatabaseHelper.query("INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks) VALUES (%s, %s, NULL, 'pending', 'Complaint submitted successfully.')", (c_id, u_id))
            
            # Notify student: complaint submitted
            DatabaseHelper.query("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, %s)",
                (u_id, f"✅ Your grievance #{c_id} '{title}' was submitted successfully and is pending review.", 'submitted'))
            
            # Notify admin: new complaint received
            admin = DatabaseHelper.query("SELECT user_id FROM users WHERE role = 'admin' LIMIT 1", one=True)
            if admin:
                student = DatabaseHelper.query("SELECT full_name FROM users WHERE user_id = %s", (u_id,), one=True)
                student_name = student['full_name'] if (student and not is_anonymous) else 'Anonymous Student'
                DatabaseHelper.query("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, %s)",
                    (admin['user_id'], f"📋 New complaint #{c_id} filed by {student_name}: '{title}' [{priority.upper()} priority]", 'new_complaint'))
            
            return jsonify({'success': True, 'message': 'Complaint successfully submitted.'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

    return render_template('complaint.html')

# 8. Track Complaints & Timeline modal
@app.route('/tracking')
@app.route('/tracking.html')
def tracking():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    u_id = session['user_id']
    role = session['role']
    
    # Query all complaints for student or show all for admin view
    if role == 'admin':
        complaints = DatabaseHelper.query("""
            SELECT c.*, cat.cat_name, d.dept_name, u.full_name as student_name, s.full_name as assigned_name 
            FROM complaints c
            LEFT JOIN categories cat ON c.cat_id = cat.cat_id
            LEFT JOIN departments d ON c.dept_id = d.dept_id
            LEFT JOIN users u ON c.user_id = u.user_id
            LEFT JOIN users s ON c.assigned_to = s.user_id
            ORDER BY c.complaint_id DESC
        """)
    else:
        complaints = DatabaseHelper.query("""
            SELECT c.*, cat.cat_name, d.dept_name, s.full_name as assigned_name 
            FROM complaints c
            LEFT JOIN categories cat ON c.cat_id = cat.cat_id
            LEFT JOIN departments d ON c.dept_id = d.dept_id
            LEFT JOIN users s ON c.assigned_to = s.user_id
            WHERE c.user_id = %s
            ORDER BY c.complaint_id DESC
        """, (u_id,))
        
    # Serialize complaints directly as JSON for client-side open detail modals support
    import json
    serialized_complaints = []
    for c in complaints:
        # Format timestamps
        date_str = c['created_at'] if isinstance(c['created_at'], str) else c['created_at'].strftime('%Y-%m-%d')
        serialized_complaints.append({
            'id': c['complaint_id'],
            'title': c['title'],
            'status': c['status'],
            'priority': c['priority'],
            'category': c['cat_name'] or 'General / Other',
            'dept': c['dept_name'] or 'Administration',
            'student': c.get('student_name', 'My Grievance') if not c['is_anonymous'] else 'Anonymous Student',
            'date': date_str,
            'description': c['description'],
            'assigned': c.get('assigned_name') or 'Unassigned'
        })
    
    complaints_json = json.dumps(serialized_complaints)
    
    return render_template('tracking.html', complaints=complaints, complaints_json=complaints_json)

# 9. Admin Dashboard
@app.route('/admin_dashboard')
@app.route('/admin_dashboard.html')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    # Calculate statistics values
    total = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints", one=True)['count']
    resolved = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE status = 'resolved'", one=True)['count']
    pending = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE status = 'pending'", one=True)['count']
    in_progress = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE status = 'in_progress'", one=True)['count']
    
    # Query complete list of complaints
    complaints = DatabaseHelper.query("""
        SELECT c.*, cat.cat_name, d.dept_name, u.full_name as student_name, u.email as student_email, s.full_name as assigned_name 
        FROM complaints c
        LEFT JOIN categories cat ON c.cat_id = cat.cat_id
        LEFT JOIN departments d ON c.dept_id = d.dept_id
        LEFT JOIN users u ON c.user_id = u.user_id
        LEFT JOIN users s ON c.assigned_to = s.user_id
        ORDER BY c.complaint_id DESC
    """)
    
    # Serialize complaints directly as JSON for client-side details modal support
    import json
    serialized_complaints = []
    for c in complaints:
        date_str = c['created_at'] if isinstance(c['created_at'], str) else c['created_at'].strftime('%Y-%m-%d')
        serialized_complaints.append({
            'id': c['complaint_id'],
            'title': c['title'],
            'status': c['status'],
            'priority': c['priority'],
            'category': c['cat_name'] or 'General / Other',
            'dept': c['dept_name'] or 'Administration',
            'student': c['student_name'] if not c['is_anonymous'] else 'Anonymous Student',
            'date': date_str,
            'description': c['description'],
            'assigned': c['assigned_name'] or 'Unassigned'
        })
    complaints_json = json.dumps(serialized_complaints)
    
    return render_template('admin_dashboard.html', 
                           total=total, 
                           resolved=resolved, 
                           pending=pending, 
                           in_progress=in_progress, 
                           complaints=complaints, 
                           complaints_json=complaints_json)

# 10. Update status API (Form POST / AJAX)
@app.route('/api/update-status', methods=['POST'])
def api_update_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Access denied: Please login.'})
        
    data = request.get_json() if request.is_json else request.form
    c_id = data.get('complaint_id')
    status = data.get('status')
    remark = data.get('remark')
    user_id = session['user_id']
    
    try:
        complaint = DatabaseHelper.query("SELECT * FROM complaints WHERE complaint_id = %s", (c_id,), one=True)
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found.'})
            
        old_status = complaint['status']
        resolved_at = datetime.datetime.now() if status == 'resolved' else None
        
        # Update record
        DatabaseHelper.query("""
            UPDATE complaints 
            SET status = %s, resolved_at = %s, updated_at = CURRENT_TIMESTAMP
            WHERE complaint_id = %s
        """, (status, resolved_at, c_id))
        
        # Insert log
        DatabaseHelper.query("""
            INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (c_id, user_id, old_status, status, remark))
        
        # Status emoji map
        status_emoji = {'pending': '⏳', 'under_review': '🔍', 'in_progress': '⚙️', 'resolved': '✅', 'rejected': '❌', 'closed': '🔒'}
        emoji = status_emoji.get(status, '🔔')
        status_label = status.replace('_', ' ').title()
        remark_text = f" — Remark: {remark}" if remark else ""
        # Notify student
        DatabaseHelper.query("""
            INSERT INTO notifications (user_id, message, type)
            VALUES (%s, %s, %s)
        """, (complaint['user_id'],
               f"{emoji} Grievance #{c_id} status updated to: {status_label}.{remark_text}",
               'status_update'))
        
        return jsonify({'success': True, 'message': 'Status successfully updated.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 11. Assign Staff API
@app.route('/api/assign-staff', methods=['POST'])
def api_assign_staff():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Access denied: Administrators only.'})
        
    data = request.get_json() if request.is_json else request.form
    c_id = data.get('complaint_id')
    staff_name = data.get('staff')
    user_id = session['user_id']
    
    try:
        # Find staff user ID matching name
        staff = DatabaseHelper.query("SELECT user_id FROM users WHERE full_name = %s AND role = 'staff'", (staff_name,), one=True)
        staff_id = staff['user_id'] if staff else None
        
        # If staff not registered yet, seed them dynamically to guarantee success
        if not staff_id:
            pw_staff = bcrypt.hashpw(b"Staff@123", bcrypt.gensalt()).decode('utf-8')
            staff_email = f"{staff_name.lower().replace(' ', '')}@campus.edu"
            staff_id = DatabaseHelper.query("""
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, 'staff')
            """, (staff_name, staff_email, pw_staff))

        complaint = DatabaseHelper.query("SELECT user_id FROM complaints WHERE complaint_id = %s", (c_id,), one=True)
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found.'})

        # Update assignment
        DatabaseHelper.query("""
            UPDATE complaints SET assigned_to = %s, status = 'in_progress', updated_at = CURRENT_TIMESTAMP WHERE complaint_id = %s
        """, (staff_id, c_id))
        
        # Log assignment
        DatabaseHelper.query("""
            INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks)
            VALUES (%s, %s, 'pending', 'in_progress', %s)
        """, (c_id, user_id, f"Assigned to staff officer {staff_name}."))
        
        # Notify student
        DatabaseHelper.query("""
            INSERT INTO notifications (user_id, message, type)
            VALUES (%s, %s, %s)
        """, (complaint['user_id'],
               f"👷 Grievance #{c_id} has been assigned to officer: {staff_name} and is now In Progress.",
               'assigned'))
        
        return jsonify({'success': True, 'message': 'Staff officer assigned successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 12. Feedback Submission
@app.route('/api/submit-feedback', methods=['POST'])
def api_submit_feedback():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Access denied: Please login.'})
        
    data = request.get_json() if request.is_json else request.form
    c_id = data.get('complaint_id')
    rating = data.get('rating')
    remarks = data.get('remarks')
    user_id = session['user_id']
    
    try:
        DatabaseHelper.query("""
            INSERT INTO feedback (complaint_id, user_id, rating, remarks)
            VALUES (%s, %s, %s, %s)
        """, (c_id, user_id, rating, remarks))
        
        # Notify admin about feedback received
        admin = DatabaseHelper.query("SELECT user_id FROM users WHERE role = 'admin' LIMIT 1", one=True)
        if admin:
            star_str = '⭐' * int(rating) if rating else ''
            student = DatabaseHelper.query("SELECT full_name FROM users WHERE user_id = %s", (user_id,), one=True)
            student_name = student['full_name'] if student else 'A student'
            remark_text = f": '{remarks}'" if remarks else ""
            DatabaseHelper.query("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, %s)",
                (admin['user_id'],
                 f"💬 {student_name} submitted feedback on complaint #{c_id} — Rating: {star_str} ({rating}/5){remark_text}",
                 'feedback'))
        
        # Also notify student their feedback was received
        DatabaseHelper.query("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, %s)",
            (user_id,
             f"💬 Your feedback for complaint #{c_id} has been recorded. Thank you!",
             'feedback'))
        
        return jsonify({'success': True, 'message': 'Thank you for your feedback!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 13. Mark notifications read API
@app.route('/api/mark-notifications-read', methods=['POST'])
def api_mark_notifications_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Access denied: Please login.'})
        
    u_id = session['user_id']
    try:
        DatabaseHelper.query("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (u_id,))
        return jsonify({'success': True, 'message': 'Notifications marked read.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 13b. Delete Complaint API (Admin only)
@app.route('/api/delete-complaint', methods=['POST'])
def api_delete_complaint():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Access denied: Admin only.'})
    
    data = request.get_json() if request.is_json else request.form
    c_id = data.get('complaint_id')
    
    if not c_id:
        return jsonify({'success': False, 'message': 'No complaint ID provided.'})
    
    try:
        # Check complaint exists
        complaint = DatabaseHelper.query("SELECT complaint_id, title, user_id FROM complaints WHERE complaint_id = %s", (c_id,), one=True)
        if not complaint:
            return jsonify({'success': False, 'message': f'Complaint #{c_id} not found.'})
        
        # Delete all related records first (foreign key dependencies)
        DatabaseHelper.query("DELETE FROM feedback WHERE complaint_id = %s", (c_id,))
        DatabaseHelper.query("DELETE FROM comments WHERE complaint_id = %s", (c_id,))
        DatabaseHelper.query("DELETE FROM complaint_logs WHERE complaint_id = %s", (c_id,))
        
        # Delete the complaint itself
        DatabaseHelper.query("DELETE FROM complaints WHERE complaint_id = %s", (c_id,))
        
        # Notify the student whose complaint was deleted
        DatabaseHelper.query("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, %s)",
            (complaint['user_id'],
             f"🗑️ Your complaint '{complaint['title']}' has been removed by the administrator.",
             'status_update'))
        
        return jsonify({'success': True, 'message': f'Complaint #{c_id} deleted permanently.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting complaint: {str(e)}'})

# 13c. Live Dashboard Stats API
@app.route('/api/dashboard-stats', methods=['GET'])
def api_dashboard_stats():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Access denied: Please login.'})
    try:
        user_id = session['user_id']
        role = session['role']
        if role == 'admin':
            total = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints", one=True)['count']
            resolved = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE status = 'resolved'", one=True)['count']
            pending = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE status = 'pending'", one=True)['count']
            in_progress = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE status = 'in_progress'", one=True)['count']
        else:
            total = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s", (user_id,), one=True)['count']
            resolved = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s AND status = 'resolved'", (user_id,), one=True)['count']
            pending = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s AND status = 'pending'", (user_id,), one=True)['count']
            in_progress = DatabaseHelper.query("SELECT COUNT(*) as count FROM complaints WHERE user_id = %s AND status = 'in_progress'", (user_id,), one=True)['count']
            
        return jsonify({
            'success': True,
            'total': total,
            'resolved': resolved,
            'pending': pending,
            'in_progress': in_progress
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 14. Notifications Page
@app.route('/notifications')
@app.route('/notifications.html')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    u_id = session['user_id']
    
    # Query all user notifications with accurate timestamps
    notifs = DatabaseHelper.query(
        "SELECT notif_id, user_id, message, type, is_read, created_at FROM notifications WHERE user_id = %s ORDER BY notif_id DESC",
        (u_id,)
    )
    
    # Serialize timestamps as ISO strings for JS relative-time
    import json, datetime
    notif_list = []
    for n in (notifs or []):
        ts = n['created_at']
        if isinstance(ts, str):
            # SQLite returns strings like '2026-05-24 15:30:00'
            ts_iso = ts.replace(' ', 'T')
        elif hasattr(ts, 'isoformat'):
            ts_iso = ts.isoformat()
        else:
            ts_iso = str(ts)
        notif_list.append({
            'notif_id': n['notif_id'],
            'message': n['message'],
            'type': n.get('type') or 'general',
            'is_read': n['is_read'],
            'created_at_iso': ts_iso,
            'created_at_str': ts_iso[:16].replace('T', ' ')
        })
    
    notifications_json = json.dumps(notif_list)
    unread_count = sum(1 for n in notif_list if n['is_read'] == 0)
    
    # Mark all as read when page is opened
    DatabaseHelper.query("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (u_id,))
    
    return render_template('notifications.html',
                           notifications=notif_list,
                           notifications_json=notifications_json,
                           unread_count=unread_count)

# 15. User Profile Page (GET & POST)
@app.route('/profile', methods=['GET', 'POST'])
@app.route('/profile.html', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    u_id = session['user_id']
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        phone = data.get('phone')
        dept_id = data.get('department')
        
        try:
            # Update user profile
            DatabaseHelper.query("UPDATE users SET phone = %s, dept_id = %s WHERE user_id = %s", (phone, dept_id, u_id))
            session['phone'] = phone
            return jsonify({'success': True, 'message': 'Profile details updated.'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Update failed: {str(e)}'})
            
    # GET details
    user = DatabaseHelper.query("""
        SELECT u.*, d.dept_name 
        FROM users u
        LEFT JOIN departments d ON u.dept_id = d.dept_id
        WHERE u.user_id = %s
    """, (u_id,), one=True)
    
    return render_template('profile.html', user=user)

# 16. Change Password API
@app.route('/api/change-password', methods=['POST'])
def api_change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Access denied: Please login.'})
        
    u_id = session['user_id']
    data = request.get_json() if request.is_json else request.form
    curr_pw = data.get('current_password')
    new_pw = data.get('new_password')
    
    try:
        user = DatabaseHelper.query("SELECT password_hash FROM users WHERE user_id = %s", (u_id,), one=True)
        if not user or not bcrypt.checkpw(curr_pw.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'success': False, 'message': 'Incorrect current password.'})
            
        hashed_pw = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        DatabaseHelper.query("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed_pw, u_id))
        return jsonify({'success': True, 'message': 'Password updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 17. About page
@app.route('/about')
@app.route('/about.html')
def about():
    return render_template('about.html')

# 19. Terms of Service page
@app.route('/terms')
@app.route('/terms.html')
def terms():
    return render_template('terms.html')

# 20. Privacy Policy page
@app.route('/privacy')
@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

# 18. API route for timeline tracking logs modal
@app.route('/api/complaint-logs/<int:c_id>')
def api_complaint_logs(c_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized.'})
    try:
        logs = DatabaseHelper.query("""
            SELECT l.*, u.full_name as changer_name, u.role as changer_role
            FROM complaint_logs l
            LEFT JOIN users u ON l.changed_by = u.user_id
            WHERE l.complaint_id = %s
            ORDER BY l.log_id ASC
        """, (c_id,))
        
        # Serialize list
        serialized_logs = []
        for l in logs:
            time_str = l['changed_at'] if isinstance(l['changed_at'], str) else l['changed_at'].strftime('%Y-%m-%d %H:%M')
            serialized_logs.append({
                'id': l['log_id'],
                'old_status': l['old_status'],
                'new_status': l['new_status'],
                'remarks': l['remarks'],
                'changed_by': l['changer_name'],
                'role': l['changer_role'],
                'time': time_str
            })
        return jsonify({'success': True, 'logs': serialized_logs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Start server
if __name__ == '__main__':
    print("[INFO] Starting Campus Complaint Management server...")
    app.run(debug=True, host='127.0.0.1', port=5000)

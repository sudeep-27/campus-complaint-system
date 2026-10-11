-- ============================================================
--  Campus Complaint Management System - Database Schema
--  Run this file in MySQL to set up the database
-- ============================================================

CREATE DATABASE IF NOT EXISTS campus_complaints;
USE campus_complaints;

-- ─────────────────────────────────────────────
-- TABLE: departments
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS departments (
    dept_id       INT AUTO_INCREMENT PRIMARY KEY,
    dept_name     VARCHAR(100) NOT NULL UNIQUE,
    dept_head     VARCHAR(100),
    contact_email VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- TABLE: users (students + staff + admin)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('student','staff','admin') DEFAULT 'student',
    roll_number   VARCHAR(30),
    dept_id       INT,
    phone         VARCHAR(15),
    profile_pic   VARCHAR(255),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────
-- TABLE: categories
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
    cat_id      INT AUTO_INCREMENT PRIMARY KEY,
    cat_name    VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    dept_id     INT,   -- which department handles this category
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────
-- TABLE: complaints
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id   INT AUTO_INCREMENT PRIMARY KEY,
    title          VARCHAR(200) NOT NULL,
    description    TEXT NOT NULL,
    status         ENUM('pending','under_review','in_progress','resolved','rejected','closed')
                   DEFAULT 'pending',
    priority       ENUM('low','medium','high','critical') DEFAULT 'medium',
    user_id        INT NOT NULL,
    cat_id         INT,
    dept_id        INT,
    assigned_to    INT,               -- staff user_id
    attachment     VARCHAR(255),
    location       VARCHAR(200),
    is_anonymous   BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at    TIMESTAMP NULL,
    FOREIGN KEY (user_id)     REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (cat_id)      REFERENCES categories(cat_id) ON DELETE SET NULL,
    FOREIGN KEY (dept_id)     REFERENCES departments(dept_id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users(user_id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────
-- TABLE: complaint_logs (status history)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS complaint_logs (
    log_id       INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    changed_by   INT NOT NULL,
    old_status   VARCHAR(50),
    new_status   VARCHAR(50),
    remarks      TEXT,
    changed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by)   REFERENCES users(user_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- TABLE: comments
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS comments (
    comment_id   INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    user_id      INT NOT NULL,
    comment_text TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)      REFERENCES users(user_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- TABLE: feedback (after complaint is resolved)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id  INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL UNIQUE,
    user_id      INT NOT NULL,
    rating       TINYINT CHECK (rating BETWEEN 1 AND 5),
    remarks      TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)      REFERENCES users(user_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- TABLE: notifications
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    notif_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    message      TEXT NOT NULL,
    is_read      BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- VIEWS
-- ─────────────────────────────────────────────

-- View: complaint details with user and department info
CREATE OR REPLACE VIEW v_complaint_details AS
SELECT
    c.complaint_id,
    c.title,
    c.description,
    c.status,
    c.priority,
    c.location,
    c.is_anonymous,
    c.created_at,
    c.updated_at,
    c.resolved_at,
    IF(c.is_anonymous, 'Anonymous', u.full_name) AS student_name,
    IF(c.is_anonymous, NULL, u.email)            AS student_email,
    IF(c.is_anonymous, NULL, u.roll_number)      AS roll_number,
    cat.cat_name                                  AS category,
    d.dept_name                                   AS department,
    s.full_name                                   AS assigned_staff
FROM complaints c
JOIN users u        ON c.user_id     = u.user_id
LEFT JOIN categories cat ON c.cat_id  = cat.cat_id
LEFT JOIN departments d  ON c.dept_id = d.dept_id
LEFT JOIN users s        ON c.assigned_to = s.user_id;

-- View: department complaint stats
CREATE OR REPLACE VIEW v_dept_stats AS
SELECT
    d.dept_name,
    COUNT(c.complaint_id)                                        AS total,
    SUM(c.status = 'pending')                                    AS pending,
    SUM(c.status = 'in_progress')                                AS in_progress,
    SUM(c.status = 'resolved')                                   AS resolved,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, c.created_at, c.resolved_at)),1) AS avg_resolution_hrs
FROM departments d
LEFT JOIN complaints c ON d.dept_id = c.dept_id
GROUP BY d.dept_id, d.dept_name;

-- ─────────────────────────────────────────────
-- STORED PROCEDURES
-- ─────────────────────────────────────────────

DELIMITER $$

-- Procedure: update complaint status + log it + notify student
CREATE PROCEDURE sp_update_complaint_status(
    IN p_complaint_id INT,
    IN p_changed_by   INT,
    IN p_new_status   VARCHAR(50),
    IN p_remarks      TEXT
)
BEGIN
    DECLARE v_old_status VARCHAR(50);
    DECLARE v_user_id    INT;

    SELECT status, user_id INTO v_old_status, v_user_id
    FROM complaints WHERE complaint_id = p_complaint_id;

    UPDATE complaints
    SET status      = p_new_status,
        resolved_at = IF(p_new_status = 'resolved', NOW(), resolved_at)
    WHERE complaint_id = p_complaint_id;

    INSERT INTO complaint_logs(complaint_id, changed_by, old_status, new_status, remarks)
    VALUES (p_complaint_id, p_changed_by, v_old_status, p_new_status, p_remarks);

    INSERT INTO notifications(user_id, message)
    VALUES (v_user_id,
        CONCAT('Your complaint #', p_complaint_id, ' status changed to: ', p_new_status,
               IF(p_remarks IS NOT NULL AND p_remarks != '', CONCAT('. Remark: ', p_remarks), '')));
END$$

-- Procedure: get complaint summary for admin dashboard
CREATE PROCEDURE sp_dashboard_summary()
BEGIN
    SELECT
        COUNT(*) AS total_complaints,
        SUM(status = 'pending')     AS pending,
        SUM(status = 'in_progress') AS in_progress,
        SUM(status = 'resolved')    AS resolved,
        SUM(status = 'rejected')    AS rejected,
        SUM(priority = 'critical')  AS critical_count,
        SUM(priority = 'high')      AS high_count
    FROM complaints;
END$$

DELIMITER ;

-- ─────────────────────────────────────────────
-- TRIGGERS
-- ─────────────────────────────────────────────

DELIMITER $$

-- Trigger: auto-assign department when category is chosen
CREATE TRIGGER trg_auto_assign_dept
BEFORE INSERT ON complaints
FOR EACH ROW
BEGIN
    IF NEW.dept_id IS NULL AND NEW.cat_id IS NOT NULL THEN
        SET NEW.dept_id = (SELECT dept_id FROM categories WHERE cat_id = NEW.cat_id);
    END IF;
END$$

DELIMITER ;

-- ─────────────────────────────────────────────
-- SEED DATA
-- ─────────────────────────────────────────────

INSERT IGNORE INTO departments (dept_name, dept_head, contact_email) VALUES
('IT & Infrastructure',  'Dr. Ramesh Kumar',   'it@campus.edu'),
('Academic Affairs',     'Prof. Sunita Sharma', 'academic@campus.edu'),
('Hostel & Facilities',  'Mr. Anil Verma',      'hostel@campus.edu'),
('Library',              'Ms. Priya Nair',       'library@campus.edu'),
('Sports & Recreation',  'Mr. Suresh Pillai',   'sports@campus.edu'),
('Canteen & Cafeteria',  'Mr. Ravi Das',        'canteen@campus.edu'),
('Security',             'Mr. Mohan Singh',     'security@campus.edu'),
('Administration',       'Dr. Kavya Menon',     'admin@campus.edu');

INSERT IGNORE INTO categories (cat_name, description, dept_id) VALUES
('Network / WiFi Issue',      'Internet connectivity problems',               1),
('Software / System Issue',   'Lab computers, software access',               1),
('Exam Scheduling',           'Issues with exam timetable',                   2),
('Faculty Concern',           'Academic-related faculty issues',               2),
('Hostel Maintenance',        'Room, plumbing, electricity in hostel',        3),
('Hostel Food Quality',       'Food served in hostel mess',                   3),
('Library Book Availability', 'Missing or damaged books',                     4),
('Library Silence Violation', 'Disturbance in library',                       4),
('Sports Equipment Damage',   'Damaged or missing sports equipment',          5),
('Canteen Hygiene',           'Cleanliness and food safety in canteen',       6),
('Canteen Pricing',           'Overcharging in canteen',                      6),
('Security Concern',          'Safety/security issue on campus',              7),
('Lost & Found',              'Lost items on campus',                         7),
('Administrative Issue',      'Certificate, bonafide, fees related',          8),
('Other',                     'Issues not covered above',                     8);

-- Admin account  (password: Admin@123)
INSERT IGNORE INTO users (full_name, email, password_hash, role) VALUES
('System Admin', 'admin@campus.edu',
 '$2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin');

-- Demo student (password: Student@123)
INSERT IGNORE INTO users (full_name, email, password_hash, role, roll_number, dept_id, phone) VALUES
('Arjun Mehta', 'arjun@student.edu',
 '$2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'student', 'CS2021001', 1, '9876543210');

-- Demo staff (password: Staff@123)
INSERT IGNORE INTO users (full_name, email, password_hash, role, dept_id) VALUES
('Ravi Shankar', 'ravi@campus.edu',
 '$2b$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'staff', 1);

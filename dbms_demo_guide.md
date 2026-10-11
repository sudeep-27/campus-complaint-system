# DBMS Lab Mini Project: Review-2 & Demo Guidelines

This guide lists the schema structure and standard SQL queries to show your project guide/evaluator during the DBMS Mini Project Demo.

---

## 1. Database Schema & Entities (8 Tables, 5+ Attributes each)

All tables use the **InnoDB** storage engine to support relationships, foreign key constraints, and transactional integrity.

### Entity Details:
1. **`departments`**: Stores campus departments (IT, Hostels, Academics, Library, etc.).
   - Attributes (5): `dept_id` (PK), `dept_name`, `dept_head`, `contact_email`, `created_at`.
2. **`users`**: Stores admin, staff/officers, and students.
   - Attributes (11): `user_id` (PK), `full_name`, `email`, `password_hash`, `role`, `roll_number`, `dept_id` (FK), `phone`, `profile_pic`, `is_active`, `created_at`.
3. **`categories`**: Stores categories under which complaints can be filed.
   - Attributes (5): `cat_id` (PK), `cat_name`, `description`, `dept_id` (FK), `created_at`.
4. **`complaints`**: Core table tracking complaints, status, and assignments.
   - Attributes (15): `complaint_id` (PK), `title`, `description`, `status`, `priority`, `user_id` (FK), `cat_id` (FK), `dept_id` (FK), `assigned_to` (FK), `attachment`, `location`, `is_anonymous`, `created_at`, `updated_at`, `resolved_at`.
5. **`complaint_logs`**: Logs status transitions (audit trail).
   - Attributes (7): `log_id` (PK), `complaint_id` (FK), `changed_by` (FK), `old_status`, `new_status`, `remarks`, `changed_at`.
6. **`comments`**: Threaded conversations on complaints.
   - Attributes (5): `comment_id` (PK), `complaint_id` (FK), `user_id` (FK), `comment_text`, `created_at`.
7. **`feedback`**: Satisfaction ratings submitted by students.
   - Attributes (6): `feedback_id` (PK), `complaint_id` (FK, Unique), `user_id` (FK), `rating`, `remarks`, `submitted_at`.
8. **`notifications`**: Real-time notification logs.
   - Attributes (6): `notif_id` (PK), `user_id` (FK), `message`, `type`, `is_read`, `created_at`.

---

## 2. Standard SQL Commands Demo Script

Open your MySQL command line client and run the following commands to demonstrate your DBMS functionalities:

### 1. Show Schema and Tables
```sql
-- Connect to the database
USE campus_complaints;

-- Show all 8 tables
SHOW TABLES;

-- Show structure of the categories table (Verify 5 attributes)
DESCRIBE categories;

-- Show structure of the complaints table
DESCRIBE complaints;
```

### 2. View Table Records (Verify 5+ Seeded Rows)
```sql
-- Count rows in every table to show they meet the 5-row requirement
SELECT 'departments' AS Table_Name, COUNT(*) AS Row_Count FROM departments
UNION SELECT 'users', COUNT(*) FROM users
UNION SELECT 'categories', COUNT(*) FROM categories
UNION SELECT 'complaints', COUNT(*) FROM complaints
UNION SELECT 'complaint_logs', COUNT(*) FROM complaint_logs
UNION SELECT 'comments', COUNT(*) FROM comments
UNION SELECT 'feedback', COUNT(*) FROM feedback
UNION SELECT 'notifications', COUNT(*) FROM notifications;

-- Read all users
SELECT user_id, full_name, email, role FROM users;
```

### 3. Demonstrate VIEW (Join Query)
A view called `complaint_summary_view` is configured to automatically join complaints with users, departments, and categories.

```sql
-- Query the VIEW
SELECT * FROM complaint_summary_view LIMIT 5;

-- Describe the VIEW structure
DESCRIBE complaint_summary_view;
```

### 4. Demonstrate TRIGGER (Auto Resolved Timestamp)
The `before_complaint_update` trigger automatically updates the `resolved_at` timestamp when a status is updated to `'resolved'` and resets it to `NULL` if reverted.

```sql
-- Check current status and resolved timestamp of a complaint (e.g., complaint #2)
SELECT complaint_id, status, resolved_at FROM complaints WHERE complaint_id = 2;

-- Update status to 'resolved' (This fires the BEFORE UPDATE trigger)
UPDATE complaints SET status = 'resolved' WHERE complaint_id = 2;

-- Verify that the trigger set the resolved_at timestamp
SELECT complaint_id, status, resolved_at FROM complaints WHERE complaint_id = 2;

-- Revert status back to 'in_progress' and check resolved_at goes back to NULL
UPDATE complaints SET status = 'in_progress' WHERE complaint_id = 2;
SELECT complaint_id, status, resolved_at FROM complaints WHERE complaint_id = 2;
```

### 5. Demonstrate INSERT
Insert a new user (Staff Member) or a new complaint:

```sql
-- Insert a new staff member
INSERT INTO users (full_name, email, password_hash, role, dept_id, phone) 
VALUES ('Prof. Rajesh Koothrapali', 'rajesh@campus.edu', '$2b$12$DummyHashStringForDemoPurposesOnly', 'staff', 2, '9876500112');

-- Verify insertion
SELECT * FROM users WHERE email = 'rajesh@campus.edu';
```

### 6. Demonstrate UPDATE
Update profile details or update a user role:

```sql
-- Update phone number for user ID 2
UPDATE users SET phone = '8888888888' WHERE user_id = 2;

-- Verify update
SELECT user_id, full_name, phone FROM users WHERE user_id = 2;
```

### 7. Demonstrate ALTER TABLE
Show how to add or modify a column dynamically:

```sql
-- Add a new column to departments table
ALTER TABLE departments ADD COLUMN room_number VARCHAR(20) DEFAULT 'Room 101';

-- Describe departments to verify new column
DESCRIBE departments;

-- Clean up: Remove the column after showing the evaluator
ALTER TABLE departments DROP COLUMN room_number;
```

### 8. Demonstrate DELETE
Delete a log or notification permanently (admin only):

```sql
-- View notifications first
SELECT * FROM notifications ORDER BY notif_id DESC LIMIT 1;

-- Delete the latest notification
DELETE FROM notifications ORDER BY notif_id DESC LIMIT 1;
```

---

## 3. Bidirectional Synchronization
Changes made in the Flask frontend web interface are directly committed to the MySQL database. 
Conversely, running updates/inserts/deletes directly in the MySQL client line will instantly update what is rendered on the student and admin dashboard portals upon page refresh.

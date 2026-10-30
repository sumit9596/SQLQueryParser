"""
Database Seeder Script
Creates a realistic SQLite database with 'departments', 'students', and 'marks' tables.
"""

import sqlite3
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "college.db"

def init_database():
    print(f"Initializing database at: {DB_PATH}")
    
    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables to ensure clean slate
    cursor.execute("DROP TABLE IF EXISTS marks;")
    cursor.execute("DROP TABLE IF EXISTS students;")
    cursor.execute("DROP TABLE IF EXISTS departments;")

    # 1. Departments Table
    cursor.execute("""
    CREATE TABLE departments (
        dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dept_name TEXT NOT NULL,
        head_of_department TEXT NOT NULL,
        building TEXT NOT NULL
    );
    """)

    # 2. Students Table
    cursor.execute("""
    CREATE TABLE students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        dept_id INTEGER NOT NULL,
        year_of_study INTEGER NOT NULL,
        email TEXT UNIQUE NOT NULL,
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
    );
    """)

    # 3. Marks Table
    cursor.execute("""
    CREATE TABLE marks (
        mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        marks_obtained INTEGER NOT NULL,
        max_marks INTEGER DEFAULT 100,
        grade TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );
    """)

    # Seed Departments
    departments = [
        (1, "Computer Science", "Dr. A. K. Sharma", "Block A"),
        (2, "Mechanical Engineering", "Dr. Rajesh Verma", "Block B"),
        (3, "Electrical Engineering", "Dr. Sunita Rao", "Block C"),
        (4, "Data Science & AI", "Dr. Vikram Seth", "Block A"),
    ]
    cursor.executemany(
        "INSERT INTO departments (dept_id, dept_name, head_of_department, building) VALUES (?, ?, ?, ?);",
        departments
    )

    # Seed Students (Roll No 1 to 10)
    students = [
        (1, 1, "Aarav Gupta", "Male", 1, 3, "aarav.gupta@college.edu"),
        (2, 2, "Ananya Singh", "Female", 1, 3, "ananya.singh@college.edu"),
        (3, 3, "Rohan Mehta", "Male", 2, 2, "rohan.mehta@college.edu"),
        (4, 4, "Pooja Patel", "Female", 3, 4, "pooja.patel@college.edu"),
        (5, 5, "Rahul Verma", "Male", 1, 3, "rahul.verma@college.edu"),  # Roll number 5
        (6, 6, "Sneha Reddy", "Female", 4, 1, "sneha.reddy@college.edu"),
        (7, 7, "Kabir Das", "Male", 4, 1, "kabir.das@college.edu"),
        (8, 8, "Diya Roy", "Female", 1, 2, "diya.roy@college.edu"),
        (9, 9, "Mohit Sharma", "Male", 2, 3, "mohit.sharma@college.edu"),
        (10, 10, "Isha Jain", "Female", 3, 2, "isha.jain@college.edu")
    ]
    cursor.executemany(
        "INSERT INTO students (student_id, roll_no, name, gender, dept_id, year_of_study, email) VALUES (?, ?, ?, ?, ?, ?, ?);",
        students
    )

    # Seed Marks
    marks = [
        # Aarav (Student 1)
        (1, "Data Structures", 85, 100, "A"),
        (1, "Database Systems", 78, 100, "B+"),
        (1, "Machine Learning", 90, 100, "A+"),
        # Ananya (Student 2 - Top Performer)
        (2, "Data Structures", 96, 100, "A+"),
        (2, "Database Systems", 94, 100, "A+"),
        (2, "Machine Learning", 98, 100, "A+"),
        # Rohan (Student 3)
        (3, "Thermodynamics", 72, 100, "B"),
        (3, "Fluid Mechanics", 68, 100, "C+"),
        # Pooja (Student 4)
        (4, "Power Systems", 88, 100, "A"),
        (4, "Control Systems", 82, 100, "A"),
        # Rahul Verma (Student 5, Roll 5)
        (5, "Data Structures", 89, 100, "A"),
        (5, "Database Systems", 92, 100, "A+"),
        (5, "Machine Learning", 86, 100, "A"),
        # Sneha (Student 6 - AI Topper)
        (6, "Python Programming", 95, 100, "A+"),
        (6, "Linear Algebra", 93, 100, "A+"),
        # Kabir (Student 7)
        (7, "Python Programming", 74, 100, "B"),
        (7, "Linear Algebra", 79, 100, "B+"),
        # Diya (Student 8)
        (8, "Data Structures", 81, 100, "A"),
        (8, "Database Systems", 85, 100, "A"),
        # Mohit (Student 9)
        (9, "Thermodynamics", 65, 100, "C"),
        (9, "Fluid Mechanics", 61, 100, "C"),
        # Isha (Student 10)
        (10, "Power Systems", 91, 100, "A+"),
        (10, "Control Systems", 89, 100, "A"),
    ]
    cursor.executemany(
        "INSERT INTO marks (student_id, subject, marks_obtained, max_marks, grade) VALUES (?, ?, ?, ?, ?);",
        marks
    )

    conn.commit()
    conn.close()
    print("Database seeded successfully with 4 Departments, 10 Students, and 23 Marks entries!")

if __name__ == "__main__":
    init_database()

import sqlite3
import os

db_path = 'instance/cs_gauntlet.db'
print(f"Checking database at: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    # Check if user table exists and get users
    try:
        cursor.execute("SELECT COUNT(*) FROM user;")
        user_count = cursor.fetchone()[0]
        print(f"Number of users: {user_count}")
        
        if user_count > 0:
            cursor.execute("SELECT id, username, email, university, github_username FROM user LIMIT 10;")
            users = cursor.fetchall()
            print("Users in database:")
            for user in users:
                print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, University: {user[3]}, GitHub: {user[4]}")
    except Exception as e:
        print(f"Error querying users: {e}")
    
    conn.close()
else:
    print("Database file does not exist")

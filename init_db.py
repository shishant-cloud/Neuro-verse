import sqlite3

def setup_database():
    # This creates the file 'neuroverse.db' in your project folder
    conn = sqlite3.connect('neuroverse.db')
    cursor = conn.cursor()

    # Create the 'users' table with the columns you need
    print("Creating table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            designation TEXT DEFAULT 'Neuro-Researcher'
        )
    ''')

    # Add a default Admin/Student so you can log in immediately
    # If the user already exists, it will skip this part
    cursor.execute("SELECT * FROM users WHERE email = 'admin@neuro.com'")
    if not cursor.fetchone():
        print("Inserting default user...")
        cursor.execute('''
            INSERT INTO users (username, email, password, designation)
            VALUES (?, ?, ?, ?)
        ''', ('Admin User', 'admin@neuro.com', '12345', 'Administrator'))

    conn.commit()
    conn.close()
    print("Database initialized successfully! You can now run app.py.")

if __name__ == '__main__':
    setup_database()
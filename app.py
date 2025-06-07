from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
DB_FILE = 'fitness.db'

IST = pytz.timezone('Asia/Kolkata')


# ---------- DATABASE INIT ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    instructor TEXT,
                    datetime_utc TEXT,
                    slots INTEGER
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    client_name TEXT,
                    client_email TEXT,
                    FOREIGN KEY(class_id) REFERENCES classes(id)
                )''')
    conn.commit()
    conn.close()


# ---------- TIMEZONE CONVERSION ----------
def convert_utc_to_timezone(dt_str, tz_str):
    tz = pytz.timezone(tz_str)
    dt_utc = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
    return dt_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")


# ---------- ROUTES ----------
@app.route('/classes', methods=['GET'])
def get_classes():
    timezone = request.args.get("timezone", "Asia/Kolkata")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, datetime_utc, instructor, slots FROM classes")
    rows = c.fetchall()
    conn.close()

    result = []
    for row in rows:
        converted_time = convert_utc_to_timezone(row[2], timezone)
        result.append({
            "id": row[0],
            "name": row[1],
            "datetime": converted_time,
            "instructor": row[3],
            "available_slots": row[4]
        })
    return jsonify(result)


@app.route('/book', methods=['POST'])
def book_class():
    data = request.get_json()
    required = ['class_id', 'client_name', 'client_email']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    class_id = data['class_id']
    name = data['client_name']
    email = data['client_email']

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT slots FROM classes WHERE id=?", (class_id,))
    class_info = c.fetchone()
    if not class_info:
        return jsonify({"error": "Class not found"}), 404
    if class_info[0] <= 0:
        return jsonify({"error": "No slots available"}), 400

    # Book the slot
    c.execute("INSERT INTO bookings (class_id, client_name, client_email) VALUES (?, ?, ?)",
              (class_id, name, email))
    c.execute("UPDATE classes SET slots = slots - 1 WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Booking successful"}), 201


@app.route('/bookings', methods=['GET'])
def get_bookings():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email required"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT b.id, c.name, c.datetime_utc FROM bookings b
                 JOIN classes c ON b.class_id = c.id WHERE b.client_email = ?''', (email,))
    rows = c.fetchall()
    conn.close()

    return jsonify([{
        "booking_id": row[0],
        "class_name": row[1],
        "class_time_IST": convert_utc_to_timezone(row[2], "Asia/Kolkata")
    } for row in rows])


# ---------- UTILITY: ADD SAMPLE CLASSES ----------
def add_sample_classes():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now_utc = datetime.now(IST).astimezone(pytz.UTC)
    sample_classes = [
        ('Yoga', 'Anjali', now_utc.replace(hour=6, minute=0).strftime("%Y-%m-%d %H:%M:%S"), 10),
        ('Zumba', 'Ravi', now_utc.replace(hour=8, minute=0).strftime("%Y-%m-%d %H:%M:%S"), 8),
        ('HIIT', 'Suresh', now_utc.replace(hour=18, minute=0).strftime("%Y-%m-%d %H:%M:%S"), 5),
    ]
    for name, instructor, dt, slots in sample_classes:
        c.execute("INSERT INTO classes (name, instructor, datetime_utc, slots) VALUES (?, ?, ?, ?)",
                  (name, instructor, dt, slots))
    conn.commit()
    conn.close()


# ---------- MAIN ----------
if __name__ == '__main__':
    init_db()
    add_sample_classes()
    app.run(debug=True)

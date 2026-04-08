from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import random
import math
import smtplib
from email.mime.text import MIMEText

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
CORS(app)

ROOM_CAPACITY = 9

# LOGIN
users = {"admin": "1234"}
real_email_count = 0


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if users.get(data['username']) == data['password']:
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"})


# EMAIL FUNCTION
def send_email(to_email, message):
    global real_email_count

    if real_email_count < 2:
        try:
            sender_email = "yourgmail@gmail.com"
            app_password = "your_app_password"

            msg = MIMEText(message)
            msg['Subject'] = "Exam Seating Details"
            msg['From'] = sender_email
            msg['To'] = to_email

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
            server.quit()

            print("✅ REAL EMAIL SENT:", to_email)

        except Exception as e:
            print("❌ Email error:", e)

        real_email_count += 1
    else:
        print("\n📧 SIMULATED EMAIL")
        print("To:", to_email)
        print("Message:", message)
        print("------------------")


# CHECK RULE
def is_safe(grid, r, c, student, rows, cols):
    directions = [(-1,0),(1,0),(0,-1),(0,1)]
    for dr, dc in directions:
        nr, nc = r+dr, c+dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc]:
                if grid[nr][nc]['subject'] == student['subject']:
                    return False
                if grid[nr][nc]['dept'] == student['dept']:
                    return False
    return True


# ARRANGEMENT
def arrange_room(students, rows, cols):
    grid = [[None for _ in range(cols)] for _ in range(rows)]
    random.shuffle(students)

    def backtrack(index):
        if index == len(students):
            return True

        r, c = divmod(index, cols)

        for i in range(len(students)):
            student = students[i]
            if student is None:
                continue

            if is_safe(grid, r, c, student, rows, cols):
                grid[r][c] = student
                students[i] = None

                if backtrack(index + 1):
                    return True

                grid[r][c] = None
                students[i] = student

        return False

    success = backtrack(0)

    if not success:
        grid = [[None for _ in range(cols)] for _ in range(rows)]
        idx = 0
        students_copy = [s for s in students if s is not None]

        for r in range(rows):
            for c in range(cols):
                if idx < len(students_copy):
                    grid[r][c] = students_copy[idx]
                    idx += 1

    return grid


# ROOM ALLOCATION
def allocate_rooms(students):
    rooms = []
    num_rooms = math.ceil(len(students) / ROOM_CAPACITY)

    for i in range(num_rooms):
        room_students = students[i*ROOM_CAPACITY:(i+1)*ROOM_CAPACITY]

        size = math.ceil(math.sqrt(len(room_students)))
        grid = arrange_room(room_students.copy(), size, size)

        seat_no = 1
        formatted = []

        for row in grid:
            new_row = []
            for s in row:
                if s:
                    text = f"Seat {seat_no}\n{s['name']}\n{s['subject']}, {s['dept']}"

                    msg = f"""
Hello {s['name']},

Room: Room {i+1}
Seat Number: {seat_no}
Subject: {s['subject']}
"""
                    send_email(s['email'], msg)

                else:
                    text = f"Seat {seat_no}\nEmpty"

                new_row.append(text)
                seat_no += 1

            formatted.append(new_row)

        rooms.append({
            "room": f"Room {i+1}",
            "layout": formatted
        })

    return rooms


# UPLOAD
@app.route('/upload', methods=['POST'])
def upload():
    global real_email_count
    real_email_count = 0

    file = request.files['file']
    df = pd.read_excel(file)

    students = []
    for _, r in df.iterrows():
        students.append({
            "name": r['Name'],
            "subject": r['Subject'],
            "dept": r.get('Department') or r.get('Branch') or r.get('Dept') or 'CSE',
            "email": r.get('Email', 'demo@gmail.com')
        })

    rooms = allocate_rooms(students)

    return jsonify({
        "rooms": rooms
    })


# PDF EXPORT (🔥 IMPROVED TABLE)
@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    data = request.json
    pdf = SimpleDocTemplate("seating.pdf")
    styles = getSampleStyleSheet()

    elements = []

    for room in data:
        elements.append(Paragraph(room['room'], styles['Heading1']))
        elements.append(Spacer(1, 10))

        table = Table(room['layout'])

        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    pdf.build(elements)

    return jsonify({"msg": "PDF created successfully"})


if __name__ == '__main__':
        app.run(debug=True, use_reloader=False)
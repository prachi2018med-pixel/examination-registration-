import os
import qrcode
import io
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from xhtml2pdf import pisa

app = Flask(__name__)
app.secret_key = "render_secret_key"

# Database Configuration
# Render provides DATABASE_URL. We fix the 'postgres://' prefix for SQLAlchemy.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///students.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), nullable=False, unique=True)
    branch = db.Column(db.String(50), nullable=False)
    subjects = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    roll_no = request.form.get('roll_no')
    branch = request.form.get('branch')
    subjects = ", ".join(request.form.getlist('subjects'))

    # Save to Database
    new_student = Student(name=name, roll_no=roll_no, branch=branch, subjects=subjects)
    db.session.add(new_student)
    db.session.commit()

    # Generate QR Code
    qr_data = f"Student: {name} | Roll: {roll_no}"
    qr = qrcode.make(qr_data)
    
    qr_dir = os.path.join('static', 'qrcodes')
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)
        
    qr.save(os.path.join(qr_dir, f"{new_student.id}.png"))

    return redirect(url_for('hall_ticket', student_id=new_student.id))

@app.route('/hallticket/<int:student_id>')
def hall_ticket(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('hallticket.html', s=student)

@app.route('/download_pdf/<int:student_id>')
def download_pdf(student_id):
    student = Student.query.get_or_404(student_id)
    # Render the HTML for the PDF
    html = render_template('hallticket.html', s=student, is_pdf=True)
    
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode("utf-8")), dest=result)
    
    if pisa_status.err:
        return "Error generating PDF", 500
    
    result.seek(0)
    return send_file(result, as_attachment=True, download_name=f"HallTicket_{student.roll_no}.pdf")

if __name__ == '__main__':
    app.run(debug=True)
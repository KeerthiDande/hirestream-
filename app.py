import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = "hirestream_secret_key"

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["hirestream_db"]
users_col = db["users"]
employees_col = db["employees"]
documents_col = db["documents"]
tasks_col = db["tasks"]
settings_col = db["settings"]
logs_col = db["logs"]

# --- Middleware ---
def login_required(f):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# --- Routes ---

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = users_col.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password", "error")
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    
    if users_col.find_one({"email": email}):
        flash("Email already exists", "error")
        return redirect(url_for("login"))
    
    hashed_password = generate_password_hash(password)
    users_col.insert_one({
        "username": username,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    })
    flash("Signup successful! Please login.", "success")
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "total_employees": employees_col.count_documents({}),
        "pending_docs": documents_col.count_documents({"status": "Pending"}),
        "active_tasks": tasks_col.count_documents({"status": "In Progress"}),
        "completed_onboarding": employees_col.count_documents({"status": "Completed"})
    }
    recent_employees = list(employees_col.find().sort("created_at", -1).limit(5))
    return render_template("dashboard.html", stats=stats, recent_employees=recent_employees)

@app.route("/employees", methods=["GET", "POST"])
@login_required
def employees():
    if request.method == "POST":
        employee_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "role": request.form.get("role"),
            "department": request.form.get("department"),
            "status": "Pending",
            "created_at": datetime.utcnow()
        }
        employees_col.insert_one(employee_data)
        flash("Employee added successfully!", "success")
        return redirect(url_for("employees"))
    
    all_employees = list(employees_col.find())
    return render_template("employees.html", employees=all_employees)

@app.route("/employees/delete/<id>")
@login_required
def delete_employee(id):
    employees_col.delete_one({"_id": ObjectId(id)})
    flash("Employee removed from records.", "success")
    return redirect(url_for("employees"))

@app.route("/documents", methods=["GET", "POST"])
@login_required
def documents():
    if request.method == "POST":
        # Simulate file upload
        doc_data = {
            "employee_name": request.form.get("employee_name"),
            "doc_type": request.form.get("doc_type"),
            "filename": request.form.get("filename"),
            "status": "Pending",
            "uploaded_at": datetime.utcnow()
        }
        documents_col.insert_one(doc_data)
        flash("Document uploaded and pending verification.", "success")
        return redirect(url_for("documents"))
        
    all_docs = list(documents_col.find())
    return render_template("documents.html", documents=all_docs)

@app.route("/documents/verify/<id>")
@login_required
def verify_document(id):
    documents_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "Verified"}})
    flash("Document verified successfully!", "success")
    return redirect(url_for("documents"))

@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "POST":
        task_data = {
            "task_name": request.form.get("task_name"),
            "assigned_to": request.form.get("assigned_to"),
            "due_date": request.form.get("due_date"),
            "status": "In Progress",
            "created_at": datetime.utcnow()
        }
        tasks_col.insert_one(task_data)
        flash("Task assigned successfully!", "success")
        return redirect(url_for("tasks"))
        
    all_tasks = list(tasks_col.find())
    return render_template("tasks.html", tasks=all_tasks)

@app.route("/tasks/complete/<id>")
@login_required
def complete_task(id):
    tasks_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "Completed"}})
    flash("Task marked as completed!", "success")
    return redirect(url_for("tasks"))

@app.route("/generate_offer", methods=["POST"])
@login_required
def generate_offer():
    # This would normally generate a PDF, but we'll simulate it
    employee_id = request.form.get("employee_id")
    flash(f"Offer letter generated for employee {employee_id}!", "success")
    return redirect(url_for("tasks"))

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        company_name = request.form.get("company_name")
        settings_col.update_one({}, {"$set": {"company_name": company_name}}, upsert=True)
        flash("Settings updated!", "success")
        return redirect(url_for("settings"))
        
    config = settings_col.find_one({}) or {"company_name": "HireStream"}
    return render_template("settings.html", config=config)

if __name__ == "__main__":
    app.run(debug=True, port=5000)

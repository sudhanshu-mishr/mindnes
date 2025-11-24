from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os, random

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
print("USING DB FILE:", os.path.join(BASE_DIR, "mindnest.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mindnest.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_minutes = db.Column(db.Integer, default=0)

    journal_entries = db.relationship("JournalEntry", backref="user", lazy=True)
    moods = db.relationship("MoodLog", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(50))
    tags = db.Column(db.String(250))
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    mood_value = db.Column(db.Integer, nullable=False)
    emotion_label = db.Column(db.String(100))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


QUOTES = [
    {"text": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein"},
    {"text": "You are allowed to be both a masterpiece and a work in progress at the same time.", "author": "Unknown"},
    {"text": "One small positive thought in the morning can change your whole day.", "author": "Unknown"},
    {"text": "Peace comes from within. Do not seek it without.", "author": "Buddha"},
    {"text": "You don’t have to control your thoughts; you just have to stop letting them control you.", "author": "Dan Millman"},
]


def get_daily_quote():
    random.seed(date.today().toordinal())
    return random.choice(QUOTES)


RESOURCES = [
    {
        "title": "5-Minute Breathing Exercise",
        "category": "Breathwork",
        "url": "https://www.youtube.com/results?search_query=5+minute+breathing+exercise",
        "description": "A short guided breathing practice to reset your nervous system.",
    },
    {
        "title": "Body Scan Meditation",
        "category": "Meditation",
        "url": "https://www.youtube.com/results?search_query=body+scan+meditation+10+minutes",
        "description": "Gently notice and relax each part of your body.",
    },
    {
        "title": "Understanding Anxiety",
        "category": "Article",
        "url": "https://www.healthline.com/health/anxiety",
        "description": "Learn more about anxiety, symptoms, and supportive strategies.",
    },
    {
        "title": "Sleep Hygiene Tips",
        "category": "Sleep",
        "url": "https://www.sleepfoundation.org/sleep-hygiene",
        "description": "Simple changes to help you rest more deeply at night.",
    },
]


def update_time_spent():
    if not current_user.is_authenticated:
        return
    start = session.get("session_start")
    now = datetime.utcnow().timestamp()
    if start is None:
        session["session_start"] = now
        return
    elapsed_seconds = now - float(start)
    minutes = int(elapsed_seconds // 60)
    if minutes >= 1:
        if current_user.total_minutes is None:
            current_user.total_minutes = 0
        current_user.total_minutes += minutes
        session["session_start"] = now
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if not name or not email or not password:
            flash("Please fill in all required fields.", "warning")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))
        existing = User.query.filter_by(email=email.lower()).first()
        if existing:
            flash("That email is already registered. Please log in.", "warning")
            return redirect(url_for("login"))
        user = User(name=name.strip(), email=email.lower().strip())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email.lower()).first()
        if user and user.check_password(password):
            login_user(user)
            session["session_start"] = datetime.utcnow().timestamp()
            flash("Welcome back 🌿", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("session_start", None)
    logout_user()
    flash("You’ve been logged out. See you soon 💛", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    update_time_spent()
    quote = get_daily_quote()
    total_entries = JournalEntry.query.filter_by(user_id=current_user.id).count()
    total_moods = MoodLog.query.filter_by(user_id=current_user.id).count()
    recent_entries = (
        JournalEntry.query.filter_by(user_id=current_user.id)
        .order_by(JournalEntry.created_at.desc())
        .limit(5)
        .all()
    )
    recent_moods = (
        MoodLog.query.filter_by(user_id=current_user.id)
        .order_by(MoodLog.created_at.desc())
        .limit(7)
        .all()
    )
    mood_labels = [m.created_at.strftime("%d %b") for m in reversed(recent_moods)]
    mood_values = [m.mood_value for m in reversed(recent_moods)]
    total_minutes = current_user.total_minutes or 0
    return render_template(
        "dashboard.html",
        quote=quote,
        total_entries=total_entries,
        total_moods=total_moods,
        recent_entries=recent_entries,
        mood_labels=mood_labels,
        mood_values=mood_values,
        total_minutes=total_minutes,
    )


@app.route("/journal", methods=["GET", "POST"])
@login_required
def journal():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        mood = request.form.get("mood")
        tags = request.form.get("tags")
        image_file = request.files.get("image")

        if not content:
            flash("Your entry needs some text.", "warning")
            return redirect(url_for("journal"))

        image_filename = None
        if image_file and image_file.filename:
            safe_name = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{image_file.filename}"
            path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
            try:
                image_file.save(path)
                image_filename = os.path.basename(path)
            except Exception:
                flash("Could not save image. Entry will be saved without it.", "warning")

        entry = JournalEntry(
            user_id=current_user.id,
            title=title,
            content=content,
            mood=mood,
            tags=tags,
            image_filename=image_filename,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Journal entry saved 🌱", "success")
        return redirect(url_for("journal"))

    entries = (
        JournalEntry.query.filter_by(user_id=current_user.id)
        .order_by(JournalEntry.created_at.desc())
        .all()
    )
    return render_template("journal.html", entries=entries)


@app.route("/journal/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_journal_entry(entry_id):
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash("Entry deleted.", "info")
    return redirect(url_for("journal"))


@app.route("/mood", methods=["GET", "POST"])
@login_required
def mood():
    if request.method == "POST":
        try:
            mood_value = int(request.form.get("mood_value", 3))
        except ValueError:
            mood_value = 3
        emotion_label = request.form.get("emotion_label")
        note = request.form.get("note")
        log = MoodLog(
            user_id=current_user.id,
            mood_value=mood_value,
            emotion_label=emotion_label,
            note=note,
        )
        db.session.add(log)
        db.session.commit()
        flash("Mood check-in saved 💚", "success")
        return redirect(url_for("mood"))

    logs = (
        MoodLog.query.filter_by(user_id=current_user.id)
        .order_by(MoodLog.created_at.desc())
        .all()
    )
    last_14 = logs[-14:]
    labels = [l.created_at.strftime("%d %b") for l in reversed(last_14)]
    values = [l.mood_value for l in reversed(last_14)]
    return render_template("mood.html", logs=logs, labels=labels, values=values)


@app.route("/resources")
@login_required
def resources():
    return render_template("resources.html", resources=RESOURCES)


@app.route("/sounds")
@login_required
def sounds():
    white_noises = [
        {"filename": "white_noise_1.wav", "title": "Soft white noise"},
        {"filename": "white_noise_2.wav", "title": "Gentle white noise"},
        {"filename": "pink_noise.wav", "title": "Pink noise (soft highs)"},
        {"filename": "brown_noise.wav", "title": "Brown noise (deep & warm)"},
    ]
    nature_tracks = [
        {"filename": "ocean_wave_noise.wav", "title": "Ocean-like waves"},
        {"filename": "forest_wind.wav", "title": "Forest wind ambience"},
        {"filename": "soft_rain.wav", "title": "Soft rain ambience"},
    ]
    tibetan_tracks = [
        {"filename": "tibetan_drone.wav", "title": "Tibetan-style calming drone"},
        {"filename": "tibetan_bells.wav", "title": "Soft Tibetan bowl & bells"},
        {"filename": "tibetan_chant_like.wav", "title": "Tibetan-inspired low chant tones"},
    ]
    return render_template(
        "sounds.html",
        white_noises=white_noises,
        nature_tracks=nature_tracks,
        tibetan_tracks=tibetan_tracks,
    )




@app.route("/games")
@login_required
def games():
    return render_template("games.html")

@app.route("/profile")
@login_required
def profile():
    update_time_spent()
    total_minutes = current_user.total_minutes or 0
    return render_template("profile.html", total_minutes=total_minutes)


def is_admin():
    return session.get("is_admin") is True


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "sudhanshu" and password == "kt2311":
            session["is_admin"] = True
            flash("Admin login successful.", "success")
            return redirect(url_for("admin_panel"))
        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")


@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
def admin_panel():
    if not is_admin():
        return redirect(url_for("admin_login"))
    users = User.query.order_by(User.created_at.desc()).all()
    summaries = []
    for u in users:
        minutes = u.total_minutes or 0
        hours = minutes // 60
        rem = minutes % 60
        time_display = f"{hours}h {rem}m" if hours else f"{minutes} min"
        summaries.append(
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "joined": u.created_at.strftime("%d %b %Y"),
                "entries": len(u.journal_entries),
                "moods": len(u.moods),
                "time": time_display,
            }
        )
    return render_template("admin_panel.html", users=summaries)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0",debug=True)

import os
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from flask_sqlalchemy import SQLAlchemy


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    db_path = os.environ.get(
        "SQLITE_DB_PATH",
        os.path.join(DATA_DIR, "infra_pulse.db"),
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    register_routes(app)

    with app.app_context():
        db.create_all()

    return app


db = SQLAlchemy()


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    incidents = db.relationship(
        "Incident",
        backref="project",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=False)
    downtime_minutes = db.Column(db.Integer, nullable=True)
    is_resolved = db.Column(db.Boolean, default=False)
    resolution_summary = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)


def get_admin_credentials() -> tuple[str, str]:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin")
    return username, password


def login_required(view_func):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    wrapper.__name__ = view_func.__name__
    return wrapper


def register_routes(app: Flask) -> None:
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            admin_user, admin_pass = get_admin_credentials()
            if username == admin_user and password == admin_pass:
                session["logged_in"] = True
                flash("Welcome back to InfraPulse.", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid credentials.", "danger")
        return render_template("login.html", app_name="InfraPulse")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        projects = Project.query.all()

        project_labels = []
        open_counts = []
        closed_counts = []
        for project in projects:
            project_labels.append(project.name)
            open_counts.append(
                Incident.query.filter_by(project_id=project.id, is_resolved=False).count()
            )
            closed_counts.append(
                Incident.query.filter_by(project_id=project.id, is_resolved=True).count()
            )

        monthly_data = (
            db.session.query(
                db.func.strftime("%Y-%m", Incident.occurred_at).label("month"),
                db.func.count(Incident.id),
            )
            .group_by("month")
            .order_by("month")
            .all()
        )
        monthly_labels = [row[0] for row in monthly_data]
        monthly_counts = [row[1] for row in monthly_data]

        return render_template(
            "dashboard.html",
            app_name="InfraPulse",
            projects=projects,
            project_labels=project_labels,
            open_counts=open_counts,
            closed_counts=closed_counts,
            monthly_labels=monthly_labels,
            monthly_counts=monthly_counts,
        )

    @app.route("/projects", methods=["GET", "POST"])
    @login_required
    def projects_view():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            if not name:
                flash("Project name is required.", "danger")
            else:
                existing = Project.query.filter_by(name=name).first()
                if existing:
                    flash("Project with this name already exists.", "warning")
                else:
                    project = Project(name=name, description=description or None)
                    db.session.add(project)
                    db.session.commit()
                    flash("Project created.", "success")
                    return redirect(url_for("projects_view"))
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return render_template(
            "projects.html",
            app_name="InfraPulse",
            projects=projects,
        )

    @app.route("/projects/<int:project_id>", methods=["GET", "POST"])
    @login_required
    def project_detail(project_id: int):
        project = Project.query.get_or_404(project_id)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            severity = request.form.get("severity", "medium")
            downtime = request.form.get("downtime_minutes", "").strip()
            is_resolved = request.form.get("is_resolved") == "on"
            resolution_summary = request.form.get("resolution_summary", "").strip()
            occurred_at_str = request.form.get("occurred_at", "").strip()

            if not title:
                flash("Incident title is required.", "danger")
            else:
                incident = Incident(
                    project_id=project.id,
                    title=title,
                    description=description or None,
                    severity=severity,
                    downtime_minutes=int(downtime) if downtime else None,
                    is_resolved=is_resolved,
                    resolution_summary=resolution_summary or None,
                )
                if occurred_at_str:
                    try:
                        incident.occurred_at = datetime.fromisoformat(occurred_at_str)
                    except ValueError:
                        flash("Invalid occurred-at timestamp, using current time.", "warning")
                if is_resolved:
                    incident.resolved_at = datetime.utcnow()

                db.session.add(incident)
                db.session.commit()
                flash("Incident logged.", "success")
                return redirect(url_for("project_detail", project_id=project.id))

        incidents = (
            Incident.query.filter_by(project_id=project.id)
            .order_by(Incident.occurred_at.desc())
            .all()
        )
        return render_template(
            "project_detail.html",
            app_name="InfraPulse",
            project=project,
            incidents=incidents,
        )

    @app.route("/projects/<int:project_id>/delete", methods=["POST"])
    @login_required
    def delete_project(project_id: int):
        project = Project.query.get_or_404(project_id)
        name = project.name
        db.session.delete(project)
        db.session.commit()
        flash(f"Project '{name}' and all its incidents were deleted.", "info")
        return redirect(url_for("projects_view"))

    @app.route("/incidents/<int:incident_id>", methods=["GET", "POST"])
    @login_required
    def incident_detail(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        project = incident.project

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            severity = request.form.get("severity", incident.severity)
            downtime = request.form.get("downtime_minutes", "").strip()
            is_resolved = request.form.get("is_resolved") == "on"
            resolution_summary = request.form.get("resolution_summary", "").strip()
            occurred_at_str = request.form.get("occurred_at", "").strip()

            if not title:
                flash("Incident title is required.", "danger")
            else:
                incident.title = title
                incident.description = description or None
                incident.severity = severity
                incident.downtime_minutes = int(downtime) if downtime else None
                incident.resolution_summary = resolution_summary or None

                if occurred_at_str:
                    try:
                        incident.occurred_at = datetime.fromisoformat(occurred_at_str)
                    except ValueError:
                        flash(
                            "Invalid occurred-at timestamp, keeping previous value.",
                            "warning",
                        )

                previous_resolved = incident.is_resolved
                incident.is_resolved = is_resolved
                if is_resolved and not previous_resolved:
                    incident.resolved_at = datetime.utcnow()
                elif not is_resolved:
                    incident.resolved_at = None

                db.session.commit()
                flash("Incident updated.", "success")
                return redirect(url_for("incident_detail", incident_id=incident.id))

        return render_template(
            "incident_detail.html",
            app_name="InfraPulse",
            incident=incident,
            project=project,
        )

    @app.route("/incidents/<int:incident_id>/toggle_resolved", methods=["POST"])
    @login_required
    def toggle_incident_resolved(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        incident.is_resolved = not incident.is_resolved
        incident.resolved_at = datetime.utcnow() if incident.is_resolved else None
        db.session.commit()
        flash("Incident status updated.", "success")
        return redirect(url_for("project_detail", project_id=incident.project_id))

    @app.route("/incidents/<int:incident_id>/delete", methods=["POST"])
    @login_required
    def delete_incident(incident_id: int):
        incident = Incident.query.get_or_404(incident_id)
        project_id = incident.project_id
        db.session.delete(incident)
        db.session.commit()
        flash("Incident deleted.", "info")
        return redirect(url_for("project_detail", project_id=project_id))


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)), debug=True)
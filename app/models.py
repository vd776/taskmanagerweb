from app import db
from datetime import datetime
from flask_security import UserMixin, RoleMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

projects_users = db.Table('projects_users',
                          db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                          db.Column('project_id', db.Integer(), db.ForeignKey('project.id')))

projects_invited_users = db.Table('projects_invited_users',
                                  db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                                  db.Column('project_id', db.Integer(), db.ForeignKey('project.id')))
class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    projects = db.relationship('Project', secondary=projects_users, backref=db.backref('assigned_users', lazy='dynamic'))
    invited_projects = db.relationship('Project', secondary=projects_invited_users,
                                       backref=db.backref('invited_users', lazy='dynamic'))

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password)


def generate_specific_password_hash(password):
    return generate_password_hash(password, method='pbkdf2:sha256')


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # user = db.relationship('User', backref=db.backref('projects', lazy=True))
    user = db.relationship('User', backref=db.backref('owned_projects', lazy=True))
    users = db.relationship('User', secondary=projects_users, backref=db.backref('assigned_projects', lazy='dynamic'))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='To Do')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', backref=db.backref('tasks', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_user = db.relationship('User', backref=db.backref('assigned_tasks', lazy=True), foreign_keys=[user_id])


class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Possible values: 'Pending', 'Accepted', 'Declined'
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref=db.backref('invitations', lazy=True))
    user = db.relationship('User', backref=db.backref('invitations', lazy=True))
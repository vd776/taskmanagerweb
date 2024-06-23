from datetime import datetime

from flask import render_template, redirect, url_for, Blueprint, request, flash
from flask_login import login_user
from flask_security import login_required, roles_required, current_user
from app import db, get_user_datastore
from app.forms import RegistrationForm, LoginForm, TaskForm, ProjectForm, AddUserForm, SearchForm, EditProjectForm
from app.models import Project, Task, User, generate_specific_password_hash, Invitation

bp = Blueprint('main', __name__)

user_datastore = get_user_datastore()


@bp.route('/')
def home():
    return render_template('index.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('A user with this email already exists. Please use a different email.', 'danger')
            return render_template('register.html', form=form)

        encrypted_password = generate_specific_password_hash(form.password.data)
        user_datastore.create_user(email=form.email.data, password=encrypted_password)
        db.session.commit()
        return redirect(url_for('main.login_custom'))
    return render_template('register.html', form=form)


@bp.route('/login_custom', methods=['GET', 'POST'])
def login_custom():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next = request.args.get('next')
            return redirect(next or url_for('main.home'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login_custom.html', form=form)


@bp.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    search = request.args.get('search')
    sort_by = request.args.get('sort', 'date_created')
    filter_by = request.args.get('filter', 'all')

    owned_projects_query = Project.query.filter_by(user_id=current_user.id)
    assigned_projects_query = current_user.assigned_projects

    if search:
        search_query = f"%{search}%"
        owned_projects_query = owned_projects_query.filter(Project.name.ilike(search_query))
        assigned_projects_query = assigned_projects_query.filter(Project.name.ilike(search_query))

    owned_projects = owned_projects_query.all()
    assigned_projects = assigned_projects_query.all()

    if filter_by == 'owned':
        all_projects = owned_projects
    elif filter_by == 'assigned':
        all_projects = assigned_projects
    else:
        all_projects = list(owned_projects + assigned_projects)  # Combine without using set to maintain order

    if sort_by == 'date_created':
        all_projects.sort(key=lambda project: project.date_created or datetime.min, reverse=True)
    elif sort_by == 'title_asc':
        all_projects.sort(key=lambda project: project.name or "")
    elif sort_by == 'title_desc':
        all_projects.sort(key=lambda project: project.name or "", reverse=True)

    return render_template('projects.html', projects=all_projects, sort_by=sort_by, filter_by=filter_by, search=search)


@bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(name=form.name.data, description=form.description.data, user_id=current_user.id)
        db.session.add(project)
        db.session.commit()
        return redirect(url_for('main.projects'))
    return render_template('new_project.html', form=form)



@bp.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    invitation = Invitation.query.filter_by(user_id=current_user.id, project_id=project_id).first()

    is_owner = project.user_id == current_user.id
    is_participant = current_user in project.users
    is_invited = invitation is not None

    if not (is_owner or is_participant or is_invited):
        flash("You don't have access to this project.", 'danger')
        return redirect(url_for('main.projects'))

    if is_invited and request.method == 'POST':
        action = request.form.get('action')
        if action == 'accept':
            project.users.append(current_user)
            db.session.delete(invitation)
            db.session.commit()
            flash('Invitation accepted!', 'success')
        elif action == 'decline':
            db.session.delete(invitation)
            db.session.commit()
            flash('Invitation declined!', 'success')
        return redirect(url_for('main.project_detail', project_id=project_id))

    return render_template('project_detail.html', project=project, is_owner=is_owner, is_participant=is_participant, is_invited=is_invited)



@bp.route('/projects/<int:project_id>/tasks/<int:task_id>')
@login_required
def task_detail(project_id, task_id):
    task = Task.query.get_or_404(task_id)
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id and current_user not in project.users or task.project_id != project_id:
        flash("You don't have access to this task.", 'danger')
        return redirect(url_for('main.projects'))
    return render_template('task_detail.html', task=task)


@bp.route('/projects/<int:project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id and current_user not in project.users:
        flash("You don't have access to this project.", 'danger')
        return redirect(url_for('main.projects'))

    form = TaskForm()
    # form.user.choices = [(user.id, user.email) for user in project.users]
    users_list = [(project.user.id, project.user.email)] + [(user.id, user.email) for user in project.users]
    form.user.choices = users_list

    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            project_id=project_id,
            user_id=form.user.data
        )
        db.session.add(task)
        db.session.commit()
        flash('Task created successfully!', 'success')
        return redirect(url_for('main.project_detail', project_id=project_id))
    return render_template('new_task.html', form=form, project=project)


@bp.route('/projects/<int:project_id>/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)

    if project.user_id != current_user.id and current_user not in project.users:
        flash("You don't have access to this project.", 'danger')
        return redirect(url_for('main.projects'))

    form = TaskForm(obj=task)

    users_list = [(project.user.id, project.user.email)] + [(user.id, user.email) for user in project.users]
    form.user.choices = users_list

    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.status = form.status.data
        task.user_id = form.user.data
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('main.project_detail', project_id=project_id))

    return render_template('edit_task.html', form=form, project=project, task=task)


@bp.route('/projects/<int:project_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    if project.user_id != current_user.id and current_user not in project.assigned_users:
        flash("You don't have access to this project.", 'danger')
        return redirect(url_for('main.projects'))

    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('main.project_detail', project_id=project_id))


@bp.route('/projects/<int:project_id>/tasks/<int:task_id>/update_status', methods=['POST'])
@login_required
def update_task_status(project_id, task_id):
    project = Project.query.get_or_404(project_id)
    task = Task.query.get_or_404(task_id)
    if project.user_id != current_user.id and current_user not in project.assigned_users:
        flash("You don't have access to this project.", 'danger')
        return redirect(url_for('main.projects'))

    status = request.form.get('status')
    if status in ['To Do', 'In Progress', 'Done']:
        task.status = status
        db.session.commit()
        flash('Task status updated successfully!', 'success')
    else:
        flash('Invalid status.', 'danger')

    return redirect(url_for('main.project_detail', project_id=project_id))


@bp.route('/projects/<int:project_id>/users', methods=['GET', 'POST'])
@login_required
def project_users(project_id):
    project = Project.query.get_or_404(project_id)
    is_owner = project.user_id == current_user.id
    is_participant = current_user in project.users
    invitation = Invitation.query.filter_by(user_id=current_user.id, project_id=project_id).first()
    is_invited = invitation is not None

    if not (is_owner or is_participant or is_invited):
        flash("You don't have access to this project.", 'danger')
        return redirect(url_for('main.projects'))

    add_user_form = AddUserForm()
    if is_owner and add_user_form.validate_on_submit():
        user = User.query.filter_by(email=add_user_form.email.data).first()
        if user:
            if user not in project.users:
                invitation = Invitation(user_id=user.id, project_id=project.id)
                db.session.add(invitation)
                db.session.commit()
                flash('User invited to project!', 'success')
            else:
                flash('User is already a member of the project.', 'warning')
        else:
            flash('User not found.', 'danger')

    return render_template('project_users.html', project=project, add_user_form=add_user_form, is_owner=is_owner, is_participant=is_participant, is_invited=is_invited)


@bp.route('/inbox')
@login_required
def inbox():
    invitations = Invitation.query.filter_by(user_id=current_user.id, status='Pending').all()
    return render_template('inbox.html', invitations=invitations)


@bp.route('/inbox/<int:invitation_id>/accept', methods=['POST'])
@login_required
def accept_invitation(invitation_id):
    invitation = Invitation.query.get_or_404(invitation_id)
    if invitation.user_id != current_user.id:
        flash("You don't have permission to accept this invitation.", 'danger')
        return redirect(url_for('main.inbox'))

    invitation.status = 'Accepted'
    project = Project.query.get(invitation.project_id)
    project.users.append(current_user)
    db.session.delete(invitation)
    db.session.commit()
    flash('Invitation accepted!', 'success')
    return redirect(url_for('main.inbox'))


@bp.route('/inbox/<int:invitation_id>/decline', methods=['POST'])
@login_required
def decline_invitation(invitation_id):
    invitation = Invitation.query.get_or_404(invitation_id)
    if invitation.user_id != current_user.id:
        flash("You don't have permission to decline this invitation.", 'danger')
        return redirect(url_for('main.inbox'))

    invitation.status = 'Declined'
    db.session.delete(invitation)
    db.session.commit()
    flash('Invitation declined.', 'success')
    return redirect(url_for('main.inbox'))


@bp.route('/projects/<int:project_id>/invitations/<int:invitation_id>/cancel', methods=['POST'])
@login_required
def cancel_invitation(project_id, invitation_id):
    project = Project.query.get_or_404(project_id)
    invitation = Invitation.query.get_or_404(invitation_id)

    if project.user_id != current_user.id:
        flash("You don't have permission to cancel this invitation.", 'danger')
        return redirect(url_for('main.project_users', project_id=project_id))

    db.session.delete(invitation)
    db.session.commit()
    flash('Invitation canceled successfully!', 'success')
    return redirect(url_for('main.project_users', project_id=project_id))

@bp.route('/projects/<int:project_id>/users/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_user_from_project(project_id, user_id):
    project = Project.query.get_or_404(project_id)
    user = User.query.get_or_404(user_id)
    if project.user_id != current_user.id:
        flash("You don't have access to modify this project.", 'danger')
        return redirect(url_for('main.project_users', project_id=project_id))

    if user in project.users:
        project.users.remove(user)
        tasks = Task.query.filter_by(project_id=project_id, user_id=user_id).all()
        for task in tasks:
            task.user_id = None
        db.session.commit()
        flash('User removed from project and tasks updated!', 'success')
    else:
        flash('User is not a member of the project.', 'warning')

    return redirect(url_for('main.project_users', project_id=project_id))


@bp.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    total_projects = len(list(user.owned_projects)) + len(list(user.assigned_projects))
    owned_projects_count = len(list(user.owned_projects))
    assigned_projects_count = len(list(user.assigned_projects))  # Fetch all assigned projects
    assigned_tasks_count = len(list(user.assigned_tasks))

    user_projects = set(user.owned_projects).union(set(user.assigned_projects))
    current_user_projects = set(current_user.owned_projects).union(set(current_user.assigned_projects))

    mutual_projects = []
    if user != current_user:
        mutual_projects = list(user_projects.intersection(current_user_projects))

    return render_template('user_profile.html', user=user, total_projects=total_projects,
                           owned_projects_count=owned_projects_count, assigned_projects_count=assigned_projects_count,
                           assigned_tasks_count=assigned_tasks_count, mutual_projects=mutual_projects)


@bp.route('/user/<int:user_id>/tasks', methods=['GET'])
@login_required
def user_assigned_tasks(user_id):
    user = User.query.get_or_404(user_id)

    # Check if the current user is accessing their own tasks
    if current_user.id != user_id:
        flash("You don't have access to view this user's tasks.", 'danger')
        return redirect(url_for('main.user_profile', user_id=user_id))

    assigned_tasks = user.assigned_tasks

    return render_template('user_assigned_tasks.html', user=user, assigned_tasks=assigned_tasks)


@bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash("You don't have access to edit this project.", 'danger')
        return redirect(url_for('main.projects'))

    form = EditProjectForm(obj=project)
    if form.validate_on_submit():
        project.name = form.name.data
        project.description = form.description.data
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('main.project_detail', project_id=project_id))

    return render_template('edit_project.html', form=form, project=project)


@bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash("You don't have access to delete this project.", 'danger')
        return redirect(url_for('main.projects'))

    tasks = Task.query.filter_by(project_id=project_id).all()
    for task in tasks:
        db.session.delete(task)

    for user in project.users:
        project.users.remove(user)

    db.session.delete(project)
    db.session.commit()
    flash('Project and all related references deleted successfully!', 'success')
    return redirect(url_for('main.projects'))

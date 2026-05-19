from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q
from .models import Client, Project, Task, Notification, Report, Message, Team, UserProfile, ProjectFile, Feedback
from .forms import SignUpForm, ProjectForm, TaskForm, ReportForm, FeedbackForm, ClientProjectForm
from datetime import date
from django.contrib.auth.models import User
from django.template.loader import get_template, TemplateDoesNotExist
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json

@login_required
def dashboard(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'
    
    projects = Project.objects.all()
    tasks = Task.objects.all()
    
    if user_role == 'admin':
        pass
    elif user_role == 'project_manager':
        projects = projects.filter(manager=request.user)
        tasks = tasks.filter(project__manager=request.user)
    elif user_role == 'team_leader':
        projects = projects.filter(Q(manager=request.user) | Q(tasks__assigned_to=request.user)).distinct()
        tasks = tasks.filter(project__in=projects)
    elif user_role == 'team_member':
        tasks = tasks.filter(assigned_to=request.user)
        projects = projects.filter(tasks__assigned_to=request.user).distinct()
    elif user_role == 'client':
        projects = projects.filter(client__email=request.user.email)
        tasks = tasks.filter(project__client__email=request.user.email)

    total_projects = projects.count()
    completed_projects = projects.filter(status='completed').count()
    ongoing_projects = projects.filter(status='ongoing').count()
    pending_projects = projects.filter(status='planning').count()
    
    total_tasks = tasks.count()
    done_tasks = tasks.filter(status='done').count()
    pending_tasks = total_tasks - done_tasks
    task_completion_rate = int((done_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    recent_projects = projects.order_by('-created_at')[:5]
    upcoming_deadlines = tasks.filter(status__in=['todo', 'in_progress'], deadline__gte=date.today()).order_by('deadline')[:5]
    
    context = {
        'user_role': user_role,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'ongoing_projects': ongoing_projects,
        'pending_projects': pending_projects,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'pending_tasks': pending_tasks,
        'task_completion_rate': task_completion_rate,
        'recent_projects': recent_projects,
        'upcoming_deadlines': upcoming_deadlines,
    }
    
    template_name = f'projects/dashboards/{user_role}.html'
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        template_name = 'projects/dashboard.html'
    
    return render(request, template_name, context)

# Client Views
from django.http import JsonResponse

@login_required
def client_list(request):
    clients = Client.objects.annotate(
        project_count=Count('projects'),
        active_project_count=Count('projects', filter=Q(projects__status__in=['planning', 'ongoing', 'on_hold']))
    )
    return render(request, 'projects/client_list.html', {'clients': clients})

@login_required
def client_detail_json(request, pk):
    client = get_object_or_404(Client, pk=pk)
    
    # Projects
    projects = []
    for p in client.projects.all():
        projects.append({
            'id': p.id,
            'title': p.title,
            'status': p.get_status_display(),
            'status_code': p.status,
            'deadline': p.deadline.strftime('%b %d, %Y') if p.deadline else 'N/A',
            'progress': p.get_progress()
        })
        
    # Files
    files = []
    for p in client.projects.all():
        for f in p.files.all():
            files.append({
                'name': f.name,
                'url': f.file.url if f.file else '',
                'project_title': p.title,
                'uploaded_at': f.uploaded_at.strftime('%b %d, %Y %I:%M %p') if f.uploaded_at else 'N/A'
            })
            
    # Messages / Communication History
    client_users = User.objects.filter(email=client.email)
    messages = []
    
    project_ids = client.projects.values_list('id', flat=True)
    q_filter = Q(project_id__in=project_ids)
    if client_users.exists():
        q_filter |= Q(sender__in=client_users) | Q(receiver__in=client_users)
        
    db_messages = Message.objects.filter(q_filter).order_by('-created_at')[:15]
    for m in db_messages:
        messages.append({
            'sender': m.sender.get_full_name() or m.sender.username,
            'receiver': (m.receiver.get_full_name() or m.receiver.username) if m.receiver else 'All',
            'project_title': m.project.title if m.project else 'General',
            'content': m.content,
            'created_at': m.created_at.strftime('%b %d, %Y %I:%M %p') if m.created_at else 'N/A'
        })

    # Invoices Tab Data
    invoices = []
    for inv in client.invoices.all():
        invoices.append({
            'invoice_number': inv.invoice_number,
            'amount': float(inv.amount),
            'status': inv.get_status_display(),
            'status_code': inv.status,
            'due_date': inv.due_date.strftime('%b %d, %Y')
        })

    # Meeting Notes Tab Data
    meeting_notes = []
    for note in client.meeting_notes.all().order_by('-created_at'):
        meeting_notes.append({
            'title': note.title,
            'summary': note.summary,
            'discussion_points': note.discussion_points,
            'next_actions': note.next_actions,
            'created_at': note.created_at.strftime('%b %d, %Y')
        })

    # Activity Logs Tab Data
    activity_logs = []
    for log in client.activity_logs.all().order_by('-created_at'):
        activity_logs.append({
            'activity_type': log.activity_type,
            'description': log.description,
            'created_at': log.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    # Permissions Tab Data
    perms = {
        'can_upload': client.permissions.can_upload if hasattr(client, 'permissions') else True,
        'can_comment': client.permissions.can_comment if hasattr(client, 'permissions') else True,
        'can_edit': client.permissions.can_edit if hasattr(client, 'permissions') else False,
    }
        
    data = {
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'phone': client.phone or 'N/A',
        'address': client.address or 'No company info',
        'client_id': client.client_id or f'CLT-2026-{100 + client.id}',
        'revenue_paid': float(client.revenue_paid),
        'revenue_pending': float(client.revenue_pending),
        'priority': client.get_priority_display(),
        'priority_code': client.priority,
        'satisfaction': float(client.satisfaction),
        'notes': client.notes or '',
        'projects': projects,
        'files': files,
        'messages': messages,
        'invoices': invoices,
        'meeting_notes': meeting_notes,
        'activity_logs': activity_logs,
        'permissions': perms,
    }
    return JsonResponse(data)

@login_required
def client_projects(request):
    projects = Project.objects.filter(client__email=request.user.email)
    return render(request, 'projects/client_projects.html', {'projects': projects})

@login_required
def client_reports(request):
    reports = Report.objects.filter(project__client__email=request.user.email).order_by('-created_at')
    return render(request, 'projects/client_reports.html', {'reports': reports})

@login_required
def client_files(request):
    files = ProjectFile.objects.filter(project__client__email=request.user.email).order_by('-uploaded_at')
    projects = Project.objects.filter(client__email=request.user.email)
    return render(request, 'projects/client_files.html', {'files': files, 'projects': projects})

@login_required
def client_feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.client = request.user
            feedback.save()
            return redirect('client_feedback')
    else:
        form = FeedbackForm()
        form.fields['project'].queryset = Project.objects.filter(client__email=request.user.email)
    feedbacks = Feedback.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'projects/client_feedback.html', {'form': form, 'feedbacks': feedbacks})

# Project Views
@login_required
def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    clients_all = Client.objects.all()
    
    # Calculate overview stats
    completed_count = projects.filter(status='completed').count()
    active_count = projects.filter(status='ongoing').count()
    
    today = date.today()
    delayed_count = projects.filter(deadline__lt=today).exclude(status='completed').count()
    
    return render(request, 'projects/project_list.html', {
        'projects': projects, 
        'clients_all': clients_all,
        'completed_count': completed_count,
        'active_count': active_count,
        'delayed_count': delayed_count,
        'today': today
    })

@login_required
def project_detail_json(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    # Tasks
    tasks = []
    for t in project.tasks.all():
        tasks.append({
            'title': t.title,
            'status': t.get_status_display(),
            'status_code': t.status,
            'priority': t.get_priority_display(),
            'priority_code': t.priority,
            'assignee': t.assigned_to.get_full_name() or t.assigned_to.username if t.assigned_to else 'Unassigned',
            'deadline': t.deadline.strftime('%b %d, %Y') if t.deadline else 'N/A'
        })
        
    # Files
    files = []
    for f in project.files.all():
        files.append({
            'name': f.name,
            'url': f.file.url if f.file else '',
            'uploaded_at': f.uploaded_at.strftime('%b %d, %Y') if f.uploaded_at else 'N/A'
        })
        
    data = {
        'id': project.id,
        'title': project.title,
        'description': project.description or 'No description provided.',
        'client_name': project.client.name,
        'client_email': project.client.email,
        'manager': project.manager.get_full_name() or project.manager.username if project.manager else 'Unassigned',
        'status': project.get_status_display(),
        'status_code': project.status,
        'priority': project.get_priority_display(),
        'priority_code': project.priority,
        'deadline': project.deadline.strftime('%b %d, %Y') if project.deadline else 'N/A',
        'progress': project.get_progress(),
        'tasks': tasks,
        'files': files
    }
    return JsonResponse(data)

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.all()
    return render(request, 'projects/project_detail.html', {'project': project, 'tasks': tasks})

@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.manager = request.user
            project.save()
            return redirect('dashboard')
    else:
        form = ProjectForm()
    return render(request, 'projects/create_project.html', {'form': form})

@login_required
def client_form(request):
    if request.method == 'POST':
        form = ClientProjectForm(request.POST, request.FILES)
        if form.is_valid():
            # Create or get the client
            client, created = Client.objects.get_or_create(
                email=form.cleaned_data['email'],
                defaults={
                    'name': form.cleaned_data['client_name'],
                    'phone': form.cleaned_data['phone'],
                }
            )
            
            # Create the project
            project = Project(
                title=form.cleaned_data['project_title'],
                description='',
                client=client,
                manager=request.user,
                deadline=form.cleaned_data['deadline']
            )
            project.save()
            
            # Handle file upload if provided
            if form.cleaned_data.get('file_upload'):
                project_file = ProjectFile(
                    project=project,
                    name=form.cleaned_data['file_upload'].name,
                    file=form.cleaned_data['file_upload']
                )
                project_file.save()
            
            return redirect('dashboard')
    else:
        form = ClientProjectForm()
    return render(request, 'projects/client_form.html', {'form': form})

# Task Views
@login_required
def task_list(request):
    tasks = Task.objects.all()
    projects_all = Project.objects.all()
    return render(request, 'projects/task_list.html', {'tasks': tasks, 'projects_all': projects_all})

@login_required
def task_board(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
    else:
        tasks = Task.objects.all()
        projects = Project.objects.all()

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('task_board')
    else:
        form = TaskForm()
        if user_role == 'project_manager':
            form.fields['project'].queryset = Project.objects.filter(manager=request.user)

    today = date.today()
    return render(request, 'projects/task_board.html', {'tasks': tasks, 'projects': projects, 'form': form, 'today': today})

# Report Views
@login_required
def team_reports(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        reports = Report.objects.filter(project__manager=request.user).order_by('-created_at')
    else:
        reports = Report.objects.all().order_by('-created_at')
    return render(request, 'projects/team_reports.html', {'reports': reports})

@login_required
def approve_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if report.project.manager == request.user or request.user.profile.role == 'admin':
        report.status = 'approved'
        report.save()
        Notification.objects.create(user=report.submitted_by, message=f"Your report '{report.title}' has been approved.")
    return redirect('team_reports')

# Calendar and Messages
@login_required
def calendar_view(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
    else:
        projects = Project.objects.all()
        tasks = Task.objects.all()
    return render(request, 'projects/calendar.html', {'projects': projects, 'tasks': tasks})

@login_required
def messages_view(request):
    from django.db.models import Max
    user_role = request.user.profile.role
    
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
    elif user_role == 'client':
        projects = Project.objects.filter(client__email=request.user.email)
    else:
        projects = Project.objects.all()
        
    all_users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    managers = []
    team_members = []
    clients = []
    
    for u in all_users:
        role = u.profile.role if hasattr(u, 'profile') else 'team_member'
        unread_count = Message.objects.filter(sender=u, receiver=request.user, is_read=False).count()
        latest_msg = Message.objects.filter(
            Q(sender=u, receiver=request.user) | Q(sender=request.user, receiver=u)
        ).aggregate(latest=Max('created_at'))['latest']
        
        user_info = {
            'id': u.id,
            'username': u.username,
            'name': u.get_full_name() or u.username,
            'unread': unread_count,
            'latest_time': latest_msg,
            'online': (u.id % 2 == 0 or u.id % 3 == 0)
        }
        
        if role == 'project_manager':
            managers.append(user_info)
        elif role in ['team_leader', 'team_member', 'admin']:
            team_members.append(user_info)
        elif role == 'client':
            clients.append(user_info)
            
    # Sort timezone safely to avoid TypeError when comparing offset-naive and offset-aware datetimes
    sort_key = lambda x: (1, x['latest_time']) if x['latest_time'] is not None else (0, datetime.min)
    managers.sort(key=sort_key, reverse=True)
    team_members.sort(key=sort_key, reverse=True)
    clients.sort(key=sort_key, reverse=True)

    return render(request, 'projects/messages.html', {
        'projects': projects,
        'managers': managers,
        'team': team_members,
        'clients': clients
    })

@login_required
def messages_view(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        managed_projects = Project.objects.filter(manager=request.user)
        messages = Message.objects.filter(Q(project__in=managed_projects) | Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')
    else:
        messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')

    if request.method == 'POST':
        content = request.POST.get('content')
        project_id = request.POST.get('project')
        if content:
            project = Project.objects.get(pk=project_id) if project_id else None
            Message.objects.create(sender=request.user, content=content, project=project)
            return redirect('messages')
    projects = Project.objects.filter(manager=request.user) if user_role == 'project_manager' else Project.objects.all()
    return render(request, 'projects/messages.html', {'messages': messages, 'projects': projects})

@login_required
@login_required
def teams(request):
    if request.user.profile.role != 'project_manager':
        return render(request, 'projects/teams.html', {'error': 'Access denied'})

    # Get all team leaders (users with team_leader role)
    team_leaders = User.objects.filter(profile__role='team_leader')
    
    # Get ALL projects (both client-uploaded and PM-created)
    # This allows PMs to assign any project to team leaders
    # Exclude projects that have already been assigned (pending or accepted)
    assigned_project_ids = ProjectAssignment.objects.filter(
        status__in=['pending', 'accepted']
    ).values_list('project_id', flat=True)
    projects = Project.objects.exclude(id__in=assigned_project_ids).order_by('-deadline')
    
    # Get assignments for each team leader
    team_leader_data = []
    for leader in team_leaders:
        assignments = ProjectAssignment.objects.filter(team_leader=leader)
        pending = assignments.filter(status='pending').count()
        accepted = assignments.filter(status='accepted').count()
        rejected = assignments.filter(status='rejected').count()
        
        team_leader_data.append({
            'user': leader,
            'pending_count': pending,
            'accepted_count': accepted,
            'rejected_count': rejected,
            'assignments': assignments,
            'assignment_count': assignments.count(),
        })
    
    teams = Team.objects.filter(project_manager=request.user).prefetch_related('leaders', 'members')

    context = {
        'teams': teams,
        'team_leader_data': team_leader_data,
        'projects': projects,
    }
    return render(request, 'projects/teams.html', context)

# Auth Views
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('client_form')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form, 'hide_sidebar': True})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form, 'hide_sidebar': True})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def edit_feedback(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk, client=request.user)
    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            form.save()
            return redirect('client_feedback')
    else:
        form = FeedbackForm(instance=feedback)
        form.fields['project'].queryset = Project.objects.filter(client__email=request.user.email)
    return render(request, 'projects/edit_feedback.html', {'form': form})
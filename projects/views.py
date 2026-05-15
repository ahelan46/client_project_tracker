from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Count, Q
from .models import Client, Project, Task, Notification
from datetime import date

@login_required
def dashboard(request):
    total_projects = Project.objects.count()
    completed_projects = Project.objects.filter(status='completed').count()
    ongoing_projects = Project.objects.filter(status='ongoing').count()
    pending_projects = Project.objects.filter(status='pending').count()
    
    total_tasks = Task.objects.count()
    done_tasks = Task.objects.filter(status='done').count()
    
    recent_projects = Project.objects.order_by('-created_at')[:5]
    upcoming_deadlines = Task.objects.filter(status__in=['todo', 'in_progress'], deadline__gte=date.today()).order_by('deadline')[:5]
    
    context = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'ongoing_projects': ongoing_projects,
        'pending_projects': pending_projects,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'recent_projects': recent_projects,
        'upcoming_deadlines': upcoming_deadlines,
    }
    return render(request, 'projects/dashboard.html', context)

# Client Views
@login_required
def client_list(request):
    clients = Client.objects.annotate(project_count=Count('projects'))
    return render(request, 'projects/client_list.html', {'clients': clients})

# Project Views
@login_required
def project_list(request):
    projects = Project.objects.all()
    clients_all = Client.objects.all()
    return render(request, 'projects/project_list.html', {
        'projects': projects,
        'clients_all': clients_all
    })

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.all()
    return render(request, 'projects/project_detail.html', {'project': project, 'tasks': tasks})

# Task Views
@login_required
def task_list(request):
    tasks = Task.objects.all()
    projects_all = Project.objects.all()
    return render(request, 'projects/task_list.html', {
        'tasks': tasks,
        'projects_all': projects_all
    })

# Auth Views
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
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

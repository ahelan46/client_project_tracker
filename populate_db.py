import os
import django
import random
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tracker.settings')
django.setup()

from django.contrib.auth.models import User
from projects.models import Client, Project, Task

def populate():
    # Clear existing data
    Task.objects.all().delete()
    Project.objects.all().delete()
    Client.objects.all().delete()
    
    # Create superuser if it doesn't exist
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Superuser created: admin/admin123")

    # Create clients
    clients_data = [
        {'name': 'Carlos Mendez', 'address': 'Apex Solutions', 'email': 'carlos@apexsolutions.mx', 'phone': '+52 55-5555-0127'},
        {'name': 'Michael Thornton', 'address': 'Horizon Tech', 'email': 'michael@horizontech.io', 'phone': '+1 415-555-0101'},
        {'name': 'Priya Patel', 'address': 'Elevate Brands', 'email': 'priya@elevatebrands.com', 'phone': '+1 312-555-0182'},
        {'name': 'David Okafor', 'address': 'GreenLeaf Co.', 'email': 'david@greenleafco.com', 'phone': '+1 718-555-0143'},
        {'name': 'Sophie Müller', 'address': 'Nordik Design', 'email': 'sophie@nordikdesign.eu', 'phone': '+49 30-555-0165'},
    ]

    clients = []
    for data in clients_data:
        client = Client.objects.create(**data)
        clients.append(client)
    
    print(f"Created {len(clients)} clients.")

    admin_user = User.objects.get(username='admin')

    # Create projects matching the UI photos
    projects_data = [
        {'title': 'Nordik Product Catalog', 'client': clients[4], 'status': 'completed', 'priority': 'medium', 'deadline': date(2026, 5, 10)},
        {'title': 'Brand Identity Redesign', 'client': clients[1], 'status': 'ongoing', 'priority': 'high', 'deadline': date(2026, 6, 5)},
        {'title': 'E-commerce Platform v2', 'client': clients[2], 'status': 'ongoing', 'priority': 'urgent', 'deadline': date(2026, 5, 25)},
        {'title': 'Marketing Campaign Q3', 'client': clients[2], 'status': 'on_hold', 'priority': 'medium', 'deadline': date(2026, 7, 14)},
        {'title': 'Sustainability Report 2025', 'client': clients[3], 'status': 'planning', 'priority': 'medium', 'deadline': date(2026, 8, 22)},
        {'title': 'Mobile App Redesign', 'client': clients[1], 'status': 'planning', 'priority': 'high', 'deadline': date(2026, 9, 15)},
    ]

    for data in projects_data:
        project = Project.objects.create(
            title=data['title'],
            client=data['client'],
            status=data['status'],
            priority=data['priority'],
            deadline=data['deadline'],
            manager=admin_user,
            description=f"Standard management for {data['title']} project."
        )
        
        # Add some tasks to each project to show progress
        statuses = ['done', 'in_progress', 'todo']
        priorities = ['low', 'medium', 'high', 'urgent']
        
        for i in range(random.randint(3, 8)):
            Task.objects.create(
                project=project,
                title=f"Task {i+1} for {project.title}",
                assigned_to=admin_user,
                status=random.choice(statuses),
                priority=random.choice(priorities),
                deadline=project.deadline - timedelta(days=random.randint(0, 10))
            )
    
    print("Populated projects and tasks.")

if __name__ == '__main__':
    populate()

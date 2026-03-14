from functools import wraps
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError

from .models import User, Student, StudentSession, SESSION_CHOICES
from .forms import LoginForm, StudentForm, AddSessionForm, UserCreateForm


# ─── Decorators ──────────────────────────────────────────────────────────────

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Recommender helper ───────────────────────────────────────────────────────

def get_recommendations(session_type):
    attended_L1 = set(StudentSession.objects.filter(session_type='L1').values_list('student_id', flat=True))
    attended_L2 = set(StudentSession.objects.filter(session_type='L2').values_list('student_id', flat=True))
    attended_L3 = set(StudentSession.objects.filter(session_type='L3').values_list('student_id', flat=True))
    attended_FOLK = set(StudentSession.objects.filter(session_type='FOLK').values_list('student_id', flat=True))
    all_ids = set(Student.objects.values_list('pk', flat=True))

    if session_type == 'L1':
        eligible = all_ids - attended_L1
        tier1 = eligible & attended_L3
        tier2 = (eligible & attended_L2) - tier1
        tier3 = eligible - tier1 - tier2
        labels = [
            'Priority 1 — Attended Level 3 (not Level 1)',
            'Priority 2 — Attended Level 2 (not Level 1)',
            'Priority 3 — New Students',
        ]

    elif session_type == 'L2':
        eligible = all_ids - attended_L2
        tier1 = eligible & attended_L3
        tier2 = (eligible & attended_L1) - tier1
        tier3 = eligible - tier1 - tier2
        labels = [
            'Priority 1 — Attended Level 3 (not Level 2)',
            'Priority 2 — Attended Level 1 (not Level 2)',
            'Priority 3 — New Students',
        ]

    elif session_type == 'L3':
        eligible = all_ids - attended_L3
        tier1 = eligible & attended_L2
        tier2 = (eligible & attended_L1) - tier1
        tier3 = eligible - tier1 - tier2
        labels = [
            'Priority 1 — Attended Level 2 (not Level 3)',
            'Priority 2 — Attended Level 1 (not Level 3)',
            'Priority 3 — New Students',
        ]

    elif session_type == 'FOLK':
        eligible = {
            sid for sid in (all_ids - attended_FOLK)
            if sum([sid in attended_L1, sid in attended_L2, sid in attended_L3]) >= 2
        }
        tier1, tier2, tier3 = eligible, set(), set()
        labels = ['Eligible — Attended 2+ Vedic Science Sessions', '', '']

    else:
        return []

    groups = []
    for ids, label in zip([tier1, tier2, tier3], labels):
        if ids and label:
            qs = Student.objects.filter(pk__in=ids).order_by('name')
            groups.append((label, qs))
    return groups


# ─── Auth Views ───────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, phone_number=form.cleaned_data['phone_number'])
        if user:
            login(request, user)
            return redirect('dashboard')
        form.add_error('phone_number', 'No account found with this phone number.')
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Main Views ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    query = request.GET.get('q', '').strip()
    students = Student.objects.select_related('created_by').prefetch_related('sessions')
    if query:
        students = students.filter(name__icontains=query)
    students = students.order_by('-created_at')
    return render(request, 'core/dashboard.html', {'students': students, 'query': query})


@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.created_by = request.user
            student.save()
            sessions = form.cleaned_data.get('sessions', [])
            session_date = form.cleaned_data.get('session_date') or date.today()
            for s_type in sessions:
                StudentSession.objects.get_or_create(
                    student=student,
                    session_type=s_type,
                    defaults={'date_attended': session_date, 'added_by': request.user}
                )
            messages.success(request, f'Student "{student.name}" added successfully.')
            return redirect('student_profile', pk=student.pk)
    else:
        form = StudentForm()
    return render(request, 'core/add_student.html', {'form': form, 'session_choices': SESSION_CHOICES})


@login_required
def student_profile(request, pk):
    student = get_object_or_404(Student, pk=pk)
    sessions = student.sessions.select_related('added_by').order_by('date_attended')
    add_form = AddSessionForm()
    return render(request, 'core/student_profile.html', {
        'student': student,
        'sessions': sessions,
        'add_form': add_form,
        'session_choices': SESSION_CHOICES,
    })


@login_required
def add_session(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = AddSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.student = student
            session.added_by = request.user
            try:
                session.save()
                messages.success(request, f'Session added for {student.name}.')
            except IntegrityError:
                messages.error(request, 'This session type is already recorded for this student.')
    return redirect('student_profile', pk=pk)


@login_required
def recommender(request):
    session_type = request.GET.get('session', '')
    groups = []
    valid_types = dict(SESSION_CHOICES)
    if session_type in valid_types:
        groups = get_recommendations(session_type)
    return render(request, 'core/recommender.html', {
        'session_choices': SESSION_CHOICES,
        'selected_session': session_type,
        'groups': groups,
    })


# ─── Admin-only User Management ───────────────────────────────────────────────

@admin_required
def user_list(request):
    users = User.objects.all().order_by('name')
    return render(request, 'core/user_management.html', {'users': users, 'add_mode': False})


@admin_required
def user_add(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone).exists():
            form.add_error('phone_number', 'A user with this phone number already exists.')
        else:
            User.objects.create_user(
                phone_number=phone,
                name=form.cleaned_data['name']
            )
            messages.success(request, 'New user created successfully.')
            return redirect('user_list')
    users = User.objects.all().order_by('name')
    return render(request, 'core/user_management.html', {'users': users, 'form': form, 'add_mode': True})

from functools import wraps
from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import (
    User, Student, StudentSession, College, CallStatus,
    FolkSession, FolkAttendance, NewFolkFollowup,
    SESSION_CHOICES, RATING_CHOICES, RATING_SORT,
    CALL_STATUS_CHOICES, FOLLOWUP_STATUS_CHOICES, GENDER_CHOICES,
    higher_rating,
)
from .forms import LoginForm, StudentForm, AddSessionForm, UserCreateForm


# ─── Decorators ──────────────────────────────────────────────────────────────

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _student_scope(request, pk):
    """Return student by pk — admin sees all, users see own + legacy (null creator)."""
    if request.user.is_admin:
        return get_object_or_404(Student, pk=pk)
    return get_object_or_404(Student, Q(created_by=request.user) | Q(created_by=None), pk=pk)


def get_recommendations(session_type, user):
    user_student_ids = set(
        Student.objects.filter(created_by=user).values_list('pk', flat=True)
    )
    attended_L1 = set(StudentSession.objects.filter(session_type='L1', student_id__in=user_student_ids).values_list('student_id', flat=True))
    attended_L2 = set(StudentSession.objects.filter(session_type='L2', student_id__in=user_student_ids).values_list('student_id', flat=True))
    attended_L3 = set(StudentSession.objects.filter(session_type='L3', student_id__in=user_student_ids).values_list('student_id', flat=True))
    all_ids = user_student_ids

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
        non_female_ids = set(
            Student.objects.filter(pk__in=all_ids).exclude(gender='F').values_list('pk', flat=True)
        )
        eligible = {
            sid for sid in non_female_ids
            if sum([sid in attended_L1, sid in attended_L2, sid in attended_L3]) >= 2
        }
        tier1, tier2, tier3 = eligible, set(), set()
        labels = ['Eligible — Attended 2+ Vedic Science Sessions (Male)', '', '']
    else:
        return []

    CALL_ORDER   = {'': 0, 'NC': 1, 'NA': 2, 'NW': 3, 'C': 4}
    RATING_ORDER = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, '': 3}

    groups = []
    for ids, label in zip([tier1, tier2, tier3], labels):
        if ids and label:
            call_status_map = {
                cs.student_id: cs.status
                for cs in CallStatus.objects.filter(student_id__in=ids, session_type=session_type)
            }
            students_list = list(Student.objects.filter(pk__in=ids).prefetch_related('sessions'))
            for s in students_list:
                s.call_status = call_status_map.get(s.pk, '')
            students_list.sort(key=lambda s: (
                CALL_ORDER.get(s.call_status, 0),
                RATING_ORDER.get(s.rating, 3),
                s.name,
            ))
            groups.append((label, students_list))
    return groups


def _apply_sessions(student, session_types, session_date, added_by):
    for s_type in session_types:
        if s_type != 'FOLK':
            if not StudentSession.objects.filter(student=student, session_type=s_type).exists():
                StudentSession.objects.create(student=student, session_type=s_type, date_attended=session_date, added_by=added_by)
        else:
            StudentSession.objects.create(student=student, session_type='FOLK', date_attended=session_date, added_by=added_by)


# ─── Auth ─────────────────────────────────────────────────────────────────────

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


# ─── Main App ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    query = request.GET.get('q', '').strip()
    students = (Student.objects.filter(created_by=request.user).prefetch_related('sessions').order_by('-created_at'))
    if query:
        students = students.filter(name__icontains=query)
    return render(request, 'core/dashboard.html', {'students': students, 'query': query})


@login_required
def add_student(request):
    colleges = College.objects.order_by('name')
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            phone        = form.cleaned_data.get('phone_number', '').strip()
            sessions     = form.cleaned_data.get('sessions', [])
            session_date = form.cleaned_data.get('session_date') or date.today()
            new_rating   = request.POST.get('rating', 'MEDIUM')
            new_name     = form.cleaned_data['name']
            new_occ      = form.cleaned_data.get('occupation', '')
            new_notes    = form.cleaned_data.get('notes', '')
            new_gender   = request.POST.get('gender', '')
            college_id   = request.POST.get('college') or None

            existing = None
            if phone:
                existing = Student.objects.filter(phone_number=phone, created_by=request.user).first()

            if existing:
                existing.name   = new_name
                existing.rating = higher_rating(existing.rating, new_rating)
                if new_occ:    existing.occupation = new_occ
                if new_notes:  existing.notes      = new_notes
                if new_gender: existing.gender     = new_gender
                if college_id:
                    try:    existing.college_id = int(college_id)
                    except: pass
                existing.save()
                _apply_sessions(existing, sessions, session_date, request.user)
                messages.success(request, f'"{existing.name}" already exists — updated.')
                return redirect('student_profile', pk=existing.pk)

            student = form.save(commit=False)
            student.created_by = request.user
            student.rating     = new_rating
            student.gender     = new_gender
            if college_id:
                try:    student.college_id = int(college_id)
                except: pass
            student.save()
            _apply_sessions(student, sessions, session_date, request.user)
            messages.success(request, f'Student "{student.name}" added.')
            return redirect('student_profile', pk=student.pk)
    else:
        form = StudentForm()
    return render(request, 'core/add_student.html', {
        'form': form, 'session_choices': SESSION_CHOICES,
        'ratings': RATING_CHOICES, 'gender_choices': GENDER_CHOICES, 'colleges': colleges,
    })


@login_required
def student_profile(request, pk):
    student  = _student_scope(request, pk)
    sessions = student.sessions.select_related('added_by').order_by('date_attended')
    colleges = College.objects.order_by('name')
    return render(request, 'core/student_profile.html', {
        'student': student, 'sessions': sessions,
        'add_form': AddSessionForm(), 'session_choices': SESSION_CHOICES,
        'ratings': RATING_CHOICES, 'gender_choices': GENDER_CHOICES, 'colleges': colleges,
    })


@login_required
def edit_student(request, pk):
    student = _student_scope(request, pk)
    if request.method == 'POST':
        student.name         = request.POST.get('name', student.name).strip() or student.name
        student.phone_number = request.POST.get('phone_number', '').strip()
        student.occupation   = request.POST.get('occupation', '').strip()
        student.notes        = request.POST.get('notes', '').strip()
        new_rating = request.POST.get('rating', student.rating)
        if new_rating in dict(RATING_CHOICES):
            student.rating = new_rating
        new_gender = request.POST.get('gender', '')
        if new_gender in dict(GENDER_CHOICES) or new_gender == '':
            student.gender = new_gender
        college_id = request.POST.get('college') or None
        if college_id:
            try:    student.college_id = int(college_id)
            except: pass
        else:
            student.college = None
        student.save()
        messages.success(request, 'Student details updated.')
    return redirect('student_profile', pk=pk)


@login_required
def add_session(request, pk):
    student = _student_scope(request, pk)
    if request.method == 'POST':
        form = AddSessionForm(request.POST)
        if form.is_valid():
            session_type = form.cleaned_data['session_type']
            if session_type != 'FOLK' and StudentSession.objects.filter(student=student, session_type=session_type).exists():
                messages.error(request, f'"{student.name}" already attended {dict(SESSION_CHOICES)[session_type]}.')
                return redirect('student_profile', pk=pk)
            s = form.save(commit=False)
            s.student  = student
            s.added_by = request.user
            s.save()
            messages.success(request, f'Session added for {student.name}.')
    return redirect('student_profile', pk=pk)


@login_required
def delete_student(request, pk):
    student = _student_scope(request, pk)
    if request.method == 'POST':
        name = student.name
        student.delete()
        messages.success(request, f'Student "{name}" deleted.')
    return redirect('dashboard')


@login_required
def recommender(request):
    session_type = request.GET.get('session', '')
    groups = get_recommendations(session_type, request.user) if session_type in dict(SESSION_CHOICES) else []
    return render(request, 'core/recommender.html', {
        'session_choices': SESSION_CHOICES, 'selected_session': session_type,
        'groups': groups, 'call_status_choices': CALL_STATUS_CHOICES,
    })


@login_required
def update_call_status(request):
    if request.method == 'POST':
        student_id   = request.POST.get('student_id')
        session_type = request.POST.get('session_type')
        status       = request.POST.get('status', '')
        student = get_object_or_404(Student, pk=student_id)
        if status in dict(CALL_STATUS_CHOICES) or status == '':
            if status == '':
                CallStatus.objects.filter(student=student, session_type=session_type).delete()
            else:
                CallStatus.objects.update_or_create(
                    student=student, session_type=session_type,
                    defaults={'status': status, 'updated_by': request.user}
                )
            return JsonResponse({'ok': True, 'status': status})
    return JsonResponse({'ok': False}, status=400)


# ─── Admin User Management ────────────────────────────────────────────────────

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
            User.objects.create_user(phone_number=phone, name=form.cleaned_data['name'])
            messages.success(request, 'New user created.')
            return redirect('user_list')
    users = User.objects.all().order_by('name')
    return render(request, 'core/user_management.html', {'users': users, 'form': form, 'add_mode': True})


# ─── FOLK Section ─────────────────────────────────────────────────────────────

@login_required
def folk_home(request):
    return render(request, 'core/folk/home.html', {
        'sessions_count': FolkSession.objects.count(),
        'followup_count': NewFolkFollowup.objects.filter(status='PENDING').count(),
        'colleges_count': College.objects.count(),
    })


@login_required
def folk_sessions_list(request):
    sessions = FolkSession.objects.prefetch_related('attendances').order_by('-date')
    return render(request, 'core/folk/sessions_list.html', {'sessions': sessions})


@login_required
def folk_session_new(request):
    if request.method == 'POST':
        date_str = request.POST.get('date', '')
        notes    = request.POST.get('notes', '').strip()
        try:
            session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Invalid date.')
            return redirect('folk_sessions_list')
        session = FolkSession.objects.create(date=session_date, notes=notes, created_by=request.user)
        messages.success(request, 'Session created.')
        return redirect('folk_session_detail', pk=session.pk)
    return render(request, 'core/folk/session_form.html', {'today': date.today().isoformat()})


@login_required
def folk_session_detail(request, pk):
    session      = get_object_or_404(FolkSession, pk=pk)
    attendances  = session.attendances.select_related('student').order_by('student__name')
    attended_ids = set(attendances.values_list('student_id', flat=True))

    # Eligible: male/ungendered, 2+ VSC sessions, not yet attending this session
    vsc_counts = (
        StudentSession.objects
        .filter(session_type__in=['L1', 'L2', 'L3'])
        .values('student_id')
        .annotate(cnt=Count('session_type', distinct=True))
    )
    eligible_ids = {row['student_id'] for row in vsc_counts if row['cnt'] >= 2}
    eligible_students = (
        Student.objects.filter(pk__in=eligible_ids)
        .exclude(gender='F').exclude(pk__in=attended_ids).order_by('name')
    )

    if request.method == 'POST':
        action     = request.POST.get('action')
        student_id = request.POST.get('student_id')

        if action == 'add' and student_id:
            student = get_object_or_404(Student, pk=student_id)
            rounds  = int(request.POST.get('chanting_rounds', 0) or 0)
            is_new  = request.POST.get('is_new_folk') == '1'
            FolkAttendance.objects.get_or_create(
                session=session, student=student,
                defaults={'chanting_rounds': rounds, 'is_new_folk': is_new}
            )
            if is_new:
                NewFolkFollowup.objects.get_or_create(
                    student=student,
                    defaults={'created_by': request.user, 'status': 'PENDING'}
                )
            messages.success(request, f'{student.name} marked as attended.')
            return redirect('folk_session_detail', pk=pk)

        elif action == 'update_rounds' and student_id:
            rounds = int(request.POST.get('chanting_rounds', 0) or 0)
            FolkAttendance.objects.filter(session=session, student_id=student_id).update(chanting_rounds=rounds)
            return redirect('folk_session_detail', pk=pk)

        elif action == 'remove' and student_id:
            FolkAttendance.objects.filter(session=session, student_id=student_id).delete()
            return redirect('folk_session_detail', pk=pk)

    return render(request, 'core/folk/session_detail.html', {
        'session': session, 'attendances': attendances, 'eligible_students': eligible_students,
    })


@login_required
def folk_session_delete(request, pk):
    session = get_object_or_404(FolkSession, pk=pk)
    if request.method == 'POST':
        session.delete()
        messages.success(request, 'Session deleted.')
    return redirect('folk_sessions_list')


@login_required
def folk_followup_list(request):
    if request.method == 'POST':
        followup = get_object_or_404(NewFolkFollowup, pk=request.POST.get('followup_id'))
        new_status = request.POST.get('status', '')
        notes      = request.POST.get('notes', '').strip()
        if new_status in dict(FOLLOWUP_STATUS_CHOICES):
            followup.status = new_status
        if notes:
            followup.notes = notes
        followup.save()
        messages.success(request, 'Follow-up updated.')
        return redirect('folk_followup_list')

    followups = NewFolkFollowup.objects.select_related('student').order_by('status', '-updated_at')
    return render(request, 'core/folk/followup_list.html', {
        'followups': followups,
        'followup_status_choices': FOLLOWUP_STATUS_CHOICES,
    })


@login_required
def colleges_list(request):
    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        if name:
            College.objects.create(name=name, location=location, created_by=request.user)
            messages.success(request, f'College "{name}" added.')
        return redirect('colleges_list')

    colleges = College.objects.annotate(student_count=Count('students')).order_by('name')
    return render(request, 'core/folk/colleges_list.html', {'colleges': colleges})


@login_required
def college_detail(request, pk):
    college  = get_object_or_404(College, pk=pk)
    students = Student.objects.filter(college=college).prefetch_related('sessions').order_by('name')
    return render(request, 'core/folk/college_detail.html', {'college': college, 'students': students})


@login_required
def college_delete(request, pk):
    college = get_object_or_404(College, pk=pk)
    if request.method == 'POST':
        name = college.name
        college.delete()
        messages.success(request, f'College "{name}" deleted.')
    return redirect('colleges_list')

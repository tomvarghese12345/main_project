from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from .forms import FacultyForm, ClassroomForm, SubjectForm, AssignmentForm
from .models import Faculty, Classroom, Subject, Assignment, TimeSlot, TimetableEntry, DAYS_OF_WEEK
from itertools import cycle
from collections import defaultdict
from django.db import transaction
import random


# LOGIN / LOGOUT
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid credentials")
        return redirect("login")
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# 🧩 TIMETABLE GENERATOR FUNCTION (Optimized + Subject + Lab Rules v2)

def generate_timetable():
    # --- Reset previous timetable ---
    TimetableEntry.objects.all().delete()

    # --- Ensure TimeSlots exist (6 periods/day) ---
    PERIODS_PER_DAY = 6
    if not TimeSlot.objects.exists():
        for day, _ in DAYS_OF_WEEK:
            for p in range(1, PERIODS_PER_DAY + 1):
                TimeSlot.objects.create(day=day, period=p)

    slots = list(TimeSlot.objects.all().order_by("day", "period"))
    slot_map = {(s.day, s.period): s for s in slots}
    days = [d for d, _ in DAYS_OF_WEEK]

    assignments = list(Assignment.objects.select_related("faculty", "subject", "classroom"))
    if not assignments:
        print("⚠️ No assignments found.")
        return []

    # --- Constraints (as you specified) ---
    LAB_BLOCK_HOURS = 3
    LAB_BLOCKS_PER_WEEK = 2         # 2 * 3 = 6 hrs/week per lab assignment
    LECTURE_TARGET_WEEK = 4        # target hours/week for lecture
    LECTURE_RELAX_MAX = 5          # allowed after relaxed second pass
    LECTURE_MAX_PER_DAY = 2
    FACULTY_MAX_PER_DAY = 4

    # --- Trackers ---
    faculty_busy = set()            # (faculty_id, day, period)
    classroom_busy = set()          # (classroom_id, day, period)
    faculty_day_load = defaultdict(int)           # (faculty_id, day) -> hours
    subject_day_load = defaultdict(int)           # (subject_id, classroom_id, day) -> hours
    subject_week_load = defaultdict(int)          # (subject_id, classroom_id) -> hours
    timetable_entries = []

    # --- Session requirements ---
    # store remaining hours needed per assignment
    reqs = {}
    for a in assignments:
        if a.class_type.lower() == "lab":
            reqs[a.id] = LAB_BLOCKS_PER_WEEK * LAB_BLOCK_HOURS  # 6
        else:
            reqs[a.id] = LECTURE_TARGET_WEEK  # 4 initially

    # Helper: safe place one lecture hour
    def place_lecture_one(a, preferred_days=None):
        """Try to place one lecture hour for assignment a. Return True if placed."""
        faculty_id = a.faculty.id
        classroom_id = a.classroom.id
        # days order: prefer days passed, else random order with low subject/week load
        day_order = preferred_days or sorted(days, key=lambda d: subject_week_load[(a.subject.id, a.classroom.id)])
        random.shuffle(day_order)  # randomize within that priority
        for day in day_order:
            if subject_day_load[(a.subject.id, a.classroom.id, day)] >= LECTURE_MAX_PER_DAY:
                continue
            if faculty_day_load[(faculty_id, day)] >= FACULTY_MAX_PER_DAY:
                continue
            # try periods 1..6 (lectures can be anywhere)
            period_order = list(range(1, PERIODS_PER_DAY + 1))
            random.shuffle(period_order)
            for p in period_order:
                if (faculty_id, day, p) in faculty_busy or (classroom_id, day, p) in classroom_busy:
                    continue
                # place
                slot = slot_map[(day, p)]
                timetable_entries.append(TimetableEntry(
                    faculty=a.faculty, subject=a.subject,
                    classroom=a.classroom, time_slot=slot,
                    class_type=a.class_type
                ))
                faculty_busy.add((faculty_id, day, p))
                classroom_busy.add((classroom_id, day, p))
                faculty_day_load[(faculty_id, day)] += 1
                subject_day_load[(a.subject.id, a.classroom.id, day)] += 1
                subject_week_load[(a.subject.id, a.classroom.id)] += 1
                reqs[a.id] -= 1
                return True
        return False

    # --- Phase A: Place labs first (only blocks starting at 1 or 4) ---
    lab_start_positions = [1, 4]  # first 3 periods (1-3) or last 3 (4-6)
    lab_assignments = [a for a in assignments if a.class_type.lower() == "lab"]
    # Shuffle labs to spread load
    random.shuffle(lab_assignments)
    for a in lab_assignments:
        sessions_placed = 0
        # prefer days with smallest faculty load to reduce overload
        day_order = sorted(days, key=lambda d: faculty_day_load[(a.faculty.id, d)])
        for day in day_order:
            if sessions_placed >= LAB_BLOCKS_PER_WEEK:
                break
            for start in lab_start_positions:
                # check block fits
                block = [(day, start + i) for i in range(LAB_BLOCK_HOURS)]
                # if any period beyond day, skip (shouldn't happen with start positions chosen)
                if any(p > PERIODS_PER_DAY for _, p in block):
                    continue
                # conflicts?
                if any((a.faculty.id, d, p) in faculty_busy or (a.classroom.id, d, p) in classroom_busy for d, p in block):
                    continue
                # faculty daily limit
                if faculty_day_load[(a.faculty.id, day)] + LAB_BLOCK_HOURS > FACULTY_MAX_PER_DAY:
                    continue
                # place block
                for d, p in block:
                    slot = slot_map[(d, p)]
                    timetable_entries.append(TimetableEntry(
                        faculty=a.faculty, subject=a.subject,
                        classroom=a.classroom, time_slot=slot,
                        class_type=a.class_type
                    ))
                    faculty_busy.add((a.faculty.id, d, p))
                    classroom_busy.add((a.classroom.id, d, p))
                    faculty_day_load[(a.faculty.id, d)] += 1
                    subject_day_load[(a.subject.id, a.classroom.id, d)] += 1
                    subject_week_load[(a.subject.id, a.classroom.id)] += 1
                reqs[a.id] -= LAB_BLOCK_HOURS
                sessions_placed += 1
                break
        # if not all sessions placed, continue; fallback will handle later

    # --- Phase B: Balanced lecture placement in rounds (fairness) ---
    lecture_assignments = [a for a in assignments if a.class_type.lower() != "lab"]
    # create order of assignments grouped by faculty to promote fairness
    # We'll run rounds: in each round attempt to place one hour for each assignment that still needs hours
    # This ensures everyone participates
    # Prepare round list
    round_list = lecture_assignments.copy()
    # Shuffle initial order
    random.shuffle(round_list)

    # Run rounds until no assignment can place in a round or all reqs for lectures are 0
    while True:
        progressed = False
        random.shuffle(round_list)
        for a in round_list:
            if reqs.get(a.id, 0) <= 0:
                continue
            # try to place one hour (prefer days with lowest subject_day_load)
            pref_days = sorted(days, key=lambda d: subject_day_load[(a.subject.id, a.classroom.id, d)])
            placed = place_lecture_one(a, preferred_days=pref_days)
            if placed:
                progressed = True
        # stop when no progress or all lecture reqs satisfied
        remaining_lectures = sum(reqs[a.id] for a in lecture_assignments)
        if not progressed or remaining_lectures <= 0:
            break

    # --- Phase C: Relaxation pass to reach up to LECTURE_RELAX_MAX if possible ---
    if any(reqs[a.id] > 0 for a in lecture_assignments):
        # try to add up to one extra hour per assignment up to LECTURE_RELAX_MAX
        for a in lecture_assignments:
            current = subject_week_load[(a.subject.id, a.classroom.id)]
            extra_allowed = LECTURE_RELAX_MAX - current
            while extra_allowed > 0 and reqs[a.id] > 0:
                # attempt to place one ignoring subject_day limit but still respecting faculty daily limit
                placed = False
                for day in days:
                    if faculty_day_load[(a.faculty.id, day)] >= FACULTY_MAX_PER_DAY:
                        continue
                    for p in range(1, PERIODS_PER_DAY + 1):
                        if (a.faculty.id, day, p) in faculty_busy or (a.classroom.id, day, p) in classroom_busy:
                            continue
                        # place
                        slot = slot_map[(day, p)]
                        timetable_entries.append(TimetableEntry(
                            faculty=a.faculty, subject=a.subject,
                            classroom=a.classroom, time_slot=slot, class_type=a.class_type
                        ))
                        faculty_busy.add((a.faculty.id, day, p))
                        classroom_busy.add((a.classroom.id, day, p))
                        faculty_day_load[(a.faculty.id, day)] += 1
                        subject_day_load[(a.subject.id, a.classroom.id, day)] += 1
                        subject_week_load[(a.subject.id, a.classroom.id)] += 1
                        reqs[a.id] -= 1
                        extra_allowed -= 1
                        placed = True
                        break
                    if placed:
                        break
                if not placed:
                    break  # can't place extra for this assignment

    # --- Phase D: Fallback forced placement but DO NOT exceed FACULTY_MAX_PER_DAY ---
    # Try to place any remaining hours into any free slots that don't break faculty daily max.
    remaining_total = sum(v for v in reqs.values() if v > 0)
    if remaining_total > 0:
        # flatten slots in order
        for a in assignments:
            while reqs[a.id] > 0:
                placed = False
                # choose slots with faculty_day_load < FACULTY_MAX_PER_DAY first
                for slot in slots:
                    d, p = slot.day, slot.period
                    if faculty_day_load[(a.faculty.id, d)] >= FACULTY_MAX_PER_DAY:
                        continue
                    if (a.faculty.id, d, p) in faculty_busy or (a.classroom.id, d, p) in classroom_busy:
                        continue
                    # for labs, ensure we can place 3 consecutive (but here it's fallback; try only if possible)
                    if a.class_type.lower() == "lab":
                        # try start positions 1 and 4 for blocks containing this slot
                        possible_blocks = []
                        for start in [1, 4]:
                            block = [(d, start + i) for i in range(LAB_BLOCK_HOURS)]
                            if any(p2 > PERIODS_PER_DAY for _, p2 in block):
                                continue
                            possible_blocks.append(block)
                        block_assigned = False
                        for block in possible_blocks:
                            if any((a.faculty.id, dd, pp) in faculty_busy or (a.classroom.id, dd, pp) in classroom_busy for dd, pp in block):
                                continue
                            if faculty_day_load[(a.faculty.id, d)] + LAB_BLOCK_HOURS > FACULTY_MAX_PER_DAY:
                                continue
                            for dd, pp in block:
                                slot2 = slot_map[(dd, pp)]
                                timetable_entries.append(TimetableEntry(
                                    faculty=a.faculty, subject=a.subject,
                                    classroom=a.classroom, time_slot=slot2, class_type=a.class_type
                                ))
                                faculty_busy.add((a.faculty.id, dd, pp))
                                classroom_busy.add((a.classroom.id, dd, pp))
                                faculty_day_load[(a.faculty.id, dd)] += 1
                                subject_day_load[(a.subject.id, a.classroom.id, dd)] += 1
                                subject_week_load[(a.subject.id, a.classroom.id)] += 1
                            reqs[a.id] -= LAB_BLOCK_HOURS
                            block_assigned = True
                            placed = True
                            break
                        if block_assigned:
                            continue
                        else:
                            # can't place a lab block here, break out to next assignment
                            break
                    else:
                        # lecture fallback single-slot placement
                        slot2 = slot_map[(d, p)]
                        timetable_entries.append(TimetableEntry(
                            faculty=a.faculty, subject=a.subject,
                            classroom=a.classroom, time_slot=slot2, class_type=a.class_type
                        ))
                        faculty_busy.add((a.faculty.id, d, p))
                        classroom_busy.add((a.classroom.id, d, p))
                        faculty_day_load[(a.faculty.id, d)] += 1
                        subject_day_load[(a.subject.id, a.classroom.id, d)] += 1
                        subject_week_load[(a.subject.id, a.classroom.id)] += 1
                        reqs[a.id] -= 1
                        placed = True
                        break
                if not placed:
                    # cannot place this assignment without violating faculty daily limit — stop trying
                    break

    # --- Persist all created entries ---
    if timetable_entries:
        with transaction.atomic():
            TimetableEntry.objects.bulk_create(timetable_entries)

    # --- Report remaining (if any) ---
    not_fully_scheduled = []
    for a in assignments:
        if reqs.get(a.id, 0) > 0:
            not_fully_scheduled.append((
                a.faculty.name,
                a.subject.subject_name,
                a.classroom.semester,
                reqs[a.id]
            ))

    if not_fully_scheduled:
        print("⚠️ The following assignments could not be fully scheduled (remaining hours):")
        for fac_name, subj_name, cls_sem, rem in not_fully_scheduled:
            print(f"  - {fac_name} :: {subj_name} ({cls_sem}) — remaining {rem} hrs")
    else:
        print(f"✅ Timetable generated: {len(timetable_entries)} entries; all assignments participated.")

    return not_fully_scheduled


# 🧩 DELETE FACULTY FUNCTION
@login_required
def delete_faculty(request, faculty_id):
    faculty = get_object_or_404(Faculty, id=faculty_id)
    faculty.delete()
    messages.success(request, f"Faculty '{faculty.name}' deleted successfully.")
    return redirect('dashboard')

@login_required
def delete_classroom(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    classroom.delete()
    messages.success(request, f"Classroom '{classroom.semester}' deleted successfully.")
    return redirect('dashboard')


@login_required
def delete_subject(request, course_id):
    subject = get_object_or_404(Subject, id=course_id)
    subject_name = subject.subject_name 
    subject.delete()
    messages.success(request, f"Subject '{subject.subject_name}' deleted successfully.")
    return redirect('dashboard')

@login_required
def delete_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    assignment.delete()
    messages.success(request, f"Assignment '{assignment.subject.subject_name}' for {assignment.faculty.name} deleted successfully.")
    return redirect('dashboard')


# 🧹 DELETE TIMETABLE FUNCTION
@login_required
def delete_timetable(request):
    if request.method == "POST":
        TimetableEntry.objects.all().delete()
        messages.success(request, "✅ All timetable entries deleted successfully.")
        return redirect("dashboard")




# 🧩 DASHBOARD
@login_required
def dashboard(request):
    faculties = Faculty.objects.all()
    classrooms = Classroom.objects.all()
    subjects = Subject.objects.all()
    assignments = Assignment.objects.select_related("faculty", "subject", "classroom")
    timetable = TimetableEntry.objects.select_related("faculty", "subject", "classroom", "time_slot")

    DAYS_OF_WEEK = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
    ]
    period_range = range(1, 7)  # 6 periods per day

    if request.method == "POST":
        if 'add_faculty' in request.POST:
            form = FacultyForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('dashboard')

        elif 'add_classroom' in request.POST:
            cform = ClassroomForm(request.POST)
            if cform.is_valid():
                cform.save()
                return redirect('dashboard')

        elif 'add_subject' in request.POST:
            sform = SubjectForm(request.POST)
            if sform.is_valid():
                sform.save()
                return redirect('dashboard')

        elif 'assign_subject' in request.POST:
            aform = AssignmentForm(request.POST)
            if aform.is_valid():
                aform.save()
                return redirect('dashboard')

        elif 'generate_timetable' in request.POST:
            generate_timetable()
            return redirect('dashboard')

    context = {
        "form": FacultyForm(),
        "faculties": faculties,
        "cform": ClassroomForm(),
        "classrooms": classrooms,
        "sform": SubjectForm(),
        "subjects": subjects,
        "aform": AssignmentForm(),
        "assignments": assignments,
        "timetable": timetable,
        "DAYS_OF_WEEK": DAYS_OF_WEEK,
        "period_range": period_range,
    }

    return render(request, "accounts/dashboard.html", context)

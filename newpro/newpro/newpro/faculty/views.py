from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from accounts.models import Faculty, TimetableEntry, Classroom
from .models import CourseDiary, LeaveApplication
from .forms import CourseDiaryForm, LeaveApplicationForm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from django.utils import timezone
import io


# ================= LOGIN ================= #

def faculty_login(request):
    if request.method == 'POST':
        fid = request.POST.get('faculty_id')
        password = request.POST.get('password')

        try:
            faculty = Faculty.objects.get(faculty_id=fid)
            if faculty.password == password:
                request.session['faculty_id'] = faculty.id
                return redirect('faculty_dashboard')
            else:
                messages.error(request, "Invalid password.")
        except Faculty.DoesNotExist:
            messages.error(request, "Invalid Faculty ID.")

    return render(request, 'faculty/login.html')


def faculty_logout(request):
    request.session.flush()
    return redirect('faculty_login')


# ================= DASHBOARD ================= #

def faculty_dashboard(request):
    faculty_id = request.session.get('faculty_id')
    if not faculty_id:
        return redirect('faculty_login')

    faculty = Faculty.objects.get(id=faculty_id)

    timetable = TimetableEntry.objects.select_related(
        'subject', 'classroom', 'faculty', 'time_slot'
    )

    faculty_entries = timetable.filter(faculty=faculty)
    faculty_map = {(e.time_slot.day, e.time_slot.period): e for e in faculty_entries}

    classrooms = Classroom.objects.all()
    class_maps = {}
    for classroom in classrooms:
        class_entries = timetable.filter(classroom=classroom)
        class_maps[classroom] = {(e.time_slot.day, e.time_slot.period): e for e in class_entries}

    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6]

    return render(request, 'faculty/dashboard.html', {
        'faculty': faculty,
        'faculty_map': faculty_map,
        'class_maps': class_maps,
        'days': days,
        'day_labels': day_labels,
        'periods': periods,
    })


# ================= COURSE DIARY ================= #

def course_diary(request):
    faculty_id = request.session.get('faculty_id')
    if not faculty_id:
        return redirect('faculty_login')

    faculty = Faculty.objects.get(id=faculty_id)

    if request.method == "POST":
        form = CourseDiaryForm(request.POST)
        if form.is_valid():
            diary = form.save(commit=False)
            diary.faculty = faculty
            diary.save()
            return redirect('course_diary')
    else:
        form = CourseDiaryForm()

    diaries = CourseDiary.objects.filter(faculty=faculty).order_by('-date')

    return render(request, 'faculty/course_diary.html', {
        'form': form,
        'diaries': diaries
    })


def course_diary_pdf(request):
    faculty_id = request.session.get('faculty_id')
    if not faculty_id:
        return redirect('faculty_login')

    faculty = Faculty.objects.get(id=faculty_id)
    diaries = CourseDiary.objects.filter(faculty=faculty).order_by('date')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"{faculty.name} - Course Diary", styles['Title']))
    elements.append(Spacer(1, 20))

    data = [["S.No", "Date", "Hour", "Module", "Topic", "Summary"]]

    for i, d in enumerate(diaries, 1):
        data.append([
            i,
            d.date.strftime("%d-%m-%Y"),
            d.get_hour_display(),
            d.module,
            d.topic,
            d.summary
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


# ================= TIMETABLE PDF ================= #




def download_pdf(request, type, obj_id):

    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    day_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6]

    if type == "faculty":
        faculty = get_object_or_404(Faculty, id=obj_id)

        timetable = TimetableEntry.objects.filter(
            faculty=faculty
        ).select_related('subject', 'classroom', 'time_slot')

        table_data = []

        for day, label in zip(days, day_labels):
            row = [label]

            for period in periods:
                entry = next(
                    (e for e in timetable
                     if e.time_slot.day == day and e.time_slot.period == period),
                    None
                )

                if entry:
                    row.append(f"{entry.subject.subject_name}\n{entry.classroom.semester}")
                else:
                    row.append("—")

            table_data.append(row)

        template_path = 'faculty/faculty_timetable_pdf.html'
        filename = f"{faculty.name}_timetable.pdf"

        context = {
            'object': faculty,
            'table_data': table_data,
            'periods': periods
        }

    elif type == "class":
        classroom = get_object_or_404(Classroom, id=obj_id)

        timetable = TimetableEntry.objects.filter(
            classroom=classroom
        ).select_related('subject', 'faculty', 'time_slot')

        table_data = []

        for day, label in zip(days, day_labels):
            row = [label]

            for period in periods:
                entry = next(
                    (e for e in timetable
                     if e.time_slot.day == day and e.time_slot.period == period),
                    None
                )

                if entry:
                    row.append(f"{entry.subject.subject_name}\n{entry.faculty.name}")
                else:
                    row.append("—")

            table_data.append(row)

        template_path = 'faculty/class_timetable_pdf.html'
        filename = f"{classroom.semester}_timetable.pdf"

        context = {
            'object': classroom,
            'table_data': table_data,
            'periods': periods
        }

    else:
        return HttpResponse("Invalid type")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF")

    return response


# ================= LEAVE APPLICATION (FACULTY) ================= #


def apply_leave(request):
    faculty_id = request.session.get('faculty_id')
    if not faculty_id:
        return redirect('faculty_login')

    faculty = Faculty.objects.get(id=faculty_id)
    generated_letter = None
    from_date = None
    to_date = None
    topic = None

    if request.method == "POST":
        form = LeaveApplicationForm(request.POST)
        if form.is_valid():
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            topic = form.cleaned_data['topic']

            current_date = timezone.now().date()

            generated_letter = (
                "Subject: Leave Application\n\n"
                "Respected Sir/Madam,\n\n"
                f"I, {faculty.name}, would like to request leave from "
                f"{from_date.strftime('%d-%m-%Y')} to {to_date.strftime('%d-%m-%Y')} "
                f"due to {topic}.\n\n"
                "Kindly grant me leave for the above-mentioned period.\n\n"
                "Thanking You,\n"
                f"{faculty.name}\n"
                f"Date: {current_date.strftime('%d-%m-%Y')}\n"
            )
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = LeaveApplicationForm()

    context = {
        'faculty': faculty,
        'form': form,
        'generated_letter': generated_letter,
        'from_date': from_date,
        'to_date': to_date,
        'topic': topic,
    }
    return render(request, 'faculty/apply_leave.html', context)


def submit_leave(request):
    faculty_id = request.session.get('faculty_id')
    if not faculty_id:
        return redirect('faculty_login')

    faculty = Faculty.objects.get(id=faculty_id)

    if request.method != "POST":
        messages.error(request, "Invalid request method for submitting leave.")
        return redirect('apply_leave')

    from_date = request.POST.get('from_date')
    to_date = request.POST.get('to_date')
    topic = request.POST.get('topic')
    generated_letter = request.POST.get('generated_letter')

    if not all([from_date, to_date, topic, generated_letter]):
        messages.error(request, "Missing data. Please generate the leave letter again.")
        return redirect('apply_leave')

    try:
        from datetime import datetime

        from_date_parsed = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date_parsed = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Invalid dates received. Please try again.")
        return redirect('apply_leave')

    LeaveApplication.objects.create(
        faculty=faculty,
        from_date=from_date_parsed,
        to_date=to_date_parsed,
        topic=topic,
        generated_letter=generated_letter,
    )

    messages.success(request, "Leave application submitted to admin with status Pending.")
    return redirect('apply_leave')


# ================= LEAVE APPLICATION (ADMIN SIDE) ================= #


def leave_applications_admin(request):
    applications = LeaveApplication.objects.select_related('faculty').order_by('-applied_on')
    return render(request, 'faculty/leave_list_admin.html', {'applications': applications})


def leave_application_detail_admin(request, pk):
    application = get_object_or_404(LeaveApplication, pk=pk)

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'approve':
            application.status = LeaveApplication.STATUS_APPROVED
            application.save(update_fields=['status'])
            messages.success(request, "Leave application approved.")
            return redirect('leave_applications_admin')
        elif action == 'reject':
            application.status = LeaveApplication.STATUS_REJECTED
            application.save(update_fields=['status'])
            messages.success(request, "Leave application rejected.")
            return redirect('leave_applications_admin')

    return render(request, 'faculty/leave_detail_admin.html', {'application': application})
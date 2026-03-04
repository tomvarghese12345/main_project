from django import forms
from .models import Faculty, Classroom, Subject, Assignment

class FacultyForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = Faculty
        fields = ['faculty_id', 'name', 'phone', 'password']
        widgets = {'password': forms.PasswordInput()}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['semester']


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['course_id', 'subject_name']


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['faculty', 'subject', 'classroom', 'class_type']

from django import forms
from .models import CourseDiary


class CourseDiaryForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    hour = forms.ChoiceField(
        choices=CourseDiary.HOUR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    module = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    topic = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    summary = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    class Meta:
        model = CourseDiary
        fields = ['date', 'hour', 'module', 'topic', 'summary']


class LeaveApplicationForm(forms.Form):
    from_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'From date',
            }
        ),
        label='From Date',
    )

    to_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'To date',
            }
        ),
        label='To Date',
    )

    topic = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for leave / topic',
            }
        ),
        label='Leave Topic',
        max_length=500,
    )
from django import forms
from .models import Student, StudentSession, SESSION_CHOICES


class LoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your phone number',
            'class': 'form-control spiritual-input',
            'autocomplete': 'off',
        })
    )


class StudentForm(forms.ModelForm):
    sessions = forms.MultipleChoiceField(
        choices=SESSION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Sessions Attended'
    )
    session_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control spiritual-input'}),
        label='Date Attended (for selected sessions)'
    )

    class Meta:
        model = Student
        fields = ['name', 'phone_number', 'occupation', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control spiritual-input', 'placeholder': 'Full name *'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control spiritual-input', 'placeholder': 'Phone number'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control spiritual-input', 'placeholder': 'Occupation'}),
            'notes': forms.Textarea(attrs={'class': 'form-control spiritual-input', 'rows': 3, 'placeholder': 'Notes'}),
        }


class AddSessionForm(forms.ModelForm):
    class Meta:
        model = StudentSession
        fields = ['session_type', 'date_attended']
        widgets = {
            'session_type': forms.Select(attrs={'class': 'form-select spiritual-input'}),
            'date_attended': forms.DateInput(attrs={'type': 'date', 'class': 'form-control spiritual-input'}),
        }


class UserCreateForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control spiritual-input', 'placeholder': 'Full name'})
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control spiritual-input', 'placeholder': 'Phone number'})
    )

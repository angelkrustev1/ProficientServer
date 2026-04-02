from django import forms
from .models import AppUser


class AppUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = AppUser
        fields = ("email", "profile_picture")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and AppUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        # Optionally enforce safe defaults (even if someone tampers with POST data)
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user

class AppUserChangeForm(forms.ModelForm):
    class Meta:
        model = AppUser
        fields = "__all__"

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Manga, SubAdminTask, Task, Author, Editor, Category

class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

class SubAdminForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    tasks = forms.ModelMultipleChoiceField(
        queryset=Task.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_subadmin = True
        if commit:
            user.save()
            # Handle tasks
            for task in self.cleaned_data['tasks']:
                SubAdminTask.objects.get_or_create(user=user, task=task)
        return user

class MangaForm(forms.ModelForm):
    author_name = forms.CharField(label="Auteur", max_length=100)
    editor_name = forms.CharField(label="Éditeur", max_length=100)
    category_name = forms.CharField(label="Catégorie", max_length=100)
    
    field_order = ['title', 'author_name', 'editor_name', 'category_name', 'price', 'rental_deposit', 'stock', 'image', 'description', 'is_popular']

    class Meta:
        model = Manga
        exclude = ['image_url', 'author', 'editor', 'category', 'consultations', 'sales']
        widgets = {
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'rental_deposit': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if getattr(self.instance, 'author', None):
                self.fields['author_name'].initial = self.instance.author.name
            if getattr(self.instance, 'editor', None):
                self.fields['editor_name'].initial = self.instance.editor.name
            if getattr(self.instance, 'category', None):
                self.fields['category_name'].initial = self.instance.category.name
        else:
            # Pour les nouveaux mangas, on vide la valeur par défaut pour forcer la saisie manuelle
            self.initial['rental_deposit'] = None

    def save(self, commit=True):
        manga = super().save(commit=False)
        
        # Automatically get or create the related objects
        author_name = self.cleaned_data.get('author_name')
        if author_name:
            author, _ = Author.objects.get_or_create(name=author_name.strip())
            manga.author = author
            
        editor_name = self.cleaned_data.get('editor_name')
        if editor_name:
            editor, _ = Editor.objects.get_or_create(name=editor_name.strip())
            manga.editor = editor
            
        category_name = self.cleaned_data.get('category_name')
        if category_name:
            category, _ = Category.objects.get_or_create(name=category_name.strip())
            manga.category = category
            
        if commit:
            manga.save()
        return manga

class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('card_number', 'card_expiry', 'card_cvv')
        widgets = {
            'card_number': forms.TextInput(attrs={'placeholder': '1234567812345678', 'maxlength': '16'}),
            'card_expiry': forms.TextInput(attrs={'placeholder': 'MM/YY', 'maxlength': '5'}),
            'card_cvv': forms.TextInput(attrs={'placeholder': '123', 'maxlength': '3'}),
        }

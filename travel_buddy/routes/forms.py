from django import forms
from django.core.exceptions import ValidationError
from .models import Route, Tag

class RouteForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Теги'
    )
    image = forms.ImageField(required=False, label='Главное изображение')
    
    class Meta:
        model = Route
        fields = ['title', 'description', 'countries', 'cities', 'start_city', 'end_city', 'waypoints', 'start_date', 'end_date', 'budget', 'max_spots', 'tags', 'image']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    # Валидация названия
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) < 3:
            raise ValidationError('Название маршрута должно содержать минимум 3 символа')
        return title.strip()
    
    # Валидация описания
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description.strip()) < 10:
            raise ValidationError('Описание должно содержать минимум 10 символов')
        return description
    
    # Валидация стран
    def clean_countries(self):
        countries = self.cleaned_data.get('countries')
        if not countries or len(countries.strip()) < 2:
            raise ValidationError('Укажите страну (минимум 2 символа)')
        return countries.strip()
    
    # Валидация бюджета
    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None and budget < 0:
            raise ValidationError('Бюджет не может быть отрицательным')
        return budget
    
    # Валидация дат
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('Дата окончания не может быть раньше даты начала')
        
        # Проверка, что дата окончания не в прошлом (опционально)
        # from datetime import date
        # if end_date and end_date < date.today():
        #     raise ValidationError('Дата окончания не может быть в прошлом')
        
        return cleaned_data
class CommentForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Напишите комментарий...'}), label='')
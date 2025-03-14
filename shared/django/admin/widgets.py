"""Custom admin widgets."""

from django import forms


class QuestionSelectWidget(forms.Select):
    """
    Custom select widget for questions that adds data attributes 
    for input_type and has_custom_input for each option.
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """
        Add data-input-type and data-has-custom attributes to each option.
        
        Args:
            name: The name of the select field
            value: The value of the option
            label: The label of the option
            selected: Whether the option is selected
            index: The index of the option
            subindex: The subindex of the option
            attrs: Additional attributes
        
        Returns:
            Dict with option data including custom attributes
        """
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        if value and str(value) != '':
            try:
                # В Django 3.0+ значения в ModelChoiceField обертываются в специальный класс
                # ModelChoiceIteratorValue, поэтому нам нужно получить фактическое значение
                question_id = value.value if hasattr(value, 'value') else value
                
                # Получаем объект вопроса
                from app.models import Question
                question = Question.objects.filter(pk=question_id).first()
                
                if question:
                    # Добавляем data-атрибуты
                    option['attrs']['data-input-type'] = question.input_type
                    
                    # Проверяем, есть ли у вопроса опции с пользовательским вводом
                    has_custom = question.options.filter(has_custom_input=True).exists()
                    option['attrs']['data-has-custom'] = 'true' if has_custom else 'false'
            except Exception as e:
                # Логируем ошибку, но не ломаем работу приложения
                print(f"Error in QuestionSelectWidget.create_option: {e}")
        
        return option

from django.contrib.admin import SimpleListFilter
from django.db.models import Q


def create_question_filter(question):
    """
    Фабрика, создающая класс фильтра (SimpleListFilter) для данного вопроса.
    Поддерживает все типы вопросов (текстовые, с одиночным и множественным выбором).
    """
    # Определяем заголовок фильтра - используем более короткое поле, если доступно
    filter_title = question.field_type.title
    
    class DynamicQuestionFilter(SimpleListFilter):
        title = filter_title  # Как будет называться фильтр в админке
        parameter_name = f"question_{question.pk}"  # Ключ фильтра в GET-параметрах
        
        def lookups(self, request, model_admin):
            """
            Возвращает список (value, verbose_name) для выпадающего списка.
            В зависимости от типа вопроса, возвращает либо уникальные текстовые ответы,
            либо варианты ответов из связанной модели AnswerOption.
            """
            lookups_list = []
            
            # В зависимости от типа вопроса, генерируем разные варианты для фильтра
            if question.input_type == 'text':
                # Для текстовых вопросов собираем уникальные ответы
                distinct_answers = model_admin.get_queryset(request).filter(
                    responses__question=question
                ).values_list(
                    'responses__text_answer', flat=True
                ).distinct().order_by('responses__text_answer')
                
                # Превратим их в список кортежей (value, label)
                for ans in distinct_answers:
                    if ans:  # пропустим пустые ответы
                        # Префикс 'text:' нужен для различения текстовых ответов от ID вариантов
                        lookups_list.append((f"text:{ans}", ans[:50]))  # обрезаем label, если слишком длинный
            
            elif question.input_type in ['single_choice', 'multiple_choice']:
                # Для вопросов с выбором вариантов, используем предопределенные варианты
                options = question.options.all().order_by('order', 'text')
                
                for option in options:
                    # Префикс 'option:' нужен для различения ID вариантов от текстовых ответов
                    lookups_list.append((f"option:{option.id}", option.text))
            
            return lookups_list

        def queryset(self, request, queryset):
            # Вместо self.value() берём список значений:
            values = request.GET.getlist(self.parameter_name)
            if not values:
                return queryset

            # Допустим, хотим сделать «ИЛИ»-логику (OR),
            # чтобы попадали записи, удовлетворя хотя бы одному из выбранных значений.
            from django.db.models import Q
            q_filter = Q()

            for val in values:
                if val.startswith('text:'):
                    # Текстовый ответ
                    text_value = val[5:]
                    q_filter |= Q(
                        responses__question=question,
                        responses__text_answer=text_value
                    )
                elif val.startswith('option:'):
                    # Выбранный вариант
                    try:
                        option_id = int(val[7:])
                        q_filter |= Q(
                            responses__question=question,
                            responses__selected_options__id=option_id
                        )
                    except ValueError:
                        pass

            print(queryset, queryset.query)
            return queryset.filter(q_filter).distinct()

    return DynamicQuestionFilter

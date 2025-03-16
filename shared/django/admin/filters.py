from django.contrib.admin import SimpleListFilter
from django.db.models import Q


def create_question_filters(question):
    """
    Возвращает список фильтров для данного вопроса:
    1) Главный фильтр со всеми вариантами (DynamicQuestionFilter).
    2) Дополнительные фильтры (OptionFamilyFilter) — по одному на каждый root-вариант,
       у которого есть дочерние варианты.
    """
    filters = []

    # 1) Всегда добавляем один «главный» фильтр
    filters.append(create_dynamic_question_filter(question))

    # 2) Если вопрос - single/multiple choice, добавляем отдельные фильтры для root-опций с детьми
    if question.input_type in ["single_choice", "multiple_choice"]:
        root_options = question.options.filter(parent__isnull=True).order_by("order", "text")
        for root_option in root_options:
            if root_option.get_descendants().exists():
                # Создаём отдельный фильтр только если есть дочерние варианты
                filters.append(create_option_family_filter(question, root_option))

    return filters


def create_dynamic_question_filter(question):
    """
    Главный фильтр, показывающий все варианты (root + потомки) в одном списке.
    """
    filter_title = question.field_type.title

    class DynamicQuestionFilter(SimpleListFilter):
        title = filter_title
        parameter_name = f"question_{question.pk}"

        def lookups(self, request, model_admin):
            lookups_list = []

            if question.input_type == 'text':
                distinct_answers = model_admin.get_queryset(request).filter(
                    responses__question=question
                ).values_list('responses__text_answer', flat=True).distinct().order_by('responses__text_answer')

                for ans in distinct_answers:
                    if ans:
                        lookups_list.append((f"text:{ans}", ans[:50]))

            elif question.input_type in ['single_choice', 'multiple_choice']:
                root_options = question.options.filter(parent__isnull=True).order_by('order', 'text')
                for root_op in root_options:
                    # Если у корневого варианта есть дети – не включаем его в главный фильтр
                    if root_op.get_descendants().exists():
                        continue
                    else:
                        lookups_list.append((f"option:{root_op.id}", root_op.text))
                    # Можно добавить и те дочерние варианты, если нужно, но обычно они будут доступны через отдельный фильтр.
            return lookups_list

        def queryset(self, request, queryset):
            values = request.GET.getlist(self.parameter_name)
            if not values:
                return queryset

            q_filter = Q()

            for val in values:
                if val.startswith("text:"):
                    text_value = val[5:]
                    q_filter |= Q(responses__question=question, responses__text_answer=text_value)

                elif val.startswith("option:"):
                    try:
                        option_id = int(val[7:])
                        option_q = Q(responses__question=question, responses__selected_options__id=option_id)

                        # Учитываем и потомков
                        from app.models import AnswerOption
                        try:
                            op = AnswerOption.objects.get(pk=option_id)
                            if op.get_descendant_count() > 0:
                                desc_ids = op.get_descendants().values_list('id', flat=True)
                                option_q |= Q(
                                    responses__question=question,
                                    responses__selected_options__id__in=list(desc_ids)
                                )
                        except AnswerOption.DoesNotExist:
                            pass

                        q_filter |= option_q
                    except ValueError:
                        pass

            return queryset.filter(q_filter).distinct()

    return DynamicQuestionFilter


def create_option_family_filter(question, root_option):
    """
    Отдельный фильтр для конкретного root-варианта (и его детей).
    """
    filter_title = root_option.text

    class OptionFamilyFilter(SimpleListFilter):
        title = filter_title
        parameter_name = f"question_option_{question.pk}_{root_option.pk}"

        def lookups(self, request, model_admin):
            lookups_list = [(f"option:{root_option.id}", root_option.text)]

            # Дети с отступами
            children = root_option.get_descendants().order_by("order", "text")
            for child in children:
                indent = "— " * (child.level - root_option.level)
                lookups_list.append((f"option:{child.id}", f"{indent}{child.text}"))

            return lookups_list

        def queryset(self, request, queryset):
            values = request.GET.getlist(self.parameter_name)
            if not values:
                return queryset

            q_filter = Q()

            for val in values:
                if val.startswith("option:"):
                    try:
                        option_id = int(val[7:])
                        option_q = Q(responses__question=question, responses__selected_options__id=option_id)

                        # Учитываем и потомков
                        from app.models import AnswerOption
                        try:
                            op = AnswerOption.objects.get(pk=option_id)
                            if op.get_descendant_count() > 0:
                                desc_ids = op.get_descendants().values_list('id', flat=True)
                                option_q |= Q(
                                    responses__question=question,
                                    responses__selected_options__id__in=list(desc_ids)
                                )
                        except AnswerOption.DoesNotExist:
                            pass

                        q_filter |= option_q
                    except ValueError:
                        pass

            return queryset.filter(q_filter).distinct()

    return OptionFamilyFilter

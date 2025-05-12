from django.db import migrations


def migrate_status_data(apps, schema_editor):
    """Переносит данные из старого поля status (строковое значение) в новое поле status (ForeignKey)."""
    SurveySubmission = apps.get_model('app', 'SurveySubmission')
    SubmissionStatus = apps.get_model('app', 'SubmissionStatus')
    
    # Перенастройка связей для всех заявок
    # В интерфейсе миграции Django нельзя использовать isinstance()!
    for submission in SurveySubmission.objects.all():
        try:
            # Пытаемся получить объект статуса по коду
            # Здесь не используем submission.status, так как это уже должно быть преобразовано в поле ForeignKey
            # Используем _status_code как внутреннее имя поля Django для ForeignKey (to_field='code')
            status_code = getattr(submission, '_status_code', None)
            if not status_code:
                # Если код не найден, пробуем получить из старого поля status_id (автоматически создано Django)
                status_id = getattr(submission, 'status_id', None)
                if status_id:
                    # Если есть status_id, значит связь уже установлена
                    continue
                else:
                    # Если нет status_id, используем значение по умолчанию 'new'
                    status_code = 'new'
            
            # Получаем объект статуса по коду
            status_obj = SubmissionStatus.objects.get(code=status_code)
            submission.status = status_obj
            submission.save()
        except Exception as e:
            # Если возникает ошибка, используем статус 'new'
            try:
                default_status = SubmissionStatus.objects.get(code='new')
                submission.status = default_status
                submission.save()
            except Exception:
                # Если даже это не работает, пропускаем запись
                continue


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0035_remove_surveysubmission_status_new_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_status_data, migrations.RunPython.noop),
    ]

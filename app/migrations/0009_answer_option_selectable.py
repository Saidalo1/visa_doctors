from django.db import migrations, models

def create_trigger(apps, schema_editor):
    # SQL для создания триггера
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION update_answer_option_selectability()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Если это вставка или обновление
            IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
                -- Проверяем, есть ли у опции дочерние элементы
                IF EXISTS (
                    SELECT 1 FROM app_answeroption 
                    WHERE parent_id = NEW.id
                ) THEN
                    -- Если есть дочерние элементы, делаем опцию невыбираемой
                    NEW.is_selectable = FALSE;
                ELSE
                    -- Если нет дочерних элементов, делаем опцию выбираемой
                    NEW.is_selectable = TRUE;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS answer_option_selectability_trigger ON app_answeroption;
        
        CREATE TRIGGER answer_option_selectability_trigger
        BEFORE INSERT OR UPDATE ON app_answeroption
        FOR EACH ROW
        EXECUTE FUNCTION update_answer_option_selectability();
    """)

def remove_trigger(apps, schema_editor):
    # SQL для удаления триггера
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS answer_option_selectability_trigger ON app_answeroption;
        DROP FUNCTION IF EXISTS update_answer_option_selectability();
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0008_remove_response_answer_about_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='answeroption',
            name='is_selectable',
            field=models.BooleanField(default=True, verbose_name='Is Selectable'),
        ),
        migrations.RunPython(
            create_trigger,
            remove_trigger
        ),
    ]

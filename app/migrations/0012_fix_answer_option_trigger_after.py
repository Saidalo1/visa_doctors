from django.db import migrations

def create_fixed_trigger(apps, schema_editor):
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION update_answer_option_selectability()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Для INSERT
            IF TG_OP = 'INSERT' THEN
                -- Если это первый ребенок у родителя, делаем родителя неселектируемым
                IF NEW.parent_id IS NOT NULL THEN
                    UPDATE app_answeroption
                    SET is_selectable = FALSE
                    WHERE id = NEW.parent_id
                    AND is_selectable = TRUE;
                END IF;
            
            -- Для UPDATE
            ELSIF TG_OP = 'UPDATE' AND OLD.parent_id IS DISTINCT FROM NEW.parent_id THEN
                -- Если у старого родителя больше нет детей, делаем его селектируемым
                IF OLD.parent_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM app_answeroption 
                    WHERE parent_id = OLD.parent_id
                ) THEN
                    UPDATE app_answeroption
                    SET is_selectable = TRUE
                    WHERE id = OLD.parent_id;
                END IF;

                -- Если у нового родителя это первый ребенок, делаем его неселектируемым
                IF NEW.parent_id IS NOT NULL THEN
                    UPDATE app_answeroption
                    SET is_selectable = FALSE
                    WHERE id = NEW.parent_id
                    AND is_selectable = TRUE;
                END IF;
            
            -- Для DELETE
            ELSIF TG_OP = 'DELETE' THEN
                -- Если у родителя больше нет детей, делаем его селектируемым
                IF OLD.parent_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM app_answeroption 
                    WHERE parent_id = OLD.parent_id
                ) THEN
                    UPDATE app_answeroption
                    SET is_selectable = TRUE
                    WHERE id = OLD.parent_id;
                END IF;
            END IF;

            RETURN NULL; -- для AFTER триггера
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS answer_option_selectability_trigger ON app_answeroption;
        
        CREATE TRIGGER answer_option_selectability_trigger
        AFTER INSERT OR UPDATE OR DELETE ON app_answeroption
        FOR EACH ROW
        EXECUTE FUNCTION update_answer_option_selectability();

        -- Инициализируем существующие записи
        UPDATE app_answeroption ao
        SET is_selectable = NOT EXISTS (
            SELECT 1 FROM app_answeroption child
            WHERE child.parent_id = ao.id
        );
    """)

def remove_fixed_trigger(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS answer_option_selectability_trigger ON app_answeroption;
        DROP FUNCTION IF EXISTS update_answer_option_selectability();
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0011_fix_answer_option_trigger'),
    ]

    operations = [
        migrations.RunPython(
            create_fixed_trigger,
            remove_fixed_trigger
        ),
    ]

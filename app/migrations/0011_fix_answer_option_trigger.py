from django.db import migrations

def create_fixed_trigger(apps, schema_editor):
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION update_answer_option_selectability()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Для INSERT или UPDATE
            IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
                -- Обновляем is_selectable для NEW записи
                -- Если есть дети - FALSE, иначе TRUE
                IF EXISTS (
                    SELECT 1 FROM app_answeroption 
                    WHERE parent_id = NEW.id
                ) THEN
                    NEW.is_selectable = FALSE;
                ELSE
                    NEW.is_selectable = TRUE;
                END IF;

                -- Если parent_id изменился, обновляем старого parent'а
                IF TG_OP = 'UPDATE' AND OLD.parent_id IS NOT NULL AND 
                   (OLD.parent_id != NEW.parent_id OR NEW.parent_id IS NULL) THEN
                    UPDATE app_answeroption
                    SET is_selectable = CASE
                        WHEN EXISTS (
                            SELECT 1 FROM app_answeroption 
                            WHERE parent_id = id
                        ) THEN FALSE
                        ELSE TRUE
                    END
                    WHERE id = OLD.parent_id;
                END IF;

                -- Обновляем нового parent'а если он есть
                IF NEW.parent_id IS NOT NULL THEN
                    UPDATE app_answeroption
                    SET is_selectable = CASE
                        WHEN EXISTS (
                            SELECT 1 FROM app_answeroption 
                            WHERE parent_id = id
                        ) THEN FALSE
                        ELSE TRUE
                    END
                    WHERE id = NEW.parent_id;
                END IF;
            END IF;

            -- Для DELETE
            IF TG_OP = 'DELETE' AND OLD.parent_id IS NOT NULL THEN
                -- Обновляем старого parent'а
                UPDATE app_answeroption
                SET is_selectable = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM app_answeroption 
                        WHERE parent_id = id
                    ) THEN FALSE
                    ELSE TRUE
                END
                WHERE id = OLD.parent_id;
            END IF;

            -- Возвращаем NEW для INSERT и UPDATE, OLD для DELETE
            RETURN CASE
                WHEN TG_OP = 'DELETE' THEN OLD
                ELSE NEW
            END;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS answer_option_selectability_trigger ON app_answeroption;
        
        CREATE TRIGGER answer_option_selectability_trigger
        BEFORE INSERT OR UPDATE OR DELETE ON app_answeroption
        FOR EACH ROW
        EXECUTE FUNCTION update_answer_option_selectability();
    """)

def remove_fixed_trigger(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS answer_option_selectability_trigger ON app_answeroption;
        DROP FUNCTION IF EXISTS update_answer_option_selectability();
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0010_improve_answer_option_trigger'),
    ]

    operations = [
        migrations.RunPython(
            create_fixed_trigger,
            remove_fixed_trigger
        ),
    ]

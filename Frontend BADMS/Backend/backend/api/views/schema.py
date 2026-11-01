from django.http import JsonResponse
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser


@api_view(['GET'])
@permission_classes([IsAdminUser])
def update_globals_db(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE globals_designation
                ADD COLUMN IF NOT EXISTS basic BOOLEAN NOT NULL DEFAULT FALSE;
            """)

            cursor.execute("""
                ALTER TABLE globals_designation
                ADD COLUMN IF NOT EXISTS category VARCHAR(20) NULL;
            """)

            cursor.execute("""
                ALTER TABLE globals_designation
                DROP COLUMN IF EXISTS dept_if_not_basic;
            """)

            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'globals_designation'
                          AND column_name = 'dept_if_not_basic_id'
                    ) THEN
                        ALTER TABLE globals_designation
                        ADD COLUMN dept_if_not_basic_id INTEGER;
                        ALTER TABLE globals_designation
                        ADD CONSTRAINT fk_dept_if_not_basic_id
                        FOREIGN KEY (dept_if_not_basic_id)
                        REFERENCES globals_departmentinfo (id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
            """)

            # GlobalsModuleaccess model has an `inventory_management` flag that older
            # Fusion schemas lack (they have `database` instead) -> get-module-access 500.
            cursor.execute("""
                ALTER TABLE globals_moduleaccess
                ADD COLUMN IF NOT EXISTS inventory_management BOOLEAN NOT NULL DEFAULT FALSE;
            """)

            cursor.execute("""
                DROP SEQUENCE IF EXISTS auth_user_id_seq CASCADE;
            """)
                
            cursor.execute("""
                CREATE SEQUENCE auth_user_id_seq;
            """)
                
            cursor.execute("""
                ALTER TABLE auth_user
                ALTER COLUMN id SET DEFAULT NEXTVAL('auth_user_id_seq');
            """)
                
            cursor.execute("""
                SELECT SETVAL('auth_user_id_seq', COALESCE(MAX(id), 1))
                FROM auth_user;
            """)

            cursor.execute("""
                DROP SEQUENCE IF EXISTS globals_moduleaccess_id_seq CASCADE;
            """)
                
            cursor.execute("""
                CREATE SEQUENCE globals_moduleaccess_id_seq;
            """)
                
            cursor.execute("""
                ALTER TABLE globals_moduleaccess
                ALTER COLUMN id SET DEFAULT NEXTVAL('globals_moduleaccess_id_seq');
            """)
                
            cursor.execute("""
                SELECT SETVAL('globals_moduleaccess_id_seq', COALESCE(MAX(id), 1))
                FROM globals_moduleaccess;
            """)

            cursor.execute("""
                DROP SEQUENCE IF EXISTS globals_holdsdesignation_id_seq CASCADE;
            """)
                
            cursor.execute("""
                CREATE SEQUENCE globals_holdsdesignation_id_seq;
            """)
                
            cursor.execute("""
                ALTER TABLE globals_holdsdesignation
                ALTER COLUMN id SET DEFAULT NEXTVAL('globals_holdsdesignation_id_seq');
            """)
                
            cursor.execute("""
                SELECT SETVAL('globals_holdsdesignation_id_seq', COALESCE(MAX(id), 1))
                FROM globals_holdsdesignation;
            """)

            cursor.execute("""
                DROP TRIGGER IF EXISTS check_basic_designation ON globals_holdsdesignation;
            """)
                
            cursor.execute("""
                DROP FUNCTION IF EXISTS enforce_single_basic_designation();
            """)
                
            cursor.execute("""
                CREATE OR REPLACE FUNCTION enforce_single_basic_designation()
                RETURNS TRIGGER AS $$
                    BEGIN
                        IF NEW.designation_id IS NOT NULL AND (
                        SELECT basic 
                        FROM globals_designation 
                        WHERE id = NEW.designation_id
                    ) = TRUE THEN
                        IF (
                            SELECT COUNT(*) 
                            FROM globals_holdsdesignation h 
                            JOIN globals_designation d 
                            ON h.designation_id = d.id
                            WHERE h.user_id = NEW.user_id AND d.basic = TRUE
                    ) > 0 THEN
                            RAISE EXCEPTION 'A user can only have one basic designation.';
                        END IF;
                    END IF;

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
                
            cursor.execute("""
                CREATE TRIGGER check_basic_designation
                BEFORE INSERT OR UPDATE ON globals_holdsdesignation
                FOR EACH ROW
                EXECUTE FUNCTION enforce_single_basic_designation();
            """)

            cursor.execute("""
                UPDATE globals_designation
                SET basic = TRUE
                WHERE name IN ('Professor', 'Associate Professor', 'Assistant Professor', 'student', 'Registrar');
            """)

            cursor.execute("""
                UPDATE globals_designation
                SET category = CASE
                    WHEN name IN ('Professor', 'Associate Professor', 'Assistant Professor', 
                                'HOD (CSE)', 'HOD (ECE)', 'HOD (ME)', 'HOD (Design)', 
                                'HOD (NS)', 'HOD (Liberal Arts)')
                    THEN 'faculty'
                    WHEN name IN ('student', 'co-ordinator', 'co co-ordinator')
                    THEN 'student'
                    WHEN name IN ('Registrar', 'Compounder')
                    THEN 'staff'
                    ELSE category
                END
                WHERE name IS NOT NULL;
            """)


        return JsonResponse({"success": True, "message": "Database updates completed successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})    

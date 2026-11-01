import django
import os
import pandas as pd
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()
from django.db import connection, transaction
from api.models import GlobalsDesignation, GlobalsDepartmentinfo

file_path = r""
data = pd.read_csv(file_path)


def add_column_if_not_exists():
    with connection.cursor() as cursor:
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name='globals_designation' 
                    AND column_name='dept_if_not_basic_id'
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
dict = dict()     
def create_departments():
   with transaction.atomic():
        for _, row in data.iterrows():
            try:
                value = int(str(row["Dept_if_NOT_basic_designation"]).strip())
            except ValueError as e:
                if(dict.get(str(row["Dept_if_NOT_basic_designation"])) == None):
                    try:
                        department = GlobalsDepartmentinfo.objects.get(name=str(row["Dept_if_NOT_basic_designation"]).strip())
                        dict[str(row["Dept_if_NOT_basic_designation"])] = department.id
                    except GlobalsDepartmentinfo.DoesNotExist:
                        department = GlobalsDepartmentinfo.objects.create(
                            name= str(row["Dept_if_NOT_basic_designation"]).strip()
                        )
                        dict[str(row["Dept_if_NOT_basic_designation"])] = department.id
                        department.save()
                        print("Department created:", department.name)
        print("Departments created successfully.") 

def update_or_create_designations():
    with transaction.atomic():
        for _, row in data.iterrows():
            try:
                designation = GlobalsDesignation.objects.get(name=row["name"])
                designation.full_name = row["full_name"]
                designation.type = row["type"]
                designation.category = row["category"]
                designation.basic = row["basic"] == 'TRUE'
                value = str(row["Dept_if_NOT_basic_designation"]).strip()
                if(value != "nan"):
                    try:
                        designation.dept_if_not_basic = GlobalsDepartmentinfo.objects.get(id=int(value))
                    except ValueError as e:
                        designation.dept_if_not_basic = GlobalsDepartmentinfo.objects.get(id=dict[value])
                else:
                    designation.dept_if_not_basic = None    
                designation.save()
            
            except GlobalsDesignation.DoesNotExist:
                # Create a new designation only if one with this name doesn't exist
                dept_if_not_basic = None
                value = str(row["Dept_if_NOT_basic_designation"]).strip()
                if(value != "nan"):
                    try:
                        dept_if_not_basic = GlobalsDepartmentinfo.objects.get(id=int(value))
                    except ValueError as e:
                        if(dict.get(value) != None):
                            dept_if_not_basic = GlobalsDepartmentinfo.objects.get(id=dict[value])
                            
                        
                GlobalsDesignation.objects.create(
                    name=row["name"],
                    full_name=row["full_name"],
                    type=row["type"],
                    category=row["category"],
                    basic=row["basic"] == 'TRUE',
                    dept_if_not_basic=dept_if_not_basic
                )

    print("Designations updated successfully.")

if __name__ == "__main__":
    add_column_if_not_exists()
    create_departments()
    update_or_create_designations()

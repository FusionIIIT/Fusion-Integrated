from django.urls import path

from ..views import roles

urlpatterns = [
    path("get-user-roles-by-username/", roles.get_user_role_by_username, name="get_user_role_by_username"),
    path("update-user-roles/", roles.update_user_roles, name="update_user_roles"),
    path("view-roles/", roles.global_designation_list, name="global_designation_list"),
    path("view-designations/", roles.get_category_designations, name="get_category_designations"),
    path("create-role/", roles.add_designation, name="add_designation"),
    path("modify-role/", roles.update_designation, name="update_designation"),
    path("get-module-access/", roles.get_module_access, name="get_module_access"),
    path("modify-roleaccess/", roles.modify_moduleaccess, name="modify_moduleaccess"),
]

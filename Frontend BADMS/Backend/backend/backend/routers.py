class SystemDBRouter:
    """Routes this tool's own data to ``system_db`` and leaves the managed ERP
    data on ``default`` (fusionlab).

    ``system_db`` holds:
      * the admin panel's own auth/session plumbing -- the auth cluster
        (``auth``, ``admin``, ``sessions``, ``contenttypes``, ``authtoken``).
        These are FK-linked and must move together. This is what makes admin
        operators a separate account set from the 3277 managed ERP users.
      * the backup subsystem's bookkeeping -- ``django_apscheduler`` jobs and
        the four backup/restore/schedule/health models. Kept off fusionlab so a
        fusionlab restore can't wipe the very log of restores.

    Everything else (the api app's ``managed=False`` ERP models) stays on
    ``default``.
    """

    # Whole apps that live in system_db (their tables FK each other).
    route_app_labels = {
        'django_apscheduler',
        # The IAM's own tables (sessions for ERP users, role->permission map,
        # login attempts). They must NOT land in the ERP database — this
        # service only ever reads that one.
        'iam',
        'auth',
        'admin',
        'sessions',
        'contenttypes',
        'authtoken',
    }
    # Individual api models (managed=True) that live in system_db. The rest of
    # the api app (managed=False ERP tables) stays on default.
    system_models = {'backuprecord', 'restorerecord', 'backupschedule', 'healthcheck', 'archivelog'}

    def _routes_to_system(self, app_label, model_name=None):
        if app_label in self.route_app_labels:
            return True
        if model_name and model_name.lower() in self.system_models:
            return True
        return False

    def db_for_read(self, model, **hints):
        if self._routes_to_system(model._meta.app_label, model._meta.model_name):
            return 'system_db'
        return None

    def db_for_write(self, model, **hints):
        if self._routes_to_system(model._meta.app_label, model._meta.model_name):
            return 'system_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if self._routes_to_system(app_label, model_name):
            # system-owned tables build ONLY on system_db
            return db == 'system_db'
        # everything else builds ONLY on default; never on system_db
        return db == 'default'

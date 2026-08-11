from django.apps import AppConfig

class UserProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_profiles'
    
    def ready(self):
            # Import signals so they are registered when the app is ready
            import user_profiles.signals  # ← this loads the signals from models.py
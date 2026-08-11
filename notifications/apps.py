# notifications/apps.py
from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import os
import json

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # Prevent initialization if already done (critical for runserver reloads)
        if firebase_admin._apps:
            return

        credentials_source = None

        # 1. Try environment variable first (best for production)
        credentials_json = os.getenv('FIREBASE_CREDENTIALS')
        if credentials_json:
            try:
                cred_dict = json.loads(credentials_json)
                credentials_source = credentials.Certificate(cred_dict)
                print("Firebase initialized from FIREBASE_CREDENTIALS environment variable")
            except json.JSONDecodeError as e:
                print(f"Error: FIREBASE_CREDENTIALS is not valid JSON: {e}")
                return
            except Exception as e:
                print(f"Error loading Firebase credentials from env: {e}")
                return

        # 2. Fallback to file (for local development)
        elif hasattr(settings, 'FIREBASE_CREDENTIALS_PATH'):
            file_path = settings.FIREBASE_CREDENTIALS_PATH
            if os.path.exists(file_path):
                try:
                    credentials_source = credentials.Certificate(file_path)
                    print(f"Firebase initialized from file: {file_path}")
                except Exception as e:
                    print(f"Error loading Firebase credentials file: {e}")
                    return
            else:
                print(f"Warning: Firebase credentials file not found at {file_path}")
                print("   → Set FIREBASE_CREDENTIALS env var or place file there.")
                return
        else:
            print("Warning: No Firebase credentials configured (missing path or env var)")
            return

        # Final initialization
        try:
            firebase_admin.initialize_app(credentials_source)
            print("Firebase Admin SDK initialized successfully")
        except ValueError as e:
            if "already exists" in str(e).lower():
                pass  # Already initialized (edge case)
            else:
                print(f"Firebase init error: {e}")
        except Exception as e:
            print(f"Unexpected Firebase init error: {e}")
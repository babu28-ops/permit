from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SECURE_SSL_REDIRECT = True  # In production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SAMESITE = "None"
AUTH_COOKIE_SAMESITE = "None"  # Custom, for use in your set_cookie calls


# Additional Security Headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = not config(
    "DEBUG", default=False, cast=bool
)  # Set to False in development, True in production
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"
PERMISSIONS_POLICY = {
    "accelerometer": [],
    "camera": [],
    "geolocation": [],
    "gyroscope": [],
    "magnetometer": [],
    "microphone": [],
    "payment": [],
    "usb": [],
}

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=5),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_SECURE": True,
    "AUTH_COOKIE_HTTPONLY": True,
    "AUTH_COOKIE_SAMESITE": "None",
    "REFRESH_COOKIE": "refresh_token",
    "REFRESH_COOKIE_SAMESITE": "None",
    "REFRESH_COOKIE_SECURE": True,
}

# dj-rest-auth Configuration
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": "access_token",
    "JWT_AUTH_HTTPONLY": True,
    "JWT_AUTH_SAMESITE": "None",
    "JWT_AUTH_SECURE": True,
    "JWT_AUTH_REFRESH_COOKIE": "refresh_token",
    "SESSION_LOGIN": False,
    "USER_DETAILS_SERIALIZER": "users.serializers.CustomUserDetailsSerializer",
    "REGISTER_SERIALIZER": "users.serializers.CustomRegisterSerializer",
    "OLD_PASSWORD_FIELD_ENABLED": True,
    "PASSWORD_CHANGE_SERIALIZER": "users.serializers.CustomPasswordChangeSerializer",
}

# CSP Configuration - New format
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'",),
        "script-src": ("'self'",),
        "style-src": ("'self'",),
        "img-src": ("'self'", "data:"),
        "font-src": ("'self'",),
        "connect-src": ("'self'", "https://api.yourdomain.com"),
    }
}


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost", cast=Csv())


# Application definition

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Local Apps
    # "locations.apps.LocationsConfig",
    "users.apps.UsersConfig",
    "societies.apps.SocietiesConfig",
    "warehouse.apps.WarehouseConfig",
    "permits.apps.PermitsConfig",
    # 3rd Party Apps
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "dj_rest_auth.registration",
    "dj_rest_auth",  # Django Rest Auth
    "django_filters",
    "csp",
    "channels",
]

SITE_ID = 1


if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SAMESITE = "Lax"  # Important for development
    SESSION_COOKIE_SAMESITE = "Lax"
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SAMESITE = "None"
    CORS_ALLOW_CREDENTIALS = False  # Only allow credentials if absolutely necessary


CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://coffee-permit.vercel.app",  # Set your production domain
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://coffee-permit.vercel.app",
    cast=Csv(),
)

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Allauth
    "csp.middleware.CSPMiddleware",  # Changed from django_csp to csp
    "users.middleware.CsrfTokenMiddleware",  # Add our custom CSRF middleware
    "users.middleware.SecurityMiddleware",
]

# Security settings
MAX_FAILED_ATTEMPTS = 5
ACCOUNT_LOCKOUT_DURATION = 30  # minutes


ROOT_URLCONF = "server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # "django.template.context_processors.request",  # Allauth
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    # "users.backends.EmailPhoneNationalIDBackend",
    # "allauth.account.auth_backends.AuthenticationBackend",
]


WSGI_APPLICATION = "server.wsgi.application"

ASGI_APPLICATION = (
    "server.asgi.application"  # Adjust 'server' to your project root if different
)


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# For Development
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

# For Production
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE"),
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
        "OPTIONS": {"sslmode": "require"},
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.CustomUser"

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": [
        # 'rest_framework.throttling.UserRateThrottle',
        # ...other throttles...
    ],
    "DEFAULT_THROTTLE_RATES": {
        # 'user': '1000/day',
        # ...other rates...
    },
}

# Allauth settings - Updated to use new format
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True

# Additional settings for email-only authp
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Coffee Permit] "
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_PASSWORD_MIN_LENGTH = 8

# Email settings for development (replace your existing email configuration)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# # For Production
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = config("EMAIL_HOST", default=None)
# EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
# EMAIL_HOST_USER = config("EMAIL_HOST_USER", default=None)
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default=None)
# EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)

# # Admins/Managers
# ADMIN_USER_NAME = config("ADMIN_USER_NAME", default="Admin User")
# ADMIN_USER_EMAIL = config("ADMIN_USER_EMAIL", default=None)
# ADMINS = [(ADMIN_USER_NAME, ADMIN_USER_EMAIL)] if ADMIN_USER_EMAIL else []
# MANAGERS = ADMINS

# Allow non-secure cookies in development
if DEBUG:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SIMPLE_JWT["AUTH_COOKIE_SECURE"] = False
    REST_AUTH["JWT_AUTH_SECURE"] = False


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [{
                "host": config("REDIS_HOST"),
                "port": config("REDIS_PORT", cast=int),
                "password": config("REDIS_PASSWORD", default=None),
                "ssl": config("REDIS_SSL", default=False, cast=bool),
            }]
        },
    },
}

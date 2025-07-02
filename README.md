# Coffee Movement Permit System - Backend

## Getting Started

Follow these steps to install and run the backend locally on your machine.

### 1. Clone the Repository

Clone the repository using **SSH** or **HTTPS**:

**Using SSH**  
```bash
git clone git@github.com:county-group/cmp-backend.git
```

**Using HTTPS**
```bash
git clone https://github.com/county-group/cmp-backend.git
```
### 2. Navigate into the Project Directory
```bash
cd cmp-backend
```

### 3. Set Up a Virtual Environment
#### **Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

#### **Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 4. Installing Dependencies
Make sure your virtual environment is activated, then run:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure The Environment Variables
Create a `.env` file and copy environment variables from `env.example` file:

```bash
cp .env.example .env
```

Edit the `.env` file and set the `SECRET_KEY`.
You can generate a Django secret key using:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> **Copy the generated key and paste it into your `.env` file under `SECRET_KEY`. This is the only required modification to get the project running.**

### 6. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```
### 7. Create a Superuser

```bash
python manage.py createsuperuser
```

### 8. Start the Development Server

```bash
daphne -p 8000 server.asgi:application
```

The backend server will start at:
```
http://127.0.0.1:8000
```

> **Note:** The backend now uses Django Channels with Redis for real-time features. Ensure Redis is running on your system (default: 127.0.0.1:6379).

### 9. Access the Admin Panel
Visit:

```
http://127.0.0.1:8000/admin
```
Login using the superuser credentials you just created.

### 10. Elevate Yourself to Admin
1. Go to `http://127.0.0.1:8000/admin/users/user/`
2. Click on your email address.
3. Navigate to Permissions.
4. Change your role from `Farmer` to `Admin`.

---

## Final Step: Use the Frontend
Now that the backend is running and your account has admin rights:

1. Go to: `https://localhost:3000`
2. Log in using your credentials.
3. You'll be redirected to the admin dashboard.
4. To register a new farmer, visit:

```
http://localhost:3000/registration
```

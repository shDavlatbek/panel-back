@echo off
echo Setting up environment...
set DJANGO_SETTINGS_MODULE=config.settings

echo Setting environment variables from .env.local...
for /f "tokens=*" %%a in (.env.local) do (
    echo %%a | findstr /v /c:"#" >nul && (
        set %%a
    )
)

@REM echo Installing dependencies...
@REM pip install -r requirements.txt

echo Creating migrations...
python manage.py makemigrations web

echo Running migrations...
python manage.py migrate

echo Starting server...
python manage.py runserver localhost:8300

echo Server is running at http://localhost:8300 
# Authentication error messages
AUTH_ERROR_MESSAGES = {
    'not_authenticated': 'Login qilmagansiz, iltimos avval login qiling',
    'authentication_failed': 'Autentifikatsiya muvaffaqiyatsiz, qayta login qiling',
    'permission_denied': 'Bu amalni bajarish uchun ruxsat yo\'q',
    'invalid_token': 'Token yaroqsiz yoki muddati tugagan',
    'token_not_found': 'Token topilmadi, qayta login qiling',
    'csrf_failed': 'CSRF tekshiruvi muvaffaqiyatsiz',
    'user_not_found': 'Foydalanuvchi topilmadi',
    'user_inactive': 'Foydalanuvchi faol emas',
    'not_found': '{item} topilmadi',
}

# Validation error messages
VALIDATION_ERROR_MESSAGES = {
    'required': '{field} kiritilishi shart',
    'invalid': '{field} noto\'g\'ri formatda',
    'min_length': '{field} kamida {min_length} belgidan iborat bo\'lishi kerak',
    'max_length': '{field} ko\'pi bilan {max_length} belgidan iborat bo\'lishi kerak',
}

# Login/Logout error messages
LOGIN_ERROR_MESSAGES = {
    'invalid_credentials': 'Login yoki parol noto\'g\'ri',
    'missing_fields': 'Iltimos, foydalanuvchi nomi va parolni kiriting',
}

# Success messages
SUCCESS_MESSAGES = {
    'login': 'Kirish muvaffaqiyatli',
    'logout': 'Chiqish muvaffaqiyatli',
    'token_refresh': 'Token yangilandi',
    'authenticated': 'Autentifikatsiya muvaffaqiyatli',
    'user_profile': 'Foydalanuvchi ma\'lumotlari muvaffaqiyatli olindi',
    'stations_list': 'Stansiyalar ro\'yxati muvaffaqiyatli olindi',
    'parameter_types_list': 'Parametr turlari ro\'yxati muvaffaqiyatli olindi',
    'parameters_list': 'Parametrlar ro\'yxati muvaffaqiyatli olindi',
    'parameters_by_type_list': 'Berilgan turdagi parametrlar ro\'yxati muvaffaqiyatli olindi',
    'station_created': 'Stansiya muvaffaqiyatli yaratildi',
    'station_updated': 'Stansiya muvaffaqiyatli tahrirlandi',
    'station_exists': '{number} raqamli stansiya allaqachon mavjud',
} 
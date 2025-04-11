# Authentication error messages
AUTH_ERROR_MESSAGES = {
    'not_authenticated': 'Autentifikatsiya muvaffaqiyatsiz, iltimos avval login qiling',
    'authentication_failed': 'Autentifikatsiya muvaffaqiyatsiz, qayta login qiling',
    'permission_denied': 'Bu amalni bajarish uchun ruxsat yo\'q',
    'invalid_token': 'Token yaroqsiz yoki muddati tugagan',
    'token_not_found': 'Token topilmadi, qayta login qiling',
    'csrf_failed': 'CSRF tekshiruvi muvaffaqiyatsiz',
    'user_not_found': 'Foydalanuvchi topilmadi',
    'user_inactive': 'Foydalanuvchi faol emas',
    'not_found': '{item} topilmadi',
    'station_exists': '{number} raqamli stansiya allaqachon mavjud',
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

# Hex grid and data API error messages
HEX_ERROR_MESSAGES = {
    'parameter_not_found': "'{parameter_name}' parametri topilmadi",
    'no_station_data': "'{parameter_name}' parametri uchun stansiya ma'lumotlari mavjud emas",
    'invalid_bounds': "Noto'g'ri chegara parametrlari: {error}",
    'parsing_failed': "Koordinatalar formatini tahlil qilishda xatolik: {error}",
    'interpolation_error': "Ma'lumotlarni interpolyatsiya qilishda xatolik: {error}",
    'grid_generation_error': "Hex to'rini yaratishda xatolik: {error}",
}

# Station API error messages
STATION_ERROR_MESSAGES = {
    'not_found': "{number} raqamli stansiya topilmadi",
    'invalid_coordinates': "Noto'g'ri koordinatalar formati: {error}",
    'already_exists': "{number} raqamli stansiya allaqachon mavjud",
    'missing_field': "{field} kiritilishi shart",
    'update_failed': "Stansiyani yangilashda xatolik: {error}",
    'creation_failed': "Stansiya yaratishda xatolik: {error}",
    'deletion_failed': "Stansiyani o'chirishda xatolik: {error}",
}

# Parameter API error messages
PARAMETER_ERROR_MESSAGES = {
    'station_not_found': "{number} raqamli stansiya topilmadi",
    'parameter_name_not_found': "'{parameter_name}' nomli parametr topilmadi",
    'no_parameters': "{station_number} raqamli stansiya uchun parametrlar mavjud emas",
    'parameter_error': "Parametr bilan ishlashda xatolik: {error}"
}
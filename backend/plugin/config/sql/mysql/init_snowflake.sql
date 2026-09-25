insert into sys_config (id, name, type, `key`, value, is_frontend, remark, created_time, updated_time)
values
(2069061886627938304, 'Estado', 'EMAIL', 'EMAIL_CONFIG_STATUS', '1', false, null, now(), null),
(2069061886627938305, 'Dirección del servidor', 'EMAIL', 'EMAIL_HOST', 'smtp.qq.com', false, null, now(), null),
(2069061886627938306, 'Puerto del servidor', 'EMAIL', 'EMAIL_PORT', '465', false, null, now(), null),
(2069061886627938307, 'Cuenta de correo', 'EMAIL', 'EMAIL_USERNAME', 'fba@qq.com', false, null, now(), null),
(2069061886627938308, 'Contraseña de correo', 'EMAIL', 'EMAIL_PASSWORD', '', false, null, now(), null),
(2069061886627938309, 'Cifrado SSL', 'EMAIL', 'EMAIL_SSL', 'true', false, null, now(), null),
(2069061886627938310, 'Estado', 'USER_SECURITY', 'USER_SECURITY_CONFIG_STATUS', '1', false, null, now(), null),
(2069061886627938311, 'Umbral de intentos fallidos', 'USER_SECURITY', 'USER_LOCK_THRESHOLD', '5', false, '0 significa bloqueo deshabilitado', now(), null),
(2069061886627938312, 'Duración del bloqueo (seg.)', 'USER_SECURITY', 'USER_LOCK_SECONDS', '300', false, null, now(), null),
(2069061886627938313, 'Vigencia de la contraseña (días)', 'USER_SECURITY', 'USER_PASSWORD_EXPIRY_DAYS', '365', false, '0 significa que nunca expira', now(), null),
(2069061886627938314, 'Aviso de expiración (días)', 'USER_SECURITY', 'USER_PASSWORD_REMINDER_DAYS', '7', false, '0 significa sin aviso', now(), null),
(2069061886627938315, 'Historial de contraseñas', 'USER_SECURITY', 'USER_PASSWORD_HISTORY_CHECK_COUNT', '3', false, null, now(), null),
(2069061886627938316, 'Longitud mínima de la contraseña', 'USER_SECURITY', 'USER_PASSWORD_MIN_LENGTH', '6', false, null, now(), null),
(2069061886627938317, 'Longitud máxima de la contraseña', 'USER_SECURITY', 'USER_PASSWORD_MAX_LENGTH', '32', false, null, now(), null),
(2069061886627938318, 'Exigir carácter especial', 'USER_SECURITY', 'USER_PASSWORD_REQUIRE_SPECIAL_CHAR', 'false', false, null, now(), null),
(2069061886627938319, 'Estado', 'LOGIN', 'LOGIN_CONFIG_STATUS', '1', false, null, now(), null),
(2069061886627938320, 'Interruptor de captcha', 'LOGIN', 'LOGIN_CAPTCHA_ENABLED', 'true', false, null, now(), null);

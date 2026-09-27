insert into sys_config (id, name, type, "key", value, is_frontend, remark, created_time, updated_time)
values
(1, 'Estado', 'EMAIL', 'EMAIL_CONFIG_STATUS', '1', false, null, now(), null),
(2, 'Dirección del servidor', 'EMAIL', 'EMAIL_HOST', 'smtp.qq.com', false, null, now(), null),
(3, 'Puerto del servidor', 'EMAIL', 'EMAIL_PORT', '465', false, null, now(), null),
(4, 'Cuenta de correo', 'EMAIL', 'EMAIL_USERNAME', 'fba@qq.com', false, null, now(), null),
(5, 'Contraseña de correo', 'EMAIL', 'EMAIL_PASSWORD', '', false, null, now(), null),
(6, 'Cifrado SSL', 'EMAIL', 'EMAIL_SSL', 'true', false, null, now(), null),
(7, 'Estado', 'USER_SECURITY', 'USER_SECURITY_CONFIG_STATUS', '1', false, null, now(), null),
(8, 'Umbral de intentos fallidos', 'USER_SECURITY', 'USER_LOCK_THRESHOLD', '5', false, '0 significa bloqueo deshabilitado', now(), null),
(9, 'Duración del bloqueo (seg.)', 'USER_SECURITY', 'USER_LOCK_SECONDS', '300', false, null, now(), null),
(10, 'Vigencia de la contraseña (días)', 'USER_SECURITY', 'USER_PASSWORD_EXPIRY_DAYS', '365', false, '0 significa que nunca expira', now(), null),
(11, 'Aviso de expiración (días)', 'USER_SECURITY', 'USER_PASSWORD_REMINDER_DAYS', '7', false, '0 significa sin aviso', now(), null),
(12, 'Historial de contraseñas', 'USER_SECURITY', 'USER_PASSWORD_HISTORY_CHECK_COUNT', '3', false, null, now(), null),
(13, 'Longitud mínima de la contraseña', 'USER_SECURITY', 'USER_PASSWORD_MIN_LENGTH', '6', false, null, now(), null),
(14, 'Longitud máxima de la contraseña', 'USER_SECURITY', 'USER_PASSWORD_MAX_LENGTH', '32', false, null, now(), null),
(15, 'Exigir carácter especial', 'USER_SECURITY', 'USER_PASSWORD_REQUIRE_SPECIAL_CHAR', 'false', false, null, now(), null),
(16, 'Estado', 'LOGIN', 'LOGIN_CONFIG_STATUS', '1', false, null, now(), null),
(17, 'Interruptor de captcha', 'LOGIN', 'LOGIN_CAPTCHA_ENABLED', 'true', false, null, now(), null);

select setval(pg_get_serial_sequence('sys_config', 'id'),coalesce(max(id), 0) + 1, true) from sys_config;

insert into gen_business (id, app_name, table_name, doc_comment, table_comment, class_name, schema_name, filename, datetime_mixin, api_version, gen_path, remark, created_time, updated_time)
values (1, 'test', 'sys_opera_log', 'Tabla de registro de operaciones', 'Tabla de registro de operaciones', 'SysOperaLog', 'SysOperaLog', 'sys_opera_log', true, 'v1', null, null, '2025-12-15 15:30:33', null);

insert into gen_column (id, name, comment, type, pd_type, "default", sort, "length", is_pk, is_nullable, gen_business_id)
values
(1, 'trace_id', 'ID de seguimiento de la solicitud', 'String', 'str', null, 2, 32, false, false, 1),
(2, 'username', 'Nombre de usuario', 'String', 'str', null, 3, 64, false, true, 1),
(3, 'method', 'Tipo de solicitud', 'String', 'str', null, 4, 32, false, false, 1),
(4, 'title', 'Módulo de operación', 'String', 'str', null, 5, 256, false, false, 1),
(5, 'path', 'Ruta de la solicitud', 'String', 'str', null, 6, 512, false, false, 1),
(6, 'ip', 'Dirección IP', 'String', 'str', null, 7, 64, false, false, 1),
(7, 'country', 'País', 'String', 'str', null, 8, 64, false, true, 1),
(8, 'region', 'Región', 'String', 'str', null, 9, 64, false, true, 1),
(9, 'city', 'Ciudad', 'String', 'str', null, 10, 64, false, true, 1),
(10, 'user_agent', 'Encabezado de la solicitud', 'String', 'str', null, 11, 512, false, false, 1),
(11, 'os', 'Sistema operativo', 'String', 'str', null, 12, 64, false, true, 1),
(12, 'browser', 'Navegador', 'String', 'str', null, 13, 64, false, true, 1),
(13, 'device', 'Dispositivo', 'String', 'str', null, 14, 64, false, true, 1),
(14, 'args', 'Parámetros de la solicitud', 'JSON', 'dict', null, 15, 0, false, true, 1),
(15, 'status', 'Estado de la operación (0 anómalo, 1 normal)', 'INTEGER', 'int', null, 16, 0, false, false, 1),
(16, 'code', 'Código de estado de la operación', 'String', 'str', null, 17, 32, false, false, 1),
(17, 'msg', 'Mensaje de aviso', 'TEXT', 'str', null, 18, 0, false, true, 1),
(18, 'cost_time', 'Duración de la solicitud (ms)', 'String', 'str', null, 19, 0, false, false, 1),
(19, 'opera_time', 'Hora de la operación', 'String', 'str', null, 20, 0, false, false, 1);

select setval(pg_get_serial_sequence('gen_business', 'id'),coalesce(max(id), 0) + 1, true) from gen_business;
select setval(pg_get_serial_sequence('gen_column', 'id'),coalesce(max(id), 0) + 1, true) from gen_column;

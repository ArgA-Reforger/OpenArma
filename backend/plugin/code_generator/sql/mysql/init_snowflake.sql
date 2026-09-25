insert into gen_business (id, app_name, table_name, doc_comment, table_comment, class_name, schema_name, filename, datetime_mixin, api_version, gen_path, remark, created_time, updated_time)
values (2112248797819043840, 'test', 'sys_opera_log', 'Tabla de registro de operaciones', 'Tabla de registro de operaciones', 'SysOperaLog', 'SysOperaLog', 'sys_opera_log', true, 'v1', null, null, '2025-12-15 15:30:33', null);

insert into gen_column (id, name, comment, type, pd_type, `default`, sort, `length`, is_pk, is_nullable, gen_business_id)
values
(2112248797881958400, 'trace_id', 'ID de seguimiento de la solicitud', 'String', 'str', null, 2, 32, false, false, 2112248797819043840),
(2112248797944872960, 'username', 'Nombre de usuario', 'String', 'str', null, 3, 64, false, true, 2112248797819043840),
(2112248798007787520, 'method', 'Tipo de solicitud', 'String', 'str', null, 4, 32, false, false, 2112248797819043840),
(2112248798070702080, 'title', 'Módulo de operación', 'String', 'str', null, 5, 256, false, false, 2112248797819043840),
(2112248798133616640, 'path', 'Ruta de la solicitud', 'String', 'str', null, 6, 512, false, false, 2112248797819043840),
(2112248798196531200, 'ip', 'Dirección IP', 'String', 'str', null, 7, 64, false, false, 2112248797819043840),
(2112248798259445760, 'country', 'País', 'String', 'str', null, 8, 64, false, true, 2112248797819043840),
(2112248798322360320, 'region', 'Región', 'String', 'str', null, 9, 64, false, true, 2112248797819043840),
(2112248798385274880, 'city', 'Ciudad', 'String', 'str', null, 10, 64, false, true, 2112248797819043840),
(2112248798448189440, 'user_agent', 'Encabezado de la solicitud', 'String', 'str', null, 11, 512, false, false, 2112248797819043840),
(2112248798511104000, 'os', 'Sistema operativo', 'String', 'str', null, 12, 64, false, true, 2112248797819043840),
(2112248798574018560, 'browser', 'Navegador', 'String', 'str', null, 13, 64, false, true, 2112248797819043840),
(2112248798636933120, 'device', 'Dispositivo', 'String', 'str', null, 14, 64, false, true, 2112248797819043840),
(2112248798699847680, 'args', 'Parámetros de la solicitud', 'JSON', 'dict', null, 15, 0, false, true, 2112248797819043840),
(2112248798762762240, 'status', 'Estado de la operación (0 anómalo, 1 normal)', 'INTEGER', 'int', null, 16, 0, false, false, 2112248797819043840),
(2112248798825676800, 'code', 'Código de estado de la operación', 'String', 'str', null, 17, 32, false, false, 2112248797819043840),
(2112248798888591360, 'msg', 'Mensaje de aviso', 'TEXT', 'str', null, 18, 0, false, true, 2112248797819043840),
(2112248798951505920, 'cost_time', 'Duración de la solicitud (ms)', 'String', 'str', null, 19, 0, false, false, 2112248797819043840),
(2112248799014420480, 'opera_time', 'Hora de la operación', 'String', 'str', null, 20, 0, false, false, 2112248797819043840);

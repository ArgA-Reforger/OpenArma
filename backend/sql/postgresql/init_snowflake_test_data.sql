insert into sys_dept (id, name, sort, leader, phone, email, status, del_flag, parent_id, created_time, updated_time)
values (2048601264366944256, 'Prueba', 0, null, null, null, 1, false, null, now(), null);

insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
(2049629108245233664, 'Resumen', 'Dashboard', '/admin', 0, 'ant-design:dashboard-outlined', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108245233665, 'Resumen del sistema', 'Analytics', '/admin/dashboard', 0, 'lucide:area-chart', 1, null, null, 1, 1, 1, '', null, 2049629108245233664, '2025-06-26 20:29:06', null),
(2049629108245233666, 'Espacio de trabajo', 'Workspace', '/workspace', 1, 'carbon:workspace', 1, null, null, 1, 0, 1, '', null, 2049629108245233664, '2025-06-26 20:29:06', null),
(2049629108245233667, 'Sistema', 'System', '/admin/system', 1, 'eos-icons:admin', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108245233668, 'Gestión de departamentos', 'SysDept', '/admin/depts', 1, 'mingcute:department-line', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108245233669, 'Nuevo', 'AddSysDept', null, 0, null, 2, null, 'sys:dept:add', 1, 0, 1, '', null, 2049629108245233668, '2025-06-26 20:29:06', null),
(2049629108245233670, 'Editar', 'EditSysDept', null, 0, null, 2, null, 'sys:dept:edit', 1, 0, 1, '', null, 2049629108245233668, '2025-06-26 20:29:06', null),
(2049629108245233671, 'Eliminar', 'DeleteSysDept', null, 0, null, 2, null, 'sys:dept:del', 1, 0, 1, '', null, 2049629108245233668, '2025-06-26 20:29:06', null),
(2049629108245233672, 'Gestión de usuarios', 'SysUser', '/admin/users', 2, 'ant-design:user-outlined', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108245233673, 'Eliminar', 'DeleteSysUser', null, 0, null, 2, null, 'sys:user:del', 1, 0, 1, '', null, 2049629108245233672, '2025-06-26 20:29:06', null),
(2049629108245233674, 'Gestión de roles', 'SysRole', '/admin/roles', 3, 'carbon:user-role', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108245233675, 'Nuevo', 'AddSysRole', null, 0, null, 2, null, 'sys:role:add', 1, 0, 1, '', null, 2049629108245233674, '2025-06-26 20:29:06', null),
(2049629108245233676, 'Editar', 'EditSysRole', null, 0, null, 2, null, 'sys:role:edit', 1, 0, 1, '', null, 2049629108245233674, '2025-06-26 20:29:06', null),
(2049629108245233677, 'Editar menús del rol', 'EditSysRoleMenu', null, 0, null, 2, null, 'sys:role:menu:edit', 1, 0, 1, '', null, 2049629108245233674, '2025-06-26 20:29:06', null),
(2049629108245233678, 'Editar ámbito de datos del rol', 'EditSysRoleScope', null, 0, null, 2, null, 'sys:role:scope:edit', 1, 0, 1, '', null, 2049629108245233674, '2025-06-26 20:29:06', null),
(2049629108245233679, 'Eliminar', 'DeleteSysRole', null, 0, null, 2, null, 'sys:role:del', 1, 0, 1, '', null, 2049629108245233674, '2025-06-26 20:29:06', null),
(2049629108245233680, 'Gestión de menús', 'SysMenu', '/admin/menus', 4, 'ant-design:menu-outlined', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108245233681, 'Nuevo', 'AddSysMenu', null, 0, null, 2, null, 'sys:menu:add', 1, 0, 1, '', null, 2049629108245233680, '2025-06-26 20:29:06', null),
(2049629108245233682, 'Editar', 'EditSysMenu', null, 0, null, 2, null, 'sys:menu:edit', 1, 0, 1, '', null, 2049629108245233680, '2025-06-26 20:29:06', null),
(2049629108249427968, 'Eliminar', 'DeleteSysMenu', null, 0, null, 2, null, 'sys:menu:del', 1, 0, 1, '', null, 2049629108245233680, '2025-06-26 20:29:06', null),
(2049629108249427969, 'Permisos de datos', 'SysDataPermission', '/admin/data-permission-dir', 5, 'icon-park-outline:permissions', 0, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108249427970, 'Ámbito de datos', 'SysDataScope', '/admin/data-permission', 6, 'cuida:scope-outline', 1, null, null, 1, 1, 1, '', null, 2049629108249427969, '2025-06-26 20:29:06', null),
(2049629108249427971, 'Nuevo', 'AddSysDataScope', null, 0, null, 2, null, 'data:scope:add', 1, 0, 1, '', null, 2049629108249427970, '2025-06-26 20:29:06', null),
(2049629108249427972, 'Editar', 'EditSysDataScope', null, 0, null, 2, null, 'data:scope:edit', 1, 0, 1, '', null, 2049629108249427970, '2025-06-26 20:29:06', null),
(2049629108249427973, 'Editar regla de ámbito de datos', 'EditDataScopeRule', null, 0, null, 2, null, 'data:scope:rule:edit', 1, 0, 1, '', null, 2049629108249427970, '2025-06-26 20:29:06', null),
(2049629108249427974, 'Eliminar', 'DeleteSysDataScope', null, 0, null, 2, null, 'data:scope:del', 1, 0, 1, '', null, 2049629108249427970, '2025-06-26 20:29:06', null),
(2049629108249427975, 'Regla de datos', 'SysDataRule', '/admin/data-permission', 7, 'material-symbols:rule', 1, null, null, 1, 1, 1, '', null, 2049629108249427969, '2025-06-26 20:29:06', null),
(2049629108249427976, 'Nuevo', 'AddSysDataRule', null, 0, null, 2, null, 'data:rule:add', 1, 0, 1, '', null, 2049629108249427975, '2025-06-26 20:29:06', null),
(2049629108249427977, 'Editar', 'EditSysDataRule', null, 0, null, 2, null, 'data:rule:edit', 1, 0, 1, '', null, 2049629108249427975, '2025-06-26 20:29:06', null),
(2049629108249427978, 'Eliminar', 'DeleteSysDataRule', null, 0, null, 2, null, 'data:rule:del', 1, 0, 1, '', null, 2049629108249427975, '2025-06-26 20:29:06', null),
(2049629108249427979, 'Gestión de plugins', 'SysPlugin', '/admin/plugins', 8, 'clarity:plugin-line', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108249427980, 'Instalar', 'InstallSysPlugin', null, 0, null, 2, null, 'sys:plugin:install', 1, 0, 1, '', null, 2049629108249427979, '2025-06-26 20:29:06', null),
(2049629108249427981, 'Desinstalar', 'UninstallSysPlugin', null, 0, null, 2, null, 'sys:plugin:uninstall', 1, 0, 1, '', null, 2049629108249427979, '2025-06-26 20:29:06', null),
(2049629108249427982, 'Editar', 'EditSysPlugin', null, 0, null, 2, null, 'sys:plugin:edit', 1, 0, 1, '', null, 2049629108249427979, '2025-06-26 20:29:06', null),
(2049629108249427983, 'Programador de tareas', 'Scheduler', '/admin/scheduler-dir', 2, 'material-symbols:automation', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108249427984, 'Gestión de tareas', 'SchedulerManage', '/admin/scheduler', 1, 'ix:scheduler', 1, null, null, 1, 1, 1, '', null, 2049629108249427983, '2025-06-26 20:29:06', null),
(2049629108249427985, 'Registro de tareas', 'SchedulerRecord', '/scheduler/record', 2, 'ix:scheduler', 1, null, null, 1, 0, 1, '', null, 2049629108249427983, '2025-06-26 20:29:06', null),
(2049629108249427986, 'Registros', 'Log', '/admin/logs', 3, 'carbon:cloud-logging', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108249427987, 'Registro de accesos', 'LoginLog', '/admin/logs/login', 1, 'mdi:login', 1, null, null, 1, 1, 1, '', null, 2049629108249427986, '2025-06-26 20:29:06', null),
(2049629108249427988, 'Eliminar', 'DeleteLoginLog', null, 0, null, 2, null, 'log:login:del', 1, 0, 1, '', null, 2049629108249427987, '2025-06-26 20:29:06', null),
(2049629108249427989, 'Vaciar', 'EmptyLoginLog', null, 0, null, 2, null, 'log:login:clear', 1, 0, 1, '', null, 2049629108249427987, '2025-06-26 20:29:06', null),
(2049629108249427990, 'Registro de operaciones', 'OperaLog', '/admin/logs/opera', 2, 'carbon:operations-record', 1, null, null, 1, 1, 1, '', null, 2049629108249427986, '2025-06-26 20:29:06', null),
(2049629108249427991, 'Eliminar', 'DeleteOperaLog', null, 0, null, 2, null, 'log:opera:del', 1, 0, 1, '', null, 2049629108249427990, '2025-06-26 20:29:06', null),
(2049629108253622272, 'Vaciar', 'EmptyOperaLog', null, 0, null, 2, null, 'log:opera:clear', 1, 0, 1, '', null, 2049629108249427990, '2025-06-26 20:29:06', null),
(2049629108253622273, 'Monitoreo', 'Monitor', '/admin/monitor', 4, 'mdi:monitor-eye', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108253622274, 'Usuarios en línea', 'Online', '/admin/monitor/online', 1, 'wpf:online', 1, null, null, 1, 1, 1, '', null, 2049629108253622273, '2025-06-26 20:29:06', null),
(2049629108253622276, 'Monitoreo de Redis', 'Redis', '/admin/monitor/redis', 2, 'devicon:redis', 1, null, null, 1, 1, 1, '', null, 2049629108253622273, '2025-06-26 20:29:06', null),
(2049629108253622277, 'Monitoreo del servidor', 'Server', '/admin/monitor/server', 3, 'mdi:server-outline', 1, null, null, 1, 1, 1, '', null, 2049629108253622273, '2025-06-26 20:29:06', null),
(2049629108253622278, 'Proyecto', 'Project', '/fba', 5, 'https://wu-clan.github.io/picx-images-hosting/logo/fba.png', 0, null, null, 1, 0, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108253622279, 'Documentación', 'Document', '/fba/document', 1, 'lucide:book-open-text', 4, null, null, 1, 1, 1, 'https://fastapi-practices.github.io/fastapi_best_architecture_docs', null, 2049629108253622278, '2025-06-26 20:29:06', null),
(2049629108253622280, 'Github', 'Github', '/fba/github', 2, 'ant-design:github-filled', 4, null, null, 1, 1, 1, 'https://github.com/fastapi-practices/fastapi_best_architecture', null, 2049629108253622278, '2025-06-26 20:29:06', null),
(2049629108253622281, 'Apifox', 'Apifox', '/fba/apifox', 3, 'simple-icons:apifox', 3, null, null, 1, 1, 1, 'https://apifox.com/apidoc/shared-28a93f02-730b-4f33-bb5e-4dad92058cc0', null, 2049629108253622278, '2025-06-26 20:29:06', null),
(2049629108253622282, 'Perfil', 'Profile', '/profile', 6, 'ant-design:profile-outlined', 1, null, null, 1, 0, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108253622283, 'Configuración del sistema', 'PluginConfig', '/admin/config', 7, 'codicon:symbol-parameter', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108253622284, 'Nuevo', 'AddConfig', null, 0, null, 2, null, 'sys:config:add', 1, 0, 1, '', null, 2049629108253622283, '2025-06-26 20:29:06', null),
(2049629108253622285, 'Editar', 'EditConfig', null, 0, null, 2, null, 'sys:config:edit', 1, 0, 1, '', null, 2049629108253622283, '2025-06-26 20:29:06', null),
(2049629108253622286, 'Eliminar', 'DeleteConfig', null, 0, null, 2, null, 'sys:config:del', 1, 0, 1, '', null, 2049629108253622283, '2025-06-26 20:29:06', null),
(2049629108253622287, 'Gestión de diccionario', 'PluginDict', '/admin/dict', 8, 'fluent-mdl2:dictionary', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108253622288, 'Nuevo tipo', 'AddDictType', null, 0, null, 2, null, 'dict:type:add', 1, 0, 1, '', null, 2049629108253622287, '2025-06-26 20:29:06', null),
(2049629108253622289, 'Editar tipo', 'EditDictType', null, 0, null, 2, null, 'dict:type:edit', 1, 0, 1, '', null, 2049629108253622287, '2025-06-26 20:29:06', null),
(2049629108253622290, 'Eliminar tipo', 'DeleteDictType', null, 0, null, 2, null, 'dict:type:del', 1, 0, 1, '', null, 2049629108253622287, '2025-06-26 20:29:06', null),
(2049629108253622291, 'Nuevo dato', 'AddDictData', null, 0, null, 2, null, 'dict:data:add', 1, 0, 1, '', null, 2049629108253622287, '2025-06-26 20:29:06', null),
(2049629108253622292, 'Editar dato', 'EditDictData', null, 0, null, 2, null, 'dict:data:edit', 1, 0, 1, '', null, 2049629108253622287, '2025-06-26 20:29:06', null),
(2049629108253622293, 'Eliminar dato', 'DeleteDictData', null, 0, null, 2, null, 'dict:data:del', 1, 0, 1, '', null, 2049629108253622287, '2025-06-26 20:29:06', null),
(2049629108257816576, 'Gestión de notificaciones', 'PluginNotice', '/admin/notices', 9, 'fe:notice-push', 1, null, null, 1, 1, 1, '', null, 2049629108245233667, '2025-06-26 20:29:06', null),
(2049629108257816577, 'Nuevo', 'AddNotice', null, 0, null, 2, null, 'sys:notice:add', 1, 0, 1, '', null, 2049629108257816576, '2025-06-26 20:29:06', null),
(2049629108257816578, 'Editar', 'EditNotice', null, 0, null, 2, null, 'sys:notice:edit', 1, 0, 1, '', null, 2049629108257816576, '2025-06-26 20:29:06', null),
(2049629108257816579, 'Eliminar', 'DeleteNotice', null, 0, null, 2, null, 'sys:notice:del', 1, 0, 1, '', null, 2049629108257816576, '2025-06-26 20:29:06', null),
(2049629108257816580, 'Generador de código', 'PluginCodeGenerator', '/plugins/code-generator', 10, 'tabler:code', 1, null, null, 1, 0, 1, '', null, null, '2025-06-26 20:29:06', null),
(2049629108257816581, 'Nueva tabla', 'AddGenCodeBusiness', '', 0, null, 2, null, 'codegen:business:add', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', '2025-06-26 20:45:16'),
(2049629108257816582, 'Editar tabla', 'EditGenCodeBusiness', null, 0, null, 2, null, 'codegen:business:edit', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null),
(2049629108257816583, 'Eliminar tabla', 'DeleteGenCodeBusiness', null, 0, null, 2, null, 'codegen:business:del', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null),
(2049629108257816584, 'Nuevo modelo', 'AddGenCodeModel', null, 0, null, 2, null, 'codegen:model:add', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null),
(2049629108257816585, 'Editar modelo', 'EditGenCodeModel', null, 0, null, 2, null, 'codegen:model:edit', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null),
(2049629108257816586, 'Eliminar modelo', 'DeleteGenCodeModel', null, 0, null, 2, null, 'codegen:model:del', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null),
(2049629108257816587, 'Importar', 'ImportGenCode', null, 0, null, 2, null, 'codegen:table:import', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null),
(2049629108257816588, 'Escribir', 'WriteGenCode', null, 0, null, 2, null, 'codegen:local:write', 1, 0, 1, '', null, 2049629108257816580, '2025-06-26 20:29:06', null);

insert into sys_role (id, name, status, is_filter_scopes, remark, created_time, updated_time)
values (2048601269345583104, 'Prueba', 1, true, null, now(), null);

insert into sys_role_menu (id, role_id, menu_id)
values
(2048601269412691968, 2048601269345583104, 2049629108245233664),
(2048601269479800832, 2048601269345583104, 2049629108245233665),
(2048601269546909696, 2048601269345583104, 2049629108245233666),
(2048601269609824256, 2048601269345583104, 2049629108253622282);

insert into sys_user (id, uuid, username, nickname, password, salt, email, status, is_superuser, is_staff, is_multi_login, avatar, phone, join_time, last_login_time, last_password_changed_time, dept_id, created_time, updated_time)
values
(2048601269672738816, gen_random_uuid(), 'admin', 'Usuario88888', '$2b$12$8y2eNucX19VjmZ3tYhBLcOsBwy9w1IjBQE4SSqwMDL5bGQVp2wqS.', decode('24326224313224387932654E7563583139566A6D5A33745968424C634F', 'hex'), 'admin@example.com', 1, true, true, true, null, null, now(), now(), now(), 2048601264366944256, now(), null),
(2049946297615646720, gen_random_uuid(), 'test', 'Usuario66666', '$2b$12$BMiXsNQAgTx7aNc7kVgnwedXGyUxPEHRnJMFbiikbqHgVoT3y14Za', decode('24326224313224424D6958734E514167547837614E63376B56676E7765', 'hex'), 'test@example.com', 1, false, false, false, null, null, now(), now(), now(), 2048601264366944256, now(), null);

insert into sys_user_role (id, user_id, role_id)
values
(2048601269739847680, 2048601269672738816, 2048601269345583104),
(2049946493732913152, 2049946297615646720, 2048601269345583104);

insert into sys_data_scope (id, name, status, created_time, updated_time)
values
(2048601269806956544, 'Permisos de datos del departamento propio', 1, now(), null),
(2048601269869871104, 'Permisos de datos del departamento y sus subordinados', 1, now(), null),
(2048601269869871105, 'Permisos de datos del usuario propio', 1, now(), null),
(2048601269869871106, 'Permisos de datos del departamento propio en todos los modelos', 1, now(), null),
(2048601269869871107, 'Permisos de datos excluyendo al superadministrador', 1, now(), null);

insert into sys_data_rule (id, name, model, "column", operator, expression, "value", created_time, updated_time)
values
(2048601269932785664, 'ID de departamento igual al departamento del usuario actual', 'Dept', '__dept_id__', 0, 0, '${dept_id}', now(), null),
(2048601269999894528, 'Nombre de departamento igual a Prueba', 'Dept', 'name', 1, 0, 'Prueba', now(), null),
(2048601269999894529, 'ID de departamento superior igual al ID del departamento Prueba', 'Dept', 'parent_id', 0, 0, '1', now(), null),
(2048601269999894530, 'Creador igual al usuario actual', '__ALL__', '__created_by__', 0, 0, '${user_id}', now(), null),
(2048601269999894531, 'ID de departamento igual al departamento del usuario actual en todos los modelos', '__ALL__', '__dept_id__', 0, 0, '${dept_id}', now(), null),
(2048601269999894533, 'Usuario no es superadministrador', 'User', 'is_superuser', 0, 1, '1', now(), null);

insert into sys_data_scope_rule (id, data_scope_id, data_rule_id)
values
(2048601270062809088, 2048601269806956544, 2048601269932785664),
(2048601270125723648, 2048601269869871104, 2048601269999894528),
(2048601270192832512, 2048601269869871104, 2048601269999894529),
(2048601270192832513, 2048601269869871105, 2048601269999894530),
(2048601270192832514, 2048601269869871106, 2048601269999894531),
(2048601270192832515, 2048601269869871107, 2048601269999894533);

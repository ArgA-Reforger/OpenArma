insert into sys_dept (id, name, sort, leader, phone, email, status, del_flag, parent_id, created_time, updated_time)
values (1, 'Prueba', 0, null, null, null, 1, false, null, now(), null);

insert into sys_menu (id, title, name, path, sort, icon, type, component, perms, status, display, cache, link, remark, parent_id, created_time, updated_time)
values
(1, 'Resumen', 'Dashboard', '/admin', 0, 'ant-design:dashboard-outlined', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(2, 'Resumen del sistema', 'Analytics', '/admin/dashboard', 0, 'lucide:area-chart', 1, null, null, 1, 1, 1, '', null, 1, '2025-06-26 20:29:06', null),
(3, 'Espacio de trabajo', 'Workspace', '/workspace', 1, 'carbon:workspace', 1, null, null, 1, 0, 1, '', null, 1, '2025-06-26 20:29:06', null),
(4, 'Sistema', 'System', '/admin/system', 1, 'eos-icons:admin', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(5, 'Gestión de departamentos', 'SysDept', '/admin/depts', 1, 'mingcute:department-line', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(6, 'Nuevo', 'AddSysDept', null, 0, null, 2, null, 'sys:dept:add', 1, 0, 1, '', null, 5, '2025-06-26 20:29:06', null),
(7, 'Editar', 'EditSysDept', null, 0, null, 2, null, 'sys:dept:edit', 1, 0, 1, '', null, 5, '2025-06-26 20:29:06', null),
(8, 'Eliminar', 'DeleteSysDept', null, 0, null, 2, null, 'sys:dept:del', 1, 0, 1, '', null, 5, '2025-06-26 20:29:06', null),
(9, 'Gestión de usuarios', 'SysUser', '/admin/users', 2, 'ant-design:user-outlined', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(10, 'Eliminar', 'DeleteSysUser', null, 0, null, 2, null, 'sys:user:del', 1, 0, 1, '', null, 9, '2025-06-26 20:29:06', null),
(11, 'Gestión de roles', 'SysRole', '/admin/roles', 3, 'carbon:user-role', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(12, 'Nuevo', 'AddSysRole', null, 0, null, 2, null, 'sys:role:add', 1, 0, 1, '', null, 11, '2025-06-26 20:29:06', null),
(13, 'Editar', 'EditSysRole', null, 0, null, 2, null, 'sys:role:edit', 1, 0, 1, '', null, 11, '2025-06-26 20:29:06', null),
(14, 'Editar menús del rol', 'EditSysRoleMenu', null, 0, null, 2, null, 'sys:role:menu:edit', 1, 0, 1, '', null, 11, '2025-06-26 20:29:06', null),
(15, 'Editar ámbito de datos del rol', 'EditSysRoleScope', null, 0, null, 2, null, 'sys:role:scope:edit', 1, 0, 1, '', null, 11, '2025-06-26 20:29:06', null),
(16, 'Eliminar', 'DeleteSysRole', null, 0, null, 2, null, 'sys:role:del', 1, 0, 1, '', null, 11, '2025-06-26 20:29:06', null),
(17, 'Gestión de menús', 'SysMenu', '/admin/menus', 4, 'ant-design:menu-outlined', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(18, 'Nuevo', 'AddSysMenu', null, 0, null, 2, null, 'sys:menu:add', 1, 0, 1, '', null, 17, '2025-06-26 20:29:06', null),
(19, 'Editar', 'EditSysMenu', null, 0, null, 2, null, 'sys:menu:edit', 1, 0, 1, '', null, 17, '2025-06-26 20:29:06', null),
(20, 'Eliminar', 'DeleteSysMenu', null, 0, null, 2, null, 'sys:menu:del', 1, 0, 1, '', null, 17, '2025-06-26 20:29:06', null),
(21, 'Permisos de datos', 'SysDataPermission', '/admin/data-permission-dir', 5, 'icon-park-outline:permissions', 0, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(22, 'Ámbito de datos', 'SysDataScope', '/admin/data-permission', 6, 'cuida:scope-outline', 1, null, null, 1, 1, 1, '', null, 21, '2025-06-26 20:29:06', null),
(23, 'Nuevo', 'AddSysDataScope', null, 0, null, 2, null, 'data:scope:add', 1, 0, 1, '', null, 22, '2025-06-26 20:29:06', null),
(24, 'Editar', 'EditSysDataScope', null, 0, null, 2, null, 'data:scope:edit', 1, 0, 1, '', null, 22, '2025-06-26 20:29:06', null),
(25, 'Editar regla de ámbito de datos', 'EditDataScopeRule', null, 0, null, 2, null, 'data:scope:rule:edit', 1, 0, 1, '', null, 22, '2025-06-26 20:29:06', null),
(26, 'Eliminar', 'DeleteSysDataScope', null, 0, null, 2, null, 'data:scope:del', 1, 0, 1, '', null, 22, '2025-06-26 20:29:06', null),
(27, 'Regla de datos', 'SysDataRule', '/admin/data-permission', 7, 'material-symbols:rule', 1, null, null, 1, 1, 1, '', null, 21, '2025-06-26 20:29:06', null),
(28, 'Nuevo', 'AddSysDataRule', null, 0, null, 2, null, 'data:rule:add', 1, 0, 1, '', null, 27, '2025-06-26 20:29:06', null),
(29, 'Editar', 'EditSysDataRule', null, 0, null, 2, null, 'data:rule:edit', 1, 0, 1, '', null, 27, '2025-06-26 20:29:06', null),
(30, 'Eliminar', 'DeleteSysDataRule', null, 0, null, 2, null, 'data:rule:del', 1, 0, 1, '', null, 27, '2025-06-26 20:29:06', null),
(31, 'Gestión de plugins', 'SysPlugin', '/admin/plugins', 8, 'clarity:plugin-line', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(32, 'Instalar', 'InstallSysPlugin', null, 0, null, 2, null, 'sys:plugin:install', 1, 0, 1, '', null, 31, '2025-06-26 20:29:06', null),
(33, 'Desinstalar', 'UninstallSysPlugin', null, 0, null, 2, null, 'sys:plugin:uninstall', 1, 0, 1, '', null, 31, '2025-06-26 20:29:06', null),
(34, 'Editar', 'EditSysPlugin', null, 0, null, 2, null, 'sys:plugin:edit', 1, 0, 1, '', null, 31, '2025-06-26 20:29:06', null),
(35, 'Programador de tareas', 'Scheduler', '/admin/scheduler-dir', 2, 'material-symbols:automation', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(36, 'Gestión de tareas', 'SchedulerManage', '/admin/scheduler', 1, 'ix:scheduler', 1, null, null, 1, 1, 1, '', null, 35, '2025-06-26 20:29:06', null),
(37, 'Registro de tareas', 'SchedulerRecord', '/scheduler/record', 2, 'ix:scheduler', 1, null, null, 1, 0, 1, '', null, 35, '2025-06-26 20:29:06', null),
(38, 'Registros', 'Log', '/admin/logs', 3, 'carbon:cloud-logging', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(39, 'Registro de accesos', 'LoginLog', '/admin/logs/login', 1, 'mdi:login', 1, null, null, 1, 1, 1, '', null, 38, '2025-06-26 20:29:06', null),
(40, 'Eliminar', 'DeleteLoginLog', null, 0, null, 2, null, 'log:login:del', 1, 0, 1, '', null, 39, '2025-06-26 20:29:06', null),
(41, 'Vaciar', 'EmptyLoginLog', null, 0, null, 2, null, 'log:login:clear', 1, 0, 1, '', null, 39, '2025-06-26 20:29:06', null),
(42, 'Registro de operaciones', 'OperaLog', '/admin/logs/opera', 2, 'carbon:operations-record', 1, null, null, 1, 1, 1, '', null, 38, '2025-06-26 20:29:06', null),
(43, 'Eliminar', 'DeleteOperaLog', null, 0, null, 2, null, 'log:opera:del', 1, 0, 1, '', null, 42, '2025-06-26 20:29:06', null),
(44, 'Vaciar', 'EmptyOperaLog', null, 0, null, 2, null, 'log:opera:clear', 1, 0, 1, '', null, 42, '2025-06-26 20:29:06', null),
(45, 'Monitoreo', 'Monitor', '/admin/monitor', 4, 'mdi:monitor-eye', 0, null, null, 1, 1, 1, '', null, null, '2025-06-26 20:29:06', null),
(46, 'Usuarios en línea', 'Online', '/admin/monitor/online', 1, 'wpf:online', 1, null, null, 1, 1, 1, '', null, 45, '2025-06-26 20:29:06', null),
(47, 'Monitoreo de Redis', 'Redis', '/admin/monitor/redis', 2, 'devicon:redis', 1, null, null, 1, 1, 1, '', null, 45, '2025-06-26 20:29:06', null),
(48, 'Monitoreo del servidor', 'Server', '/admin/monitor/server', 3, 'mdi:server-outline', 1, null, null, 1, 1, 1, '', null, 45, '2025-06-26 20:29:06', null),
(49, 'Proyecto', 'Project', '/fba', 5, 'https://wu-clan.github.io/picx-images-hosting/logo/fba.png', 0, null, null, 1, 0, 1, '', null, null, '2025-06-26 20:29:06', null),
(50, 'Documentación', 'Document', '/fba/document', 1, 'lucide:book-open-text', 4, null, null, 1, 1, 1, 'https://fastapi-practices.github.io/fastapi_best_architecture_docs', null, 49, '2025-06-26 20:29:06', null),
(51, 'Github', 'Github', '/fba/github', 2, 'ant-design:github-filled', 4, null, null, 1, 1, 1, 'https://github.com/fastapi-practices/fastapi_best_architecture', null, 49, '2025-06-26 20:29:06', null),
(52, 'Apifox', 'Apifox', '/fba/apifox', 3, 'simple-icons:apifox', 3, null, null, 1, 1, 1, 'https://apifox.com/apidoc/shared-28a93f02-730b-4f33-bb5e-4dad92058cc0', null, 49, '2025-06-26 20:29:06', null),
(53, 'Perfil', 'Profile', '/profile', 6, 'ant-design:profile-outlined', 1, null, null, 1, 0, 1, '', null, null, '2025-06-26 20:29:06', null),
(54, 'Configuración del sistema', 'PluginConfig', '/admin/config', 7, 'codicon:symbol-parameter', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(55, 'Nuevo', 'AddConfig', null, 0, null, 2, null, 'sys:config:add', 1, 0, 1, '', null, 54, '2025-06-26 20:29:06', null),
(56, 'Editar', 'EditConfig', null, 0, null, 2, null, 'sys:config:edit', 1, 0, 1, '', null, 54, '2025-06-26 20:29:06', null),
(57, 'Eliminar', 'DeleteConfig', null, 0, null, 2, null, 'sys:config:del', 1, 0, 1, '', null, 54, '2025-06-26 20:29:06', null),
(58, 'Gestión de diccionario', 'PluginDict', '/admin/dict', 8, 'fluent-mdl2:dictionary', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(59, 'Nuevo tipo', 'AddDictType', null, 0, null, 2, null, 'dict:type:add', 1, 0, 1, '', null, 58, '2025-06-26 20:29:06', null),
(60, 'Editar tipo', 'EditDictType', null, 0, null, 2, null, 'dict:type:edit', 1, 0, 1, '', null, 58, '2025-06-26 20:29:06', null),
(61, 'Eliminar tipo', 'DeleteDictType', null, 0, null, 2, null, 'dict:type:del', 1, 0, 1, '', null, 58, '2025-06-26 20:29:06', null),
(62, 'Nuevo dato', 'AddDictData', null, 0, null, 2, null, 'dict:data:add', 1, 0, 1, '', null, 58, '2025-06-26 20:29:06', null),
(63, 'Editar dato', 'EditDictData', null, 0, null, 2, null, 'dict:data:edit', 1, 0, 1, '', null, 58, '2025-06-26 20:29:06', null),
(64, 'Eliminar dato', 'DeleteDictData', null, 0, null, 2, null, 'dict:data:del', 1, 0, 1, '', null, 58, '2025-06-26 20:29:06', null),
(65, 'Gestión de notificaciones', 'PluginNotice', '/admin/notices', 9, 'fe:notice-push', 1, null, null, 1, 1, 1, '', null, 4, '2025-06-26 20:29:06', null),
(66, 'Nuevo', 'AddNotice', null, 0, null, 2, null, 'sys:notice:add', 1, 0, 1, '', null, 65, '2025-06-26 20:29:06', null),
(67, 'Editar', 'EditNotice', null, 0, null, 2, null, 'sys:notice:edit', 1, 0, 1, '', null, 65, '2025-06-26 20:29:06', null),
(68, 'Eliminar', 'DeleteNotice', null, 0, null, 2, null, 'sys:notice:del', 1, 0, 1, '', null, 65, '2025-06-26 20:29:06', null),
(69, 'Generador de código', 'PluginCodeGenerator', '/plugins/code-generator', 10, 'tabler:code', 1, null, null, 1, 0, 1, '', null, null, '2025-06-26 20:29:06', null),
(70, 'Nueva tabla', 'AddGenCodeBusiness', '', 0, null, 2, null, 'codegen:business:add', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', '2025-06-26 20:45:16'),
(71, 'Editar tabla', 'EditGenCodeBusiness', null, 0, null, 2, null, 'codegen:business:edit', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null),
(72, 'Eliminar tabla', 'DeleteGenCodeBusiness', null, 0, null, 2, null, 'codegen:business:del', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null),
(73, 'Nuevo modelo', 'AddGenCodeModel', null, 0, null, 2, null, 'codegen:model:add', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null),
(74, 'Editar modelo', 'EditGenCodeModel', null, 0, null, 2, null, 'codegen:model:edit', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null),
(75, 'Eliminar modelo', 'DeleteGenCodeModel', null, 0, null, 2, null, 'codegen:model:del', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null),
(76, 'Importar', 'ImportGenCode', null, 0, null, 2, null, 'codegen:table:import', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null),
(77, 'Escribir', 'WriteGenCode', null, 0, null, 2, null, 'codegen:local:write', 1, 0, 1, '', null, 69, '2025-06-26 20:29:06', null);

insert into sys_role (id, name, status, is_filter_scopes, remark, created_time, updated_time)
values (1, 'Prueba', 1, true, null, now(), null);

insert into sys_role_menu (id, role_id, menu_id)
values
(1, 1, 1),
(2, 1, 2),
(3, 1, 3),
(4, 1, 53);

insert into sys_user (id, uuid, username, nickname, password, salt, email, status, is_superuser, is_staff, is_multi_login, avatar, phone, join_time, last_login_time, last_password_changed_time, dept_id, created_time, updated_time)
values
(1, gen_random_uuid(), 'admin', 'Usuario88888', '$2b$12$8y2eNucX19VjmZ3tYhBLcOsBwy9w1IjBQE4SSqwMDL5bGQVp2wqS.', decode('24326224313224387932654E7563583139566A6D5A33745968424C634F', 'hex'), 'admin@example.com', 1, true, true, true, null, null, now(), now(), now(), 1, now(), null),
(2, gen_random_uuid(), 'test', 'Usuario66666', '$2b$12$BMiXsNQAgTx7aNc7kVgnwedXGyUxPEHRnJMFbiikbqHgVoT3y14Za', decode('24326224313224424D6958734E514167547837614E63376B56676E7765', 'hex'), 'test@example.com', 1, false, false, false, null, null, now(), now(), now(), 1, now(), null);

insert into sys_user_role (id, user_id, role_id)
values
(1, 1, 1),
(2, 2, 1);

insert into sys_data_scope (id, name, status, created_time, updated_time)
values
(1, 'Permisos de datos del departamento propio', 1, now(), null),
(2, 'Permisos de datos del departamento de prueba y sus subordinados', 1, now(), null),
(3, 'Permisos de datos del usuario propio', 1, now(), null),
(4, 'Permisos de datos del departamento propio en todos los modelos', 1, now(), null),
(5, 'Permisos de datos excluyendo al superadministrador', 1, now(), null);

insert into sys_data_rule (id, name, model, "column", operator, expression, "value", created_time, updated_time)
values
(1, 'ID de departamento igual al departamento del usuario actual', 'Dept', '__dept_id__', 0, 0, '${dept_id}', now(), null),
(2, 'Nombre de departamento igual a Prueba', 'Dept', 'name', 1, 0, 'Prueba', now(), null),
(3, 'ID de departamento superior igual al ID del departamento Prueba', 'Dept', 'parent_id', 0, 0, '1', now(), null),
(4, 'Creador igual al usuario actual', '__ALL__', '__created_by__', 0, 0, '${user_id}', now(), null),
(5, 'ID de departamento igual al departamento del usuario actual en todos los modelos', '__ALL__', '__dept_id__', 0, 0, '${dept_id}', now(), null),
(6, 'Usuario no es superadministrador', 'User', 'is_superuser', 0, 1, '1', now(), null);

insert into sys_role_data_scope (id, role_id, data_scope_id)
values
(1, 1, 1),
(2, 1, 2);

insert into sys_data_scope_rule (id, data_scope_id, data_rule_id)
values
(1, 1, 1),
(2, 2, 2),
(3, 2, 3),
(4, 3, 4),
(5, 4, 5),
(6, 5, 6);

select setval(pg_get_serial_sequence('sys_dept', 'id'),coalesce(max(id), 0) + 1, true) from sys_dept;
select setval(pg_get_serial_sequence('sys_menu', 'id'),coalesce(max(id), 0) + 1, true) from sys_menu;
select setval(pg_get_serial_sequence('sys_role', 'id'),coalesce(max(id), 0) + 1, true) from sys_role;
select setval(pg_get_serial_sequence('sys_role_menu', 'id'),coalesce(max(id), 0) + 1, true) from sys_role_menu;
select setval(pg_get_serial_sequence('sys_user', 'id'),coalesce(max(id), 0) + 1, true) from sys_user;
select setval(pg_get_serial_sequence('sys_user_role', 'id'),coalesce(max(id), 0) + 1, true) from sys_user_role;
select setval(pg_get_serial_sequence('sys_data_scope', 'id'),coalesce(max(id), 0) + 1, true) from sys_data_scope;
select setval(pg_get_serial_sequence('sys_data_rule', 'id'),coalesce(max(id), 0) + 1, true) from sys_data_rule;
select setval(pg_get_serial_sequence('sys_role_data_scope', 'id'),coalesce(max(id), 0) + 1, true) from sys_role_data_scope;
select setval(pg_get_serial_sequence('sys_data_scope_rule', 'id'),coalesce(max(id), 0) + 1, true) from sys_data_scope_rule;

package abs.rbac.authz

import future.keywords.if
import future.keywords.in

# Пакет: abs.rbac.authz (Rego v0 синтаксис, для OPA 0.59.0)
# URL для вызова: POST /v1/data/abs.rbac.authz/allow
# Соответствует: saas-onboarding-flow.md §4, iam-deploy-runbook.md §1.3
#
# Authz-логика:
# 1) Тенант активен (data.tenants[input.tenant_id].status == "active")
# 2) У пользователя есть хотя бы одна роль из input.user_roles
# 3) Эта роль разрешает запрошенный (method, path) через match_endpoint

default allow := false

allow if {
	is_tenant_active
	some user_role in input.user_roles
	allowed_endpoints := data.tenants[input.tenant_id].roles[user_role].allowed_methods
	some endpoint in allowed_endpoints
	match_endpoint(endpoint, input.method, input.path)
}

# Проверка активности тенанта
is_tenant_active if {
	data.tenants[input.tenant_id].status == "active"
}

# ----------------------------------------------------------------
# match_endpoint — сопоставление endpoint с паттерном из allowed_methods
# ----------------------------------------------------------------

# Точное совпадение: "GET /api/v1/accounts" == "GET /api/v1/accounts"
match_endpoint(endpoint, method, path) if {
	endpoint == sprintf("%s %s", [method, path])
}

# Catch-all: "*" разрешает любой endpoint
match_endpoint("*", _, _) if true

# Wildcard в конце: "GET /api/v1/accounts/*" → "GET /api/v1/accounts/123"
match_endpoint(endpoint, method, path) if {
	endswith(endpoint, "*")
	prefix := trim_suffix(endpoint, "*")
	startswith(sprintf("%s %s", [method, path]), prefix)
}

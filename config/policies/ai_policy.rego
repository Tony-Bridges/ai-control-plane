package ai_control

import future.keywords

# Policy versioning
policy_version = "3.1.7"
policy_effective_date = "2024-01-15"

# Default deny
default allow = false

# ======================
# Risk-based decisions
# ======================

# Critical risk - always block unless security department
block {
    input.request.risk_score > 70
    input.context.department != "security"
    action := "BLOCK"
    reason := "Critical risk threshold exceeded"
}

# Security department override for investigations
allow {
    input.request.risk_score > 70
    input.context.department == "security"
    input.context.purpose == "investigation"
    action := "ALLOW_WITH_AUDIT"
    reason := "Security investigation override"
}

# ======================
# Department-specific policies
# ======================

# HR policies
hr_block {
    input.context.department == "hr"
    input.request.classification == "employee"
    input.request.risk_score > 50
    action := "BLOCK"
    reason := "HR employee data protection"
}

hr_mask {
    input.context.department == "hr"
    input.request.classification == "employee"
    input.request.risk_score > 30
    input.request.risk_score <= 50
    action := "MASK"
    reason := "HR data masking required"
}

# Legal department - local model only
legal_local_only {
    input.context.department == "legal"
    input.request.classification in ["medical", "financial", "employee"]
    action := "ALLOW"
    model := "local_llama"
    reason := "Legal data must stay on-premise"
}

# Finance department - approved models only
finance_allowed_models = {"azure_openai", "local_llama"}

finance_model_check {
    input.context.department == "finance"
    not finance_allowed_models[input.model_preference]
    action := "BLOCK"
    reason := sprintf("Finance department cannot use model: %s", [input.model_preference])
}

# Medical data - strict control
medical_block {
    input.request.classification == "medical"
    input.request.contains_sa_id == true
    action := "BLOCK"
    reason := "Medical data with SA ID prohibited"
}

medical_anonymize {
    input.request.classification == "medical"
    input.request.risk_score > 30
    input.request.contains_sa_id == false
    action := "ANONYMIZE"
    model := "local_llama"
    reason := "Medical data must be anonymized and kept local"
}

# ======================
# Multi-tenant policies
# ======================

# Tenant isolation
tenant_policy {
    input.context.tenant_id
    tenant_policies[input.context.tenant_id][input.request.classification]
}

tenant_policies = {
    "tenant_a": {
        "general": {"action": "ALLOW", "model": "openai", "max_risk": 50},
        "financial": {"action": "ANONYMIZE", "model": "azure_openai", "max_risk": 70},
        "medical": {"action": "BLOCK", "model": "local_llama", "max_risk": 0}
    },
    "tenant_b": {
        "general": {"action": "ALLOW", "model": "azure_openai", "max_risk": 70},
        "financial": {"action": "ALLOW", "model": "azure_openai", "max_risk": 80},
        "medical": {"action": "MASK", "model": "local_llama", "max_risk": 50}
    },
    "tenant_c": {
        "general": {"action": "ALLOW", "model": "anthropic", "max_risk": 60},
        "financial": {"action": "ALLOW", "model": "anthropic", "max_risk": 70},
        "medical": {"action": "BLOCK", "model": "local_llama", "max_risk": 0}
    }
}

# ======================
# Cost-aware routing
# ======================

# Model cost tiers (per 1k tokens)
model_costs = {
    "openai": 0.03,
    "azure_openai": 0.025,
    "anthropic": 0.035,
    "local_llama": 0.005
}

# Route based on cost constraints
cost_routing {
    input.context.cost_constraint
    max_cost := input.context.cost_constraint
    model := model_costs[key] <= max_cost
    action := "ALLOW"
}

# ======================
# Latency-aware routing
# ======================

# Route based on latency requirements
latency_routing {
    input.context.max_latency_ms < 1000
    model := "local_llama"
    action := "ALLOW"
}

latency_routing {
    input.context.max_latency_ms < 5000
    model := "azure_openai"
    action := "ALLOW"
}

latency_routing {
    input.context.max_latency_ms >= 5000
    model := "anthropic"
    action := "ALLOW"
}

# ======================
# Geo-region policies
# ======================

# Data residency
geo_policy {
    input.context.region == "EU"
    input.model_preference in ["openai", "anthropic"]
    action := "BLOCK"
    reason := "EU data cannot use non-compliant models"
}

geo_policy {
    input.context.region == "ZA"
    model := "local_llama"
    action := "ALLOW"
    reason := "SA data must stay local"
}

# ======================
# Audit and compliance
# ======================

# Force audit for all high-risk
audit_required {
    input.request.risk_score > 50
    audit_level := "full"
}

audit_required {
    input.request.classification in ["medical", "financial"]
    audit_level := "full"
}

audit_required {
    input.context.department in ["hr", "legal"]
    audit_level := "summary"
}

# ======================
# Policy version tracking
# ======================

# Include policy version in decisions
policy_info = {
    "version": policy_version,
    "effective_date": policy_effective_date,
    "policy_hash": crypto.sha256(policy_version)
}

# Decision tracking
decision {
    action := "ALLOW"
    model := "openai"
    policy_applied := "default_allow"
    policy_version := policy_version
    reason := "No restrictive policies matched"
}

# ======================
# Advanced rules
# ======================

# Time-based policies
time_restriction {
    hour := time.now().hour()
    hour < 9 or hour > 17
    input.context.department in ["finance", "legal"]
    action := "BLOCK"
    reason := "Financial operations only allowed during business hours"
}

# Rate limiting per tenant
tenant_rate_limit {
    input.context.tenant_id
    rate_limits[input.context.tenant_id] < 100
    action := "ALLOW"
}

rate_limits = {
    "tenant_a": 50,  # requests per minute
    "tenant_b": 100,
    "tenant_c": 25
}

# Compliance checks
compliance_required {
    input.request.classification in ["medical", "financial"]
    input.context.compliance_approved != true
    action := "BLOCK"
    reason := "Compliance approval required"
}

# ======================
# Context-preserving tokenization rules
# ======================

# Maintain relationships in tokenization
tokenization_rules {
    input.request.classification in ["employee", "financial"]
    preserve_context := true
    tokenization_level := "medium"
}

# For medical, preserve relationships but anonymize values
tokenization_rules {
    input.request.classification == "medical"
    preserve_context := true
    tokenization_level := "high"
}
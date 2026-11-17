"""
verification/docs_data/role_capability_matrix.py

Ground truth: what each of the 7 roles can View/Create/Update/Delete per
feature, AFTER the t0.2.0 dojo/owner-scoping fixes (apps/members, events,
activities, skills views.py). This records ACTUAL code behavior, not the
original aspirational Blueprint-derived proposal — see matrix_diff_report.py
for every place those two still diverge.

Scope values:
  'ALL'  — unfiltered, sees all org-wide data
  'DOJO' — filtered to the coach's own DojoStaff-linked dojo(s)
  'OWN'  — filtered to the request.user's own MemberProfile-linked rows
  None   — no access (403)

CAPABILITY_MATRIX is keyed by "app:view_name" (matches Django url names).
Each row's dict has one entry per of the 7 roles, plus a "verb" key
('V'=view list/detail, 'C'=create, 'U'=update, 'D'=delete).
"""

CAPABILITY_MATRIX = {
    # --- members ---
    "members:member_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": "DOJO", "MEMBER": None, "PARENT": None,
    },
    "members:member_detail": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": "DOJO", "MEMBER": None, "PARENT": None,
    },
    "members:member_edit": {
        "verb": "U",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": None, "MEMBER": None, "PARENT": None,
    },

    # --- events ---
    "events:event_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "DOJO", "MEMBER": "ALL", "PARENT": "ALL",
    },
    "events:event_detail": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "DOJO", "MEMBER": "ALL", "PARENT": "ALL",
    },
    "events:event_create": {
        "verb": "C",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": None, "MEMBER": None, "PARENT": None,
    },

    # --- activities ---
    "activities:activity_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "DOJO", "MEMBER": "ALL", "PARENT": "ALL",
    },
    "activities:activity_detail": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "DOJO", "MEMBER": "ALL", "PARENT": "ALL",
    },

    # --- skills ---
    "skills:skill_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "DOJO", "MEMBER": "OWN", "PARENT": "OWN",
    },

    # --- dojos (unchanged — non-sensitive reference data, see diff report) ---
    "dojos:dojo_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "ALL", "MEMBER": "ALL", "PARENT": "ALL",
    },
    "dojos:dojo_detail": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "ALL", "MEMBER": "ALL", "PARENT": "ALL",
    },

    # --- fees (unchanged — accepted gap, see diff report) ---
    "fees:fee_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": None, "MEMBER": None, "PARENT": None,
    },

    # --- payments (unchanged — accepted gap, see diff report) ---
    "payments:payment_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": None, "MEMBER": None, "PARENT": None,
    },

    # --- communications (stub — see diff report) ---
    "communications:inbox": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": None, "COACH": None, "MEMBER": None, "PARENT": None,
    },

    # --- cms ---
    "cms:page_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": None,
        "EDITOR": "ALL", "COACH": None, "MEMBER": None, "PARENT": None,
    },
    "cms:page_edit": {
        "verb": "U",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": None,
        "EDITOR": "ALL", "COACH": None, "MEMBER": None, "PARENT": None,
    },

    # --- matches (unchanged — Tournament is not member-owned, see diff report) ---
    "matches:match_list": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "ALL", "MEMBER": "ALL", "PARENT": "ALL",
    },
    "matches:match_detail": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "ALL", "MEMBER": "ALL", "PARENT": "ALL",
    },

    # --- chatbot (stub — see diff report) ---
    "chatbot:chatbot": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "ALL", "MEMBER": "ALL", "PARENT": "ALL",
    },

    # --- accounts (dashboard — always own-role-scoped by design, not a gap) ---
    "accounts:dashboard": {
        "verb": "V",
        "GRANDMASTER": "ALL", "DEPUTY_GRANDMASTER": "ALL", "ADMIN": "ALL",
        "EDITOR": "ALL", "COACH": "DOJO", "MEMBER": "OWN", "PARENT": "OWN",
    },
}

# One canonical login username per role — decouples pure role-level RBAC
# checks (test_rbac_matrix.py, unchanged from t0.1.0) from the fact that
# COACH/MEMBER/PARENT now have multiple personas in test_credentials.csv v2.
PRIMARY_USERNAME_BY_ROLE = {
    "GRANDMASTER": "test_grandmaster",
    "DEPUTY_GRANDMASTER": "test_deputy_grandmaster",
    "ADMIN": "test_admin",
    "EDITOR": "test_editor",
    "COACH": "test_coach_a",
    "MEMBER": "test_member_a1",
    "PARENT": "test_parent_a",
}

# Views with a real Create/Update/Delete verb — used by test_rbac_write_matrix.py
# so allowed roles are read from this file, not re-hardcoded per test.
WRITE_VIEWS = {
    "events:event_create": "C",
    "members:member_edit": "U",
    "cms:page_edit": "U",
}


def allowed_roles_for(view_name: str) -> set[str]:
    """Roles with any non-None scope for the given view_name."""
    row = CAPABILITY_MATRIX[view_name]
    return {role for role in PRIMARY_USERNAME_BY_ROLE if row.get(role) is not None}

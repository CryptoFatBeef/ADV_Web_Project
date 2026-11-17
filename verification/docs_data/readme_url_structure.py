"""
verification/docs_data/readme_url_structure.py

Ground truth: URL structure documented in README.md.

NOTE ON APP COUNT: README.md Changelog refers to "12 apps" — that figure is
the pre-v0.3.1 scope (before public + enrollment were added). The authoritative
current count is 14 apps per the Architecture tree (see test_installed_app_count_matches_docs).
The "12 apps" figure in the Changelog is NOT updated — it describes the historical
scope at v0.1.0–v0.3.0, not the current total.

Format: list of (url_name, expected_path) tuples.
url_name uses Django's namespaced URL name format ("namespace:view_name").
"""

PUBLIC_URLS = [
    ("public:home",           "/"),
    ("public:about",          "/about/"),
    ("public:instructors",    "/instructors/"),
    ("public:dojo_list",      "/our-dojos/"),
    ("public:news_list",      "/news/"),
    ("public:showcase_list",  "/showcase/"),
    ("public:robots_txt",     "/robots.txt"),
]

AUTH_URLS = [
    ("accounts:login",     "/accounts/login/"),
    ("accounts:logout",    "/accounts/logout/"),
    ("accounts:dashboard", "/accounts/dashboard/"),
    ("accounts:profile",   "/accounts/profile/"),
]

# CRM route prefixes (path prefixes only; specific view names confirmed per-app)
CRM_ROUTE_PREFIXES = [
    "members/",
    "dojos/",
    "events/",
    "activities/",
    "skills/",
    "fees/",
    "payments/",
    "communications/",
    "cms/",
    "matches/",
    "chatbot/",
]

ENROLLMENT_URLS = [
    ("enrollment:enroll", "/enroll/"),
]

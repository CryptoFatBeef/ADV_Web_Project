"""
verification/docs_data/matrix_diff_report.py

Every place the original aspirational Role Capability Matrix proposal
(Blueprint-derived, written before code was verified) still diverges from
the ACTUAL code behavior recorded in role_capability_matrix.py, after the
t0.2.0 dojo/owner-scoping fixes. Logged explicitly per the project rule:
matrix-vs-code diffs are never resolved by silently editing the matrix —
every row here is a decision, not an oversight.

Run `python -m verification.docs_data.matrix_diff_report` to (re)generate
verification/reports/matrix_diff_report.md from this data.
"""
from dataclasses import dataclass


@dataclass
class DiffRow:
    feature: str
    proposed: str
    actual: str
    status: str


DIFF_ROWS = [
    DiffRow(
        feature="members",
        proposed="EDITOR=-, COACH=V:DOJO (create/delete unimplemented)",
        actual="COACH=DOJO (fixed this pass); no Create/Delete view exists for MemberProfile anywhere",
        status="Partially fixed — scoping added; Create/Delete remain unimplemented, future work",
    ),
    DiffRow(
        feature="member_skills (skills)",
        proposed="COACH=CU:DOJO, MEMBER/PARENT=V:OWN",
        actual="COACH=DOJO, MEMBER/PARENT=OWN (view-scoping fixed this pass); no Create/Update view exists, no DetailView at all",
        status="Partially fixed — list-level scoping added; still fully read-only (list-only)",
    ),
    DiffRow(
        feature="dojos",
        proposed="COACH=V:OWN, MEMBER/PARENT=V",
        actual="ALL roles=ALL (unchanged)",
        status="Accepted gap — dojo directory data (name/address/district/phone) is non-sensitive reference data; restricting COACH from seeing other dojos has low security value, not worth the added complexity",
    ),
    DiffRow(
        feature="events",
        proposed="COACH=VCU:DOJO",
        actual="COACH=DOJO for list/detail (fixed this pass); Create stays ADMIN_ROLES-only (COACH cannot create); no Update/Delete view exists",
        status="Partially fixed — view-level scoping added; Create/Update/Delete gaps remain, future work",
    ),
    DiffRow(
        feature="attendance",
        proposed="COACH=CU:DOJO, MEMBER/PARENT=V:OWN",
        actual="No web view exists at all for AttendanceLog — admin-only",
        status="Accepted gap — building a new view is out of scope for a scoping-only pass; future work",
    ),
    DiffRow(
        feature="activities_apps",
        proposed="COACH=VU:DOJO, MEMBER/PARENT=VC:OWN",
        actual="COACH=DOJO for the ActivityEvent-level list/detail (fixed this pass); the true per-member ActivityApplication (FSM) model has no web view at all — MEMBER/PARENT scoping doesn't apply to anything that exists",
        status="Partially fixed — ActivityEvent scoping added; ActivityApplication CRUD/scoping is a new-view gap, future work",
    ),
    DiffRow(
        feature="fees_invoices",
        proposed="COACH=V:DOJO, MEMBER/PARENT=V:OWN",
        actual="ADMIN_ROLES only — COACH/MEMBER/PARENT get 403, no access at all",
        status="Accepted gap — granting MEMBER/PARENT access requires expanding the roles=[] list (an access-policy change, not just get_queryset scoping) plus a template review; out of scope this pass",
    ),
    DiffRow(
        feature="payments",
        proposed="MEMBER/PARENT=C:OWN",
        actual="ADMIN_ROLES only — no Create view exists at all; members cannot self-serve submit a payment via any view",
        status="Accepted gap — same reasoning as fees; also needs a new Create view/form, not just scoping",
    ),
    DiffRow(
        feature="communications",
        proposed="GM/DGM/ADMIN=VCUD, COACH=C:DOJO, MEMBER/PARENT=V:OWN",
        actual="Literal 'coming soon' TemplateView stub, ADMIN_ROLES-gated, no model-backed CRUD of any kind",
        status="Not applicable — nothing exists yet to scope; feature build-out is a separate task",
    ),
    DiffRow(
        feature="cms_content",
        proposed="GM/DGM/ADMIN/EDITOR=VCUD",
        actual="EDITOR_ROLES=['GRANDMASTER','DEPUTY_GRANDMASTER','EDITOR'] — ADMIN is explicitly excluded from cms; no Create/Delete view exists",
        status="Documented — ADMIN's exclusion from cms appears intentional (editorial content is EDITOR's domain) but diverges from the proposal; Create/Delete remain unimplemented",
    ),
    DiffRow(
        feature="matches",
        proposed="MEMBER/PARENT=V:OWN",
        actual="ALL roles=ALL (unchanged) — confirmed MatchListView/MatchDetailView both use model=Tournament, not MatchEntry",
        status="Accepted gap — a Tournament isn't owned by one member; true fix needs a new MatchEntry-level view (out of scope, no new views this pass). A small optional context-only my_entries addition to MatchDetailView was considered and explicitly declined for this pass.",
    ),
    DiffRow(
        feature="chatbot_faq",
        proposed="GM/DGM/ADMIN/EDITOR=VCUD",
        actual="Literal 'coming soon' TemplateView stub, zero role restriction (any authenticated role), no model-backed CRUD",
        status="Not applicable — nothing exists yet to scope; feature build-out is a separate task",
    ),
    DiffRow(
        feature="user_accounts",
        proposed="MEMBER/PARENT=U:OWN",
        actual="Dashboard/Profile are TemplateViews only; no real user list/create/update/delete view exists for admins, and no self-service profile-edit form exists for members either",
        status="Accepted gap — building profile-edit and admin user-management views is out of scope for a scoping-only pass",
    ),
    DiffRow(
        feature="MemberProfile.status access control",
        proposed="(implied) SUSPENDED members should be denied some access; INACTIVE affects visibility",
        actual="No code anywhere gates access by MemberProfile.status — RoleRequiredMixin only ever checks request.user.role. A SUSPENDED or INACTIVE member can log in and view their own dashboard exactly like an ACTIVE member.",
        status="Documented gap — exercised by a canary asserting CURRENT (non-denying) behavior in test_object_level_access.py, not fixed; implementing status-based denial needs its own design decisions (where/how to enforce) out of scope here",
    ),
]


def render_markdown() -> str:
    lines = [
        "# Role Capability Matrix — Diff Report",
        "",
        "Generated from `verification/docs_data/matrix_diff_report.py`. "
        "Every row here is a logged decision, not a silent resolution — see "
        "`verification/docs_data/role_capability_matrix.py` for the code-accurate matrix.",
        "",
        "| Feature | Proposed | Actual (t0.2.0) | Status |",
        "|---|---|---|---|",
    ]
    for row in DIFF_ROWS:
        lines.append(f"| {row.feature} | {row.proposed} | {row.actual} | {row.status} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    from pathlib import Path

    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "matrix_diff_report.md"
    out_path.write_text(render_markdown(), encoding="utf-8")
    print(f"Written {len(DIFF_ROWS)} diff rows → {out_path}")


if __name__ == "__main__":
    main()

"""Every status vocabulary in one place, mirroring PRD section 4."""

from __future__ import annotations

from enum import StrEnum


class ActorType(StrEnum):
    """Who is acting. Three identities, each with its own email+password.

    Platform staff are deliberately a separate table from company users: a bug
    in company scoping should never be able to escalate into cross-tenant access.
    """

    PLATFORM = "platform"
    COMPANY_USER = "company_user"
    PARTICIPANT = "participant"


class AccountActionPurpose(StrEnum):
    """What a one-time AccountActionToken is for. Never login — passwords do
    that; these cover the two moments a live session cannot."""

    SET_PASSWORD = "set_password"
    RESET_PASSWORD = "reset_password"


class PlatformRole(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"


class CompanyTier(StrEnum):
    SME = "sme"
    MIDMARKET = "midmarket"
    ENTERPRISE = "enterprise"


class CompanyUserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    REP = "rep"
    VIEWER = "viewer"


class CompanyUserStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class DeliveryMode(StrEnum):
    ONLINE = "online"
    IN_PERSON = "in_person"
    HYBRID = "hybrid"


class ProgrammeStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    SELECTING = "selecting"
    CONFIRMED = "confirmed"
    RUNNING = "running"
    SUBMITTED = "submitted"
    JUDGING = "judging"
    COMPLETE = "complete"


class Provenance(StrEnum):
    PUBLIC = "public"
    COMPANY_SUPPLIED = "company_supplied"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"


class AccessStatus(StrEnum):
    OK = "ok"
    DENIED = "denied"
    NOT_FOUND = "not_found"
    UNCHECKED = "unchecked"


class OrgType(StrEnum):
    SCHOOL = "school"
    COMPANY = "company"
    ASSOCIATION = "association"


class ApplicationStatus(StrEnum):
    SUBMITTED = "submitted"
    SCREENED = "screened"
    OFFERED = "offered"
    WAITLISTED = "waitlisted"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class ParticipantStatus(StrEnum):
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    NO_SUBMISSION = "no_submission"
    PITCHED = "pitched"
    CLOSED = "closed"


class SubmissionStatus(StrEnum):
    DRAFT = "draft"
    COMPLETE = "complete"
    LOCKED = "locked"


class SubmissionSlot(StrEnum):
    ARTIFACT = "artifact"
    MEMO = "memo"
    EXTRA = "extra"


class SnapshotStatus(StrEnum):
    PENDING = "pending"
    OK = "ok"
    FAILED = "failed"


class ScorerType(StrEnum):
    REP = "rep"
    JUDGE = "judge"
    MENTOR = "mentor"


class ReferralIntent(StrEnum):
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"


class SkillType(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class SkillStatus(StrEnum):
    CANONICAL = "canonical"
    PENDING_REVIEW = "pending_review"


class ThreadType(StrEnum):
    ANNOUNCEMENT = "announcement"
    RESOURCE = "resource"
    QUESTION_CHALLENGE = "question_challenge"
    QUESTION_LOGISTICS = "question_logistics"
    DIRECT = "direct"


class ThreadStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"


class AuthorRole(StrEnum):
    ADMIN = "admin"
    REP = "rep"
    PARTICIPANT = "participant"


class CredentialType(StrEnum):
    COMPLETION = "completion"
    TOP_PERFORMER = "top_performer"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class OutboxSubjectType(StrEnum):
    """Deviation from PRD section 4: the outbox subject is polymorphic.

    Offer, waitlist and rejection emails fire while the subject is still an
    Application, and an account-action email has no participant at all, so
    keying idempotency on participant_id alone cannot express those effects.
    """

    PARTICIPANT = "participant"
    APPLICATION = "application"
    COMPANY_USER = "company_user"
    PROGRAMME = "programme"
    SUBMISSION_LINK = "submission_link"
    ACCOUNT_ACTION = "account_action"


class ProjectKind(StrEnum):
    """Where a piece of work came from.

    PROGRAMME is the only kind the platform can vouch for by itself; the rest
    are the participant's own account of work done elsewhere, which is why the
    two are counted and ordered separately on a profile.
    """

    PROGRAMME = "programme"
    HACKATHON = "hackathon"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    COMPETITION = "competition"
    INDEPENDENT = "independent"


class ProjectLinkKind(StrEnum):
    GITHUB = "github"
    DEMO = "demo"
    VIDEO = "video"
    DECK = "deck"
    DOC = "doc"
    BRIEF = "brief"


class ArtifactVisibility(StrEnum):
    """Per-project consent for showing the work itself.

    Deliberately not inherited from Application.consent_share_company: that
    consent was given to one company for one week of judging, and a public
    profile is a different audience for an indefinite time. PRIVATE is the
    default, so an artifact becomes visible only by an explicit act.
    """

    PRIVATE = "private"
    LINK_ONLY = "link_only"
    PUBLIC = "public"

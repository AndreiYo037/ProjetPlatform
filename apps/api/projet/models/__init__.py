"""All ORM models, re-exported so metadata is complete on a single import."""

from projet.models.auth import AccountActionToken, AuthSession, PlatformUser
from projet.models.company import (
    AuditLog,
    Company,
    CompanyUser,
    ProgrammeAssignment,
)
from projet.models.messaging import Attachment, Post, Thread, ThreadMember, ThreadRead
from projet.models.ops import Outbox
from projet.models.people import (
    Application,
    Participant,
    Person,
    Team,
    TeamMember,
    normalise_email,
)
from projet.models.portfolio import ProjectEntry, ProjectLink, ProjectSkill
from projet.models.profile import Credential, ProfileSkill, Testimonial
from projet.models.programme import (
    DataPackResource,
    Event,
    JudgingSession,
    ProblemStatementDraft,
    Programme,
    ProgrammeRole,
    RubricCriterion,
)
from projet.models.scoring import CriterionScore, Score, ScoreMember, ScoreSkillTag
from projet.models.submission import Submission, SubmissionLink
from projet.models.taxonomy import (
    Capability,
    Role,
    RoleTemplate,
    Skill,
    SkillCapability,
)

__all__ = [
    "Application",
    "AccountActionToken",
    "Attachment",
    "AuditLog",
    "AuthSession",
    "Capability",
    "Company",
    "CompanyUser",
    "Credential",
    "CriterionScore",
    "DataPackResource",
    "Event",
    "JudgingSession",
    "Outbox",
    "Participant",
    "Person",
    "PlatformUser",
    "ProblemStatementDraft",
    "Post",
    "ProfileSkill",
    "Programme",
    "ProgrammeAssignment",
    "ProgrammeRole",
    "ProjectEntry",
    "ProjectLink",
    "ProjectSkill",
    "Role",
    "RoleTemplate",
    "RubricCriterion",
    "Score",
    "ScoreMember",
    "ScoreSkillTag",
    "Skill",
    "SkillCapability",
    "Submission",
    "SubmissionLink",
    "Team",
    "TeamMember",
    "Testimonial",
    "Thread",
    "ThreadMember",
    "ThreadRead",
    "normalise_email",
]

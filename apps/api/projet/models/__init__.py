"""All ORM models, re-exported so metadata is complete on a single import."""

from projet.models.company import (
    AuditLog,
    Company,
    CompanyUser,
    MagicLinkToken,
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
from projet.models.profile import Credential, ProfileSkill, Testimonial
from projet.models.programme import (
    DataPackResource,
    Event,
    JudgingSession,
    Programme,
    RubricCriterion,
)
from projet.models.scoring import CriterionScore, Score, ScoreMember, ScoreSkillTag
from projet.models.submission import Submission, SubmissionLink
from projet.models.taxonomy import Role, RoleTemplate, Skill

__all__ = [
    "Application",
    "Attachment",
    "AuditLog",
    "Company",
    "CompanyUser",
    "Credential",
    "CriterionScore",
    "DataPackResource",
    "Event",
    "JudgingSession",
    "MagicLinkToken",
    "Outbox",
    "Participant",
    "Person",
    "Post",
    "ProfileSkill",
    "Programme",
    "ProgrammeAssignment",
    "Role",
    "RoleTemplate",
    "RubricCriterion",
    "Score",
    "ScoreMember",
    "ScoreSkillTag",
    "Skill",
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

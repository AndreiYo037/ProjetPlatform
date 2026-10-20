"""The durable product: credentials, judge-attested skills, testimonials."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from projet.db import Base
from projet.models.base import JSONList, TimestampTZ, enum_column, utcnow, uuid_pk
from projet.models.enums import CredentialType


class Credential(Base):
    __tablename__ = "credential"
    __table_args__ = (UniqueConstraint("person_id", "programme_id", "type"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id"))
    type: Mapped[CredentialType] = mapped_column(enum_column(CredentialType))
    verify_code: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class Certificate(Base):
    """What a team is given for taking part: one per team, printed with every
    member's name together. Merit or Completion; a company can also give a
    placing ("3rd Place") on top of Merit.

    Separate from Credential on purpose. A credential is per person and rides
    on the profile; a certificate is a document for the whole team, and its
    teammates may not have a Projet account at all, so the names it prints are
    stored on the row rather than derived from accounts.
    """

    __tablename__ = "certificate"
    __table_args__ = (UniqueConstraint("programme_id", "team_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id"))
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"))
    tier: Mapped[str] = mapped_column(String(20))
    place_label: Mapped[str | None] = mapped_column(String(40))
    rank: Mapped[int | None] = mapped_column(Integer)
    entries: Mapped[int | None] = mapped_column(Integer)
    names: Mapped[list[str]] = mapped_column(JSONList)
    # Persons who can see and download it. String ids, since it is a JSON list.
    recipient_person_ids: Mapped[list[str]] = mapped_column(JSONList)
    applied_teams: Mapped[int | None] = mapped_column(Integer)
    submitted_teams: Mapped[int | None] = mapped_column(Integer)
    event_name: Mapped[str | None] = mapped_column(String(120))
    event_date: Mapped[str | None] = mapped_column(String(40))
    pdf_storage_key: Mapped[str | None] = mapped_column(String(300))
    issued_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class ProfileSkill(Base):
    """FR-903d — judge-attested, not self-declared. The attestation carries the
    name, title and company of the practitioner who tagged it, which is what
    makes it materially stronger than a self-reported skill."""

    __tablename__ = "profile_skill"
    __table_args__ = (UniqueConstraint("person_id", "programme_id", "skill_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    programme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programme.id"))
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skill.id"))
    attested_by_name: Mapped[str | None] = mapped_column(String(200))
    attested_by_title: Mapped[str | None] = mapped_column(String(200))
    attested_by_company: Mapped[str | None] = mapped_column(String(200))
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)


class Testimonial(Base):
    """FR-1053 — authored on the submissions dashboard, with no link to Score."""

    __tablename__ = "testimonial"

    id: Mapped[uuid.UUID] = uuid_pk()
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE")
    )
    author_company_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_user.id"))
    body: Mapped[str] = mapped_column(Text)
    # The signed letter. Drafting fills `body`; publishing requires this file.
    pdf_storage_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TimestampTZ, default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(TimestampTZ)

    # The letter's own parts, each a box on the judging page. recipients are the
    # names on the Re: line (a team has several); the sign-off is who the letter
    # is from; company_details is the address, website and email beneath it.
    recipients: Mapped[list[str] | None] = mapped_column(JSONList)
    signoff_name: Mapped[str | None] = mapped_column(String(200))
    signoff_title: Mapped[str | None] = mapped_column(String(200))
    signoff_company: Mapped[str | None] = mapped_column(String(200))
    company_details: Mapped[str | None] = mapped_column(Text)

    # The e-signature. A letter is signed against the exact wording: body_hash
    # is the SHA-256 of the text at the moment of signing, so any later edit
    # makes the signature stop matching and it is cleared.
    signed_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    signed_name: Mapped[str | None] = mapped_column(String(200))
    signed_title: Mapped[str | None] = mapped_column(String(200))
    signature_key: Mapped[str | None] = mapped_column(Text)
    # True when the signer typed their name instead of drawing one.
    signature_typed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    body_hash: Mapped[str | None] = mapped_column(String(64))
    signed_ip: Mapped[str | None] = mapped_column(String(64))
    signed_user_agent: Mapped[str | None] = mapped_column(Text)

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_mixin, declared_attr, relationship
from sqlalchemy.sql import func

from utils.uuidv7 import uuid7_pk

from .cognine_models import Base


# Abstract Model for audit fields
@declarative_mixin
class ModifyModel:
    """Abstract model with audit fields for tracking creation and modification"""

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Employee references for audit trail
    @declared_attr
    def created_by(cls):
        return Column(Integer, ForeignKey("public.employee.id"), nullable=True)

    @declared_attr
    def updated_by(cls):
        return Column(Integer, ForeignKey("public.employee.id"), nullable=True)

    # Relationships to Employee for audit
    @property
    def creator(self):
        return relationship("Employee", foreign_keys=[self.created_by], post_update=True)

    @property
    def updater(self):
        return relationship("Employee", foreign_keys=[self.updated_by], post_update=True)


class MasterData(ModifyModel, Base):
    __tablename__ = "master_data"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    isactive = Column(Boolean, nullable=False, default=True)

    # Relationships
    employee_roles = relationship("EmployeeRoleMapping", back_populates="role")


class EmployeeRoleMapping(ModifyModel, Base):
    """Employee Role Mapping model for many-to-many relationship"""

    __tablename__ = "employee_role_mappings"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    employee_id = Column(Integer, ForeignKey("public.employee.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("AUDIT.master_data.id"), nullable=False)
    isactive = Column(Boolean, nullable=False, default=True)

    # Relationships
    role = relationship("MasterData", foreign_keys=[role_id], back_populates="employee_roles")


class AuditTemplate(ModifyModel, Base):
    __tablename__ = "audit_templates"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    name = Column(String(255), nullable=False)
    isactive = Column(Boolean, nullable=False, default=True)

    areas = relationship("AuditArea", back_populates="template", order_by="AuditArea.created_at")


class AuditArea(ModifyModel, Base):
    __tablename__ = "audit_areas"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    template_id = Column(UUID, ForeignKey("AUDIT.audit_templates.id"), nullable=False)
    name = Column(String(255), nullable=False)
    weightage = Column(Integer, nullable=False)
    isactive = Column(Boolean, nullable=False, default=True)

    template = relationship("AuditTemplate", back_populates="areas")
    scopes = relationship("AuditScope", back_populates="area", order_by="AuditScope.created_at")


class AuditScope(ModifyModel, Base):
    __tablename__ = "audit_scopes"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    area_id = Column(UUID, ForeignKey("AUDIT.audit_areas.id"), nullable=False)
    name = Column(String(255), nullable=False)
    isactive = Column(Boolean, nullable=False, default=True)

    area = relationship("AuditArea", back_populates="scopes")
    questions = relationship("AuditQuestion", back_populates="scope")


class AuditQuestion(ModifyModel, Base):
    __tablename__ = "audit_questions"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    scope_id = Column(UUID, ForeignKey("AUDIT.audit_scopes.id"), nullable=False)
    text = Column(Text, nullable=False)
    percentage = Column(Integer, nullable=False)
    is_mandatory = Column(Boolean, default=True)
    isactive = Column(Boolean, nullable=False, default=True)

    scope = relationship("AuditScope", back_populates="questions")
    options = relationship(
        "AuditQuestionOption", back_populates="question", order_by="AuditQuestionOption.created_at"
    )


class AuditQuestionOption(ModifyModel, Base):
    __tablename__ = "audit_question_options"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    question_id = Column(UUID, ForeignKey("AUDIT.audit_questions.id"), nullable=False)
    label = Column(String(255), nullable=False)
    value = Column(Integer, nullable=False)
    isactive = Column(Boolean, nullable=False, default=True)

    question = relationship("AuditQuestion", back_populates="options")


class Audit(Base, ModifyModel):
    __tablename__ = "audits"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)

    project_id = Column(Integer, ForeignKey("public.projects.id"), nullable=False)
    template_id = Column(UUID, ForeignKey("AUDIT.audit_templates.id"), nullable=False)

    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)  # Draft/Scheduled/InProgress/Completed/Closed

    overall_score = Column(Integer)
    rag_status = Column(String(10))
    isactive = Column(Boolean, nullable=False, default=True)

    project = relationship("Projects")
    template = relationship("AuditTemplate")


class AuditParticipant(Base, ModifyModel):
    __tablename__ = "audit_participants"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    audit_id = Column(UUID, ForeignKey("AUDIT.audits.id"))
    employee_id = Column(BigInteger, ForeignKey("public.employee.id"))
    role_type = Column(String(50))  # Auditor, Delivery, Lead, Viewer
    isactive = Column(Boolean, nullable=False, default=True)

    audit = relationship("Audit", backref="participants")


class AuditResponse(Base, ModifyModel):
    __tablename__ = "audit_responses"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)

    audit_id = Column(UUID, ForeignKey("AUDIT.audits.id"), nullable=False)
    question_id = Column(UUID, ForeignKey("AUDIT.audit_questions.id"), nullable=False)

    selected_option_id = Column(UUID, ForeignKey("AUDIT.audit_question_options.id"))
    score = Column(Integer)

    comment = Column(Text)
    recommendation = Column(Text)
    isactive = Column(Boolean, nullable=False, default=True)

    audit = relationship("Audit", backref="responses")
    question = relationship("AuditQuestion")


class AuditEvidence(Base, ModifyModel):
    __tablename__ = "audit_evidences"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    response_id = Column(UUID, ForeignKey("AUDIT.audit_responses.id"))

    evidence_type = Column(String(20))  # FILE / URL / DOCUMENT_LINK
    file_url = Column(Text)
    original_file_name = Column(String(255))
    mime_type = Column(String(100))
    isactive = Column(Boolean, nullable=False, default=True)


class AuditReportSnapshot(Base, ModifyModel):
    __tablename__ = "audit_report_snapshots"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    audit_id = Column(UUID, ForeignKey("AUDIT.audits.id"), unique=True)

    overall_score = Column(Integer)
    rag_status = Column(String(10))
    report_json = Column(JSONB)  # frozen report
    isactive = Column(Boolean, nullable=False, default=True)


class AuditActionItem(Base, ModifyModel):
    __tablename__ = "audit_action_items"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)
    audit_id = Column(UUID, ForeignKey("AUDIT.audits.id"))
    audit_question_id = Column(UUID, ForeignKey("AUDIT.audit_questions.id"), nullable=True)

    title = Column(String(255))
    description = Column(Text)
    owner_id = Column(BigInteger, ForeignKey("public.employee.id"))
    priority = Column(String(50))
    due_date = Column(Date)
    status = Column(String(50))  # Open/InProgress/Closed
    isactive = Column(Boolean, nullable=False, default=True)


class AuditProjectTemplate(Base, ModifyModel):
    __tablename__ = "audit_project_templates"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)

    project_id = Column(BigInteger, ForeignKey("public.projects.id"), nullable=False)
    template_id = Column(UUID, ForeignKey("AUDIT.audit_templates.id"), nullable=False)

    is_default = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    isactive = Column(Boolean, nullable=False, default=True)


class AuditChangeLog(Base):
    __tablename__ = "change_logs"
    __table_args__ = {"schema": "AUDIT"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7_pk)

    table_name = Column(String(150), nullable=False)
    record_id = Column(String(100), nullable=False)

    operation = Column(String(20), nullable=False)
    # INSERT | UPDATE | DELETE

    changed_by = Column(BigInteger, nullable=True)  # employee id
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    old_data = Column(JSONB)  # before change
    new_data = Column(JSONB)  # after change
    changed_fields = Column(JSONB)  # diff only
    isactive = Column(Boolean, nullable=False, default=True)

    source = Column(String(50))  # API / SYSTEM / IMPORT

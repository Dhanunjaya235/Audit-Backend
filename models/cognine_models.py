from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Employee(Base):
    __tablename__ = "employee"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True, index=True)
    employeename = Column(String(255), nullable=False)
    email = Column(Text, unique=True, nullable=False)
    doj = Column(Date)
    jobtitle = Column(Text)
    department = Column(String(255))
    reportsto = Column(Text)
    isactive = Column(Boolean, default=True)
    newreportinghead = Column(Text)

    managed_projects = relationship("ProjectManagers", back_populates="employee")
    project_resources = relationship("ProjectResources", back_populates="employee")
    pmo_projects = relationship("ProjectPMOs", back_populates="employee")
    project_tech_leads = relationship("ProjectTechLeads", back_populates="employee")


class Clients(Base):
    __tablename__ = "clients"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    clientname = Column(Text, unique=True, nullable=False)
    address = Column(Text, nullable=False)
    city = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)
    clientbillingtypeid = Column(Integer)

    projects = relationship("Projects", back_populates="client")


class Projects(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True, index=True)
    projectname = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    startdate = Column(Date, nullable=False)
    enddate = Column(Date)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)
    notes = Column(Text)
    projectaliasemail = Column(Text)
    clientid = Column(Integer, ForeignKey("public.clients.id"), nullable=False)
    hoursperday = Column(Integer, default=6)
    actualstorypoints = Column(Boolean, default=False)

    client = relationship("Clients", back_populates="projects")
    project_managers = relationship("ProjectManagers", back_populates="project")
    project_pmos = relationship("ProjectPMOs", back_populates="project")
    project_resources = relationship("ProjectResources", back_populates="project")
    tech_leads = relationship("ProjectTechLeads", back_populates="project")


class ProjectManagers(Base):
    __tablename__ = "project_managers"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    startdate = Column(Date, nullable=False)
    enddate = Column(Date)
    projectid = Column(Integer, ForeignKey("public.projects.id"), nullable=False)
    employeeid = Column(Integer, ForeignKey("public.employee.id"), nullable=False)
    status = Column(Boolean, default=True)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)

    project = relationship("Projects", back_populates="project_managers")
    employee = relationship("Employee", back_populates="managed_projects")


class ProjectPMOs(Base):
    __tablename__ = "project_pmos"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)
    projectid = Column(Integer, ForeignKey("public.projects.id"), nullable=False)
    status = Column(Boolean, default=True)
    employeeid = Column(Integer, ForeignKey("public.employee.id"))

    project = relationship("Projects", back_populates="project_pmos")
    employee = relationship("Employee", back_populates="pmo_projects")


class Roles(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    rolename = Column(Text, unique=True, nullable=False)
    displayrolename = Column(Text, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)
    active = Column(Boolean, nullable=False)
    projectrole = Column(Boolean, nullable=False)
    globalrole = Column(Boolean, nullable=False)
    priorityorder = Column(Integer, nullable=False)
    isactive = Column(Boolean)

    project_resources = relationship("ProjectResources", back_populates="role")


class ProjectResources(Base):
    __tablename__ = "project_resources"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    employeeid = Column(Integer, ForeignKey("public.employee.id"), nullable=False)
    roleid = Column(Integer, ForeignKey("public.roles.id"), nullable=False)
    projectid = Column(Integer, ForeignKey("public.projects.id"), nullable=False)
    startdate = Column(Date, nullable=False)
    enddate = Column(Date)
    projectallocation = Column(Integer, nullable=False)
    billableallocation = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)
    projectresourcestatusid = Column(Integer, default=1)
    practicenotes = Column(Text)

    employee = relationship("Employee", back_populates="project_resources")
    project = relationship("Projects", back_populates="project_resources")
    role = relationship("Roles", back_populates="project_resources")


class ProjectTechLeads(Base):
    __tablename__ = "project_tech_leads"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, index=True)
    startdate = Column(Date, nullable=False)
    enddate = Column(Date)
    projectid = Column(Integer, ForeignKey("public.projects.id"), nullable=False)
    employeeid = Column(Integer, ForeignKey("public.employee.id"), nullable=False)
    status = Column(Boolean, default=True)
    createdat = Column(TIMESTAMP)
    updatedat = Column(TIMESTAMP)

    project = relationship("Projects", back_populates="tech_leads")
    employee = relationship("Employee", back_populates="project_tech_leads")


class Practice(Base):
    __tablename__ = "Practice"
    __table_args__ = {"schema": "LND"}

    PracticeId = Column(Integer, primary_key=True, index=True)
    PracticeName = Column(Text)
    PracticeManagementEmail = Column(Text)
    PracticeGroupEmail = Column(Text)
    IsActive = Column(Boolean, nullable=False)


class PracticePracticeHeadsMapping(Base):
    __tablename__ = "PracticePracticeHeadsMapping"
    __table_args__ = {"schema": "LND"}

    PracticeHeadMappingId = Column(Integer, primary_key=True, index=True)
    PracticeHeadEmployeeId = Column(Integer, ForeignKey("public.employee.id"), nullable=False)
    PracticeId = Column(Integer, ForeignKey("LND.Practice.PracticeId"), nullable=False)
    IsActive = Column(Boolean, nullable=False)
    CreatedDate = Column(TIMESTAMP(timezone=True), nullable=False)
    ModifiedDate = Column(TIMESTAMP(timezone=True), nullable=False)


class EmployeePracticeMapping(Base):
    __tablename__ = "EmployeePractice"
    __table_args__ = {"schema": "LND"}

    EmployeePracticeId = Column(Integer, primary_key=True, index=True)
    EmployeeId = Column(Integer, ForeignKey("public.employee.id"), nullable=False, index=True)
    PracticeId = Column(Integer, ForeignKey("LND.Practice.PracticeId"), nullable=False, index=True)
    IsPrimary = Column(Boolean, nullable=False)
    CreatedById = Column(Integer, ForeignKey("public.employee.id"), nullable=False, index=True)
    ModifiedById = Column(Integer, ForeignKey("public.employee.id"), nullable=False, index=True)
    CreatedDate = Column(TIMESTAMP(timezone=True), nullable=False)
    ModifiedDate = Column(TIMESTAMP(timezone=True), nullable=False)
    IsActive = Column(Boolean, nullable=False, default=False)

    employee = relationship("Employee", foreign_keys=[EmployeeId])
    practice = relationship("Practice", foreign_keys=[PracticeId])
    created_by = relationship("Employee", foreign_keys=[CreatedById])
    modified_by = relationship("Employee", foreign_keys=[ModifiedById])

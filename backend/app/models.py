from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Branch(Base):
    __tablename__ = "branches"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="officer")
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    pincodes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    branch: Mapped[Branch | None] = relationship()

class Loan(Base):
    __tablename__ = "loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    borrower_name: Mapped[str] = mapped_column(String(160))
    pincode: Mapped[str] = mapped_column(String(10), index=True)
    branch_name: Mapped[str] = mapped_column(String(100), default="Indore")
    outstanding: Mapped[float] = mapped_column(Numeric(14, 2))
    dpd: Mapped[int] = mapped_column(Integer, default=0)
    promise_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_history: Mapped[str] = mapped_column(String(30), default="unknown")
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open")
    priority_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_override_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    officer: Mapped[User | None] = relationship(foreign_keys=[assigned_to])
    promises: Mapped[list["Promise"]] = relationship(back_populates="loan")
    outcomes: Mapped[list["Outcome"]] = relationship(back_populates="loan")

class Outcome(Base):
    __tablename__ = "outcomes"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    loan: Mapped[Loan] = relationship(back_populates="outcomes")

class Promise(Base):
    __tablename__ = "promises"
    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    promise_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="upcoming")
    reminder_status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    loan: Mapped[Loan] = relationship(back_populates="promises")

class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("loans.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LoanDpdSnapshot(Base):
    __tablename__ = "loan_dpd_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    dpd: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("loan_id", "snapshot_date", name="uq_loan_dpd_snapshot"),)

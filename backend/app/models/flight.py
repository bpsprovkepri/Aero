from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Numeric, Boolean, Text, Float,
    ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ScrapeRun(Base):
    """Data Meta — metadata per eksekusi scraping."""
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), unique=True, nullable=False)        # UUID
    run_type = Column(String(10), default="MANUAL")                 # SCHEDULED / MANUAL
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())        # timestamp pengambilan, ✅ timezone=True
    scrape_date = Column(Date, nullable=False)                      # tanggal pengamatan (dimensi)
    route = Column(String(10), nullable=False)                      # "BTH-CGK"
    status = Column(String(10), default="RUNNING")                  # RUNNING / COMPLETED / FAILED
    total_records = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    # Relationship
    fares = relationship("FlightFare", back_populates="run")

    __table_args__ = (
        Index("idx_scrape_runs_run_id", "run_id"),
        Index("idx_scrape_runs_scrape_date", "scrape_date"),
    )


class FlightFare(Base):
    """Data Primer — data penerbangan hasil scraping."""
    __tablename__ = "flight_fares"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK ke scrape_runs
    run_id = Column(String(50), ForeignKey("scrape_runs.run_id"), nullable=False)

    # --- Data Primer ---
    route = Column(String(10), nullable=False)                # "BTH-CGK"
    airline = Column(String(50), nullable=False)               # "GARUDA INDONESIA"
    source = Column(String(30), nullable=False)                # garuda_api / citilink_api / bookcabin_api
    travel_date = Column(Date, nullable=False)                 # tanggal terbang
    flight_number = Column(String(10), nullable=False)         # "GA157"
    depart_time = Column(String(5), nullable=False)            # "17:40"
    arrive_time = Column(String(5), nullable=False)            # "19:30"
    basic_fare = Column(Numeric(15, 2), nullable=False)        # harga
    currency = Column(String(3), default="IDR")

    # --- Per-record meta ---
    scrape_source_page = Column(String(100))                   # URL endpoint
    source_type = Column(String(15), nullable=False)           # airline / bookcabin
    raw_price_label = Column(String(50))                       # fare family label
    status_scrape = Column(String(10), default="SUCCESS")      # SUCCESS / FAILED
    error_reason = Column(Text)                                # null jika sukses
    is_lowest_fare = Column(Boolean, default=False)

    # Relationship
    run = relationship("ScrapeRun", back_populates="fares")

    __table_args__ = (
        Index("idx_flight_fares_route_date", "route", "travel_date"),
        Index("idx_flight_fares_run_id", "run_id"),
        Index("idx_flight_fares_airline", "airline"),
    )


class FareDailySummary(Base):
    """Data Turunan — agregasi harian dari flight_fares."""
    __tablename__ = "fare_daily_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route = Column(String(10), nullable=False)
    airline = Column(String(50), nullable=False)
    travel_date = Column(Date, nullable=False)
    scrape_date = Column(Date, nullable=False)

    daily_min_price = Column(Numeric(15, 2))
    daily_avg_price = Column(Numeric(15, 2))
    daily_max_price = Column(Numeric(15, 2))
    price_change_dod = Column(Numeric(15, 2))       # day over day change
    volatility = Column(Float)                       # std dev / variasi harga
    cheapest_airline_per_day = Column(String(50))     # maskapai termurah hari itu
    cheapest_route_per_day = Column(String(10))       # rute termurah hari itu

    __table_args__ = (
        Index("idx_fare_summary_route_date", "route", "travel_date"),
        Index("idx_fare_summary_scrape_date", "scrape_date"),
    )

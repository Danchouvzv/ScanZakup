"""
Pytest configuration and shared fixtures.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_async_session
from app.main import app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    def override_get_session():
        return test_session
    
    app.dependency_overrides[get_async_session] = override_get_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["SECRET_KEY"] = "test-secret-key"
    yield
    # Cleanup is automatic when test finishes


# Sample data fixtures
@pytest.fixture
def sample_trd_buy_data():
    """Sample procurement data for testing."""
    return {
        "id": 1,
        "trd_buy_number_anno": "TRD-2024-001",
        "ref_buy_status": 210,
        "ref_type_trade": 1,
        "name_ru": "Закуп компьютерного оборудования",
        "name_kz": "Компьютерлік жабдықтарды сатып алу",
        "total_sum": 5000000.00,
        "count_lot": 2,
        "ref_subject_type": 1,
        "customer_bin": "123456789012",
        "start_date": "2024-01-15T10:00:00",
        "end_date": "2024-01-25T18:00:00",
    }


@pytest.fixture
def sample_lot_data():
    """Sample lot data for testing."""
    return {
        "id": 1,
        "lot_number": 1,
        "ref_lot_status": 310,
        "subject_biin": "123456789012",
        "name_ru": "Компьютеры и периферия",
        "name_kz": "Компьютерлер мен перифериялық құрылғылар",
        "quantity": 50.0,
        "price": 2500000.00,
        "sum": 2500000.00,
        "customer_bin": "123456789012",
        "trd_buy_id": 1,
    }


@pytest.fixture
def sample_contract_data():
    """Sample contract data for testing."""
    return {
        "id": 1,
        "contract_number": "CON-2024-001",
        "ref_contract_status": 410,
        "supplier_biin": "987654321098",
        "customer_bin": "123456789012",
        "subject_biin": "123456789012",
        "contract_sum": 2400000.00,
        "sign_date": "2024-02-01T14:30:00",
        "ec_end_date": "2024-12-31T23:59:59",
        "lot_id": 1,
        "trd_buy_id": 1,
    }


@pytest.fixture
def sample_participant_data():
    """Sample participant data for testing."""
    return {
        "id": 1,
        "iin_bin": "123456789012",
        "name_ru": "ТОО Тест Компания",
        "name_kz": "Тест Компаниясы ЖШС",
        "ref_subject_type": 2,
        "is_single_org": False,
        "system_id": "SYS001",
        "email": "test@company.kz",
        "phone": "+7 701 234 5678",
        "address": "г. Алматы, ул. Тестовая, 123",
    } 
"""Unit tests for PetService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.pet import Pet, PetCreate, PetStatus, PetUpdate
from app.services.pet import PetService
from tests.factories.pet import PetCreateFactory


def make_service(
    repo: AsyncMock, commit: AsyncMock | None = None, rollback: AsyncMock | None = None
) -> PetService:
    return PetService(repo, commit=commit, rollback=rollback)


@pytest.mark.asyncio
async def test_get_pet_returns_pet() -> None:
    """get_pet returns the pet when found."""
    repo = AsyncMock()
    pet = Pet(id=1, name="Fido", photoUrls=[], status=PetStatus.available)
    repo.get.return_value = pet

    service = make_service(repo)
    result = await service.get_pet(1)

    assert result.id == 1
    assert result.name == "Fido"


@pytest.mark.asyncio
async def test_get_pet_raises_404_when_not_found() -> None:
    """get_pet raises HTTPException 404 when pet is not found."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.get.return_value = None

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.get_pet(99)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_add_pet_creates_pet() -> None:
    """add_pet delegates creation to the repository."""
    repo = AsyncMock()
    pet_data = PetCreateFactory()
    expected = Pet(id=1, name=pet_data.name, photoUrls=pet_data.photo_urls, status=pet_data.status)
    repo.create.return_value = expected

    service = make_service(repo)
    result = await service.add_pet(pet_data)

    repo.create.assert_called_once_with(pet_data)
    assert result.id == 1


@pytest.mark.asyncio
async def test_add_pet_raises_value_error_for_empty_name() -> None:
    """add_pet raises ValueError/ValidationError when name is empty."""
    from pydantic import ValidationError

    repo = AsyncMock()
    service = make_service(repo)

    with pytest.raises((ValueError, ValidationError)):
        await service.add_pet(PetCreate(name="", photoUrls=[]))


@pytest.mark.asyncio
async def test_update_pet_delegates_to_repo() -> None:
    """update_pet delegates to the repository and returns updated pet."""
    repo = AsyncMock()
    pet_update = PetUpdate(id=1, name="Rex", photoUrls=[], status=PetStatus.sold)
    expected = Pet(id=1, name="Rex", photoUrls=[], status=PetStatus.sold)
    repo.update.return_value = expected

    service = make_service(repo)
    result = await service.update_pet(pet_update)

    repo.update.assert_called_once_with(pet_update)
    assert result.name == "Rex"


@pytest.mark.asyncio
async def test_update_pet_raises_404_when_not_found() -> None:
    """update_pet raises HTTPException 404 when the pet does not exist."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.update.side_effect = KeyError("Pet 1 not found")

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.update_pet(PetUpdate(id=1, name="Rex", photoUrls=[]))

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_pet_calls_repo() -> None:
    """delete_pet calls repository delete."""
    repo = AsyncMock()
    repo.delete.return_value = None

    service = make_service(repo)
    await service.delete_pet(1)

    repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_pet_raises_404_when_not_found() -> None:
    """delete_pet raises HTTPException 404 when not found."""
    from fastapi import HTTPException

    repo = AsyncMock()
    repo.delete.side_effect = KeyError("Pet 1 not found")

    service = make_service(repo)
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_pet(1)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_find_by_status_delegates_to_repo() -> None:
    """find_by_status calls repository list_by_status."""
    repo = AsyncMock()
    pets = [Pet(id=1, name="Fido", photoUrls=[], status=PetStatus.available)]
    repo.list_by_status.return_value = pets

    service = make_service(repo)
    result = await service.find_by_status("available")

    repo.list_by_status.assert_called_once_with("available")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_find_by_tags_delegates_to_repo() -> None:
    """find_by_tags calls repository list_by_tags."""
    repo = AsyncMock()
    repo.list_by_tags.return_value = []

    service = make_service(repo)
    result = await service.find_by_tags(["cute"])

    repo.list_by_tags.assert_called_once_with(["cute"])
    assert result == []


@pytest.mark.asyncio
async def test_add_pet_commits_when_callback_is_configured() -> None:
    """add_pet calls commit callback after successful write."""
    repo = AsyncMock()
    pet_data = PetCreateFactory()
    expected = Pet(id=1, name=pet_data.name, photoUrls=pet_data.photo_urls, status=pet_data.status)
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()

    service = PetService(repo, commit=commit, rollback=rollback)
    await service.add_pet(pet_data)

    commit.assert_awaited_once()
    rollback.assert_not_called()


@pytest.mark.asyncio
async def test_update_pet_rolls_back_on_unexpected_error() -> None:
    """update_pet rolls back and re-raises for non-domain repository errors."""
    repo = AsyncMock()
    repo.update.side_effect = RuntimeError("db down")
    commit = AsyncMock()
    rollback = AsyncMock()

    service = PetService(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db down"):
        await service.update_pet(PetUpdate(id=1, name="Rex", photoUrls=[]))

    commit.assert_not_called()
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_pet_rolls_back_on_unexpected_error():
    repo = AsyncMock()
    repo.delete.side_effect = RuntimeError("db error")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = PetService(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db error"):
        await service.delete_pet(1)
    commit.assert_not_called()
    rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_pet_with_form_updates_name_and_status(monkeypatch):
    repo = AsyncMock()
    pet = Pet(
        id=1, name="Fido", photoUrls=["a.jpg"], status=PetStatus.available, category=None, tags=[]
    )
    repo.get.return_value = pet
    updated_pet = Pet(
        id=1, name="Rex", photoUrls=["a.jpg"], status=PetStatus.sold, category=None, tags=[]
    )
    repo.update.return_value = updated_pet
    service = make_service(repo)
    result = await service.update_pet_with_form(1, name="Rex", status="sold")
    assert result.name == "Rex"
    assert result.status == PetStatus.sold


@pytest.mark.asyncio
async def test_add_pet_successful_creation():
    repo = AsyncMock()
    pet_data = PetCreateFactory()
    expected = Pet(id=1, name=pet_data.name, photoUrls=pet_data.photo_urls, status=pet_data.status)
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = PetService(repo, commit=commit, rollback=rollback)
    result = await service.add_pet(pet_data)
    repo.create.assert_called_once_with(pet_data)
    commit.assert_awaited_once()
    rollback.assert_not_called()
    assert result == expected


@pytest.mark.asyncio
async def test_add_pet_raises_value_error_for_whitespace_name():
    repo = AsyncMock()
    service = PetService(repo)
    with pytest.raises(ValueError, match="Pet name cannot be empty"):
        await service.add_pet(PetCreate(name="   ", photoUrls=[]))


@pytest.mark.asyncio
async def test_add_pet_rolls_back_and_reraises_on_exception():
    repo = AsyncMock()
    pet_data = PetCreateFactory()
    repo.create.side_effect = RuntimeError("db error")
    commit = AsyncMock()
    rollback = AsyncMock()
    service = PetService(repo, commit=commit, rollback=rollback)
    with pytest.raises(RuntimeError, match="db error"):
        await service.add_pet(pet_data)
    rollback.assert_awaited_once()
    commit.assert_not_called()


@pytest.mark.asyncio
async def test_add_pet_does_not_call_rollback_on_success():
    repo = AsyncMock()
    pet_data = PetCreateFactory()
    expected = Pet(id=1, name=pet_data.name, photoUrls=pet_data.photo_urls, status=pet_data.status)
    repo.create.return_value = expected
    commit = AsyncMock()
    rollback = AsyncMock()
    service = PetService(repo, commit=commit, rollback=rollback)
    await service.add_pet(pet_data)
    rollback.assert_not_called()

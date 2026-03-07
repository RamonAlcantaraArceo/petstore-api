"""Pet endpoints — /api/v1/pet."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile

from app.dependencies import get_pet_service
from app.schemas.pet import Pet, PetCreate, PetUpdate
from app.services.pet import PetService

router = APIRouter(prefix="/pet", tags=["pet"])


@router.post("", response_model=Pet, status_code=200)
async def add_pet(
    pet: PetCreate,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> Pet:
    """Add a new pet to the store.

    Args:
        pet: Pet data from request body.
        service: Injected PetService.

    Returns:
        The created pet.
    """
    return await service.add_pet(pet)


@router.put("", response_model=Pet, status_code=200)
async def update_pet(
    pet: PetUpdate,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> Pet:
    """Update an existing pet.

    Args:
        pet: Updated pet data from request body.
        service: Injected PetService.

    Returns:
        The updated pet.
    """
    return await service.update_pet(pet)


@router.get("/findByStatus", response_model=list[Pet])
async def find_pets_by_status(
    status: Annotated[str, Query(description="Status values to filter by")] = "available",
    service: PetService = Depends(get_pet_service),
) -> list[Pet]:
    """Find pets by status.

    Args:
        status: Availability status to filter by.
        service: Injected PetService.

    Returns:
        List of pets matching the given status.
    """
    return await service.find_by_status(status)


@router.get("/findByTags", response_model=list[Pet])
async def find_pets_by_tags(
    tags: Annotated[list[str], Query(description="Tags to filter by")],
    service: PetService = Depends(get_pet_service),
) -> list[Pet]:
    """Find pets by tags.

    Args:
        tags: Tag names to filter by.
        service: Injected PetService.

    Returns:
        List of pets matching any of the given tags.
    """
    return await service.find_by_tags(tags)


@router.get("/{pet_id}", response_model=Pet)
async def get_pet_by_id(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> Pet:
    """Find pet by ID.

    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.

    Returns:
        The pet with the given ID.
    """
    return await service.get_pet(pet_id)


@router.post("/{pet_id}", response_model=Pet)
async def update_pet_with_form(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
    name: Annotated[str | None, Form()] = None,
    status: Annotated[str | None, Form()] = None,
) -> Pet:
    """Update a pet with form data.

    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.
        name: New name for the pet.
        status: New status for the pet.

    Returns:
        The updated pet.
    """
    return await service.update_pet_with_form(pet_id, name=name, status=status)


@router.delete("/{pet_id}", status_code=200)
async def delete_pet(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> dict[str, str]:
    """Delete a pet.

    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.

    Returns:
        Confirmation message.
    """
    await service.delete_pet(pet_id)
    return {"message": "Pet deleted"}


@router.post("/{pet_id}/uploadFile", status_code=200)
async def upload_file(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
    file: UploadFile | None = None,
    additional_metadata: Annotated[str | None, Form()] = None,
) -> dict[str, str]:
    """Upload an image for a pet.

    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.
        file: The image file to upload.
        additional_metadata: Optional metadata string.

    Returns:
        Confirmation message with file info.
    """
    # Verify pet exists
    await service.get_pet(pet_id)
    filename = file.filename if file else "none"
    return {"message": f"File uploaded: {filename}"}

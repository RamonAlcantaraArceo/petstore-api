"""Pet endpoints — /api/v1/pet."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from petstore_core.schemas.pet import Pet, PetCreate, PetStatus, PetUpdate
from petstore_core.services.pet import PetService

from app.api.v1.error_mapping import map_domain_errors
from app.dependencies import get_pet_service

unprotected_router = APIRouter(prefix="/pet", tags=["pet"])
protected_router = APIRouter(prefix="/pet", tags=["pet"])


@protected_router.post("", response_model=Pet, status_code=200, operation_id="add_pet")
async def add_pet(
    pet: PetCreate,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> Pet:
    """Add a new pet to the store.

    \f
    Args:
        pet: Pet data from request body.
        service: Injected PetService.

    Returns:
        The created pet.
    """
    return await map_domain_errors(service.add_pet(pet))


@protected_router.put("", response_model=Pet, status_code=200, operation_id="update_pet")
async def update_pet(
    pet: PetUpdate,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> Pet:
    """Update an existing pet.

    \f
    Args:
        pet: Updated pet data from request body.
        service: Injected PetService.

    Returns:
        The updated pet.
    """
    return await map_domain_errors(service.update_pet(pet))


@unprotected_router.get(
    "/findByStatus", response_model=list[Pet], operation_id="find_pets_by_status"
)
async def find_pets_by_status(
    status: Annotated[
        PetStatus | None,
        Query(description="Status value to filter by. Omit to return all pets."),
    ] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int | None,
        Query(ge=1, le=100, description="Maximum number of records to return (1–100)"),
    ] = None,
    service: PetService = Depends(get_pet_service),
) -> list[Pet]:
    """Find pets by status with optional pagination.

    \f
    Args:
        service: Injected PetService.
        status: Availability status to filter by. When omitted, all pets are
            returned.
        skip: Number of records to skip (offset).
        limit: Maximum number of records to return.

    Returns:
        List of pets matching the given status (or all pets when status is
        not provided).
    """
    return await map_domain_errors(service.find_by_status(status, skip=skip, limit=limit))


@protected_router.get("/findByTags", response_model=list[Pet], operation_id="find_pets_by_tags")
async def find_pets_by_tags(
    tags: Annotated[list[str] | None, Query(description="Tags to filter by")] = None,
    service: PetService = Depends(get_pet_service),
) -> list[Pet]:
    """Find pets by tags.

    \f
    Args:
        tags: Tag names to filter by.
        service: Injected PetService.

    Returns:
        List of pets matching any of the given tags.
    """
    if tags is None:
        tags = []
    return await map_domain_errors(service.find_by_tags(tags))


@unprotected_router.get("/{pet_id}", response_model=Pet, operation_id="get_pet_by_id")
async def get_pet_by_id(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> Pet:
    """Find pet by ID.

    \f
    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.

    Returns:
        The pet with the given ID.
    """
    return await map_domain_errors(service.get_pet(pet_id))


@protected_router.post("/{pet_id}", response_model=Pet, operation_id="update_pet_with_form")
async def update_pet_with_form(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
    name: Annotated[str | None, Form()] = None,
    status: Annotated[str | None, Form()] = None,
) -> Pet:
    """Update a pet with form data.

    \f
    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.
        name: New name for the pet.
        status: New status for the pet.

    Returns:
        The updated pet.
    """
    return await map_domain_errors(service.update_pet_with_form(pet_id, name=name, status=status))


@protected_router.delete("/{pet_id}", status_code=204, operation_id="delete_pet")
async def delete_pet(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
) -> None:
    """Delete a pet.

    \f
    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.
    """
    await map_domain_errors(service.delete_pet(pet_id))


@protected_router.post("/{pet_id}/uploadFile", status_code=200, operation_id="upload_file")
async def upload_file(
    pet_id: int,
    service: Annotated[PetService, Depends(get_pet_service)],
    file: UploadFile | None = None,
    additional_metadata: Annotated[str | None, Form()] = None,
) -> dict[str, str]:
    """Upload an image for a pet.

    \f
    Args:
        pet_id: The pet's unique identifier.
        service: Injected PetService.
        file: The image file to upload.
        additional_metadata: Optional metadata string.

    Returns:
        Confirmation message with file info.
    """
    # Verify pet exists
    await map_domain_errors(service.get_pet(pet_id))
    filename = file.filename if file else "none"
    return {"message": f"File uploaded: {filename}"}

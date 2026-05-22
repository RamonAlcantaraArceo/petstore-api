"""Unit tests for fixture dataset definitions."""

from __future__ import annotations

import allure
import pytest

from app.fixtures.datasets import DATASETS, FixtureDataset, get_dataset
from app.schemas.order import OrderStatus
from app.schemas.pet import PetStatus

pytestmark = [allure.epic("Fixtures"), allure.feature("Datasets")]


# ---------------------------------------------------------------------------
# get_dataset
# ---------------------------------------------------------------------------


@allure.story("Dataset Registry")
@allure.severity(allure.severity_level.NORMAL)
def test_get_dataset_returns_known_dataset() -> None:
    """get_dataset returns the correct FixtureDataset for a known name."""
    ds = get_dataset("basic")
    assert isinstance(ds, FixtureDataset)
    assert ds.name == "basic"


@allure.story("Dataset Registry")
@allure.severity(allure.severity_level.NORMAL)
def test_get_dataset_raises_for_unknown_name() -> None:
    """get_dataset raises ValueError for an unregistered dataset name."""
    with pytest.raises(ValueError, match="Unknown fixture dataset"):
        get_dataset("nonexistent_dataset")


@allure.story("Dataset Registry")
@allure.severity(allure.severity_level.NORMAL)
def test_get_dataset_error_message_lists_available_datasets() -> None:
    """ValueError message includes names of available datasets."""
    with pytest.raises(ValueError) as exc_info:
        get_dataset("bad_name")
    msg = str(exc_info.value)
    for name in DATASETS:
        assert name in msg


@allure.story("Dataset Registry")
@allure.severity(allure.severity_level.NORMAL)
def test_all_registered_datasets_are_retrievable() -> None:
    """Every entry in DATASETS can be retrieved by name via get_dataset."""
    for name in DATASETS:
        ds = get_dataset(name)
        assert ds.name == name


# ---------------------------------------------------------------------------
# empty dataset
# ---------------------------------------------------------------------------


@allure.story("Empty Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_empty_dataset_has_no_entities() -> None:
    """The 'empty' dataset contains no pets, orders, or users."""
    ds = get_dataset("empty")
    assert ds.pets == []
    assert ds.orders == []
    assert ds.users == []


# ---------------------------------------------------------------------------
# basic dataset
# ---------------------------------------------------------------------------


@allure.story("Basic Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_basic_dataset_has_pets_and_users_but_no_orders() -> None:
    """The 'basic' dataset has pets and users but no orders."""
    ds = get_dataset("basic")
    assert len(ds.pets) > 0
    assert len(ds.users) > 0
    assert ds.orders == []


@allure.story("Basic Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_basic_dataset_all_pets_are_available() -> None:
    """All pets in the 'basic' dataset have 'available' status."""
    ds = get_dataset("basic")
    for pet in ds.pets:
        assert pet.status == PetStatus.available


# ---------------------------------------------------------------------------
# mixed_v1 dataset
# ---------------------------------------------------------------------------


@allure.story("Mixed V1 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v1_contains_all_pet_statuses() -> None:
    """mixed_v1 includes pets with available, pending, and sold statuses."""
    ds = get_dataset("mixed_v1")
    statuses = {pet.status for pet in ds.pets}
    assert PetStatus.available in statuses
    assert PetStatus.pending in statuses
    assert PetStatus.sold in statuses


@allure.story("Mixed V1 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v1_has_orders_and_users() -> None:
    """mixed_v1 has at least one order and one user."""
    ds = get_dataset("mixed_v1")
    assert len(ds.orders) > 0
    assert len(ds.users) > 0


@allure.story("Mixed V1 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v1_order_pet_indices_are_valid() -> None:
    """All order pet_index values in mixed_v1 reference valid pet positions."""
    ds = get_dataset("mixed_v1")
    for order in ds.orders:
        assert 0 <= order.pet_index < len(ds.pets)


@allure.story("Mixed V1 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v1_orders_have_valid_statuses() -> None:
    """All orders in mixed_v1 have a valid OrderStatus."""
    ds = get_dataset("mixed_v1")
    for order in ds.orders:
        assert order.status in list(OrderStatus)


# ---------------------------------------------------------------------------
# mixed_v2 dataset
# ---------------------------------------------------------------------------


@allure.story("Mixed V2 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v2_contains_all_pet_statuses() -> None:
    """mixed_v2 includes pets with available, pending, and sold statuses."""
    ds = get_dataset("mixed_v2")
    statuses = {pet.status for pet in ds.pets}
    assert PetStatus.available in statuses
    assert PetStatus.pending in statuses
    assert PetStatus.sold in statuses


@allure.story("Mixed V2 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v2_has_more_pets_than_mixed_v1() -> None:
    """mixed_v2 contains more pets than mixed_v1, providing richer data."""
    v1 = get_dataset("mixed_v1")
    v2 = get_dataset("mixed_v2")
    assert len(v2.pets) > len(v1.pets)


@allure.story("Mixed V2 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v2_order_pet_indices_are_valid() -> None:
    """All order pet_index values in mixed_v2 reference valid pet positions."""
    ds = get_dataset("mixed_v2")
    for order in ds.orders:
        assert 0 <= order.pet_index < len(ds.pets)


@allure.story("Mixed V2 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v2_has_multiple_users() -> None:
    """mixed_v2 contains at least four users."""
    ds = get_dataset("mixed_v2")
    assert len(ds.users) >= 4


@allure.story("Mixed V2 Dataset")
@allure.severity(allure.severity_level.NORMAL)
def test_mixed_v2_pets_have_categories() -> None:
    """All pets in mixed_v2 have a category assigned."""
    ds = get_dataset("mixed_v2")
    for pet in ds.pets:
        assert pet.category is not None


# ---------------------------------------------------------------------------
# Cross-dataset invariants
# ---------------------------------------------------------------------------


@allure.story("Dataset Invariants")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("name", ["basic", "mixed_v1", "mixed_v2"])
def test_datasets_have_unique_pet_names(name: str) -> None:
    """Pet names within any single dataset are unique."""
    ds = get_dataset(name)
    names = [p.name for p in ds.pets]
    assert len(names) == len(set(names))


@allure.story("Dataset Invariants")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("name", ["mixed_v1", "mixed_v2"])
def test_datasets_with_orders_reference_sold_or_delivered_pets(name: str) -> None:
    """Orders with delivered status are attached to 'sold' pets."""
    ds = get_dataset(name)
    for order in ds.orders:
        if order.status == OrderStatus.delivered:
            pet = ds.pets[order.pet_index]
            assert pet.status == PetStatus.sold

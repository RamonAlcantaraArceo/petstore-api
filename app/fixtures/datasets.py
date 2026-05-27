"""Named fixture datasets for seeding the Petstore API.

Each dataset is a self-contained snapshot of pets, orders, and users that
can be loaded into any storage backend (in-memory or PostgreSQL) to give
the service a deterministic starting state.

Available datasets
------------------
empty     — No data; clean slate (default when SEED_DATASET is not set).
basic     — A handful of available pets and two users; no orders.
mixed_v1  — Dogs, cats, and fish across all pet statuses; orders; users
            with contact details.
mixed_v2  — Exotic animals with categories and tags across all statuses;
            orders; additional users.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from petstore_core.schemas.order import OrderStatus
from petstore_core.schemas.pet import Category, PetStatus, Tag


@dataclass
class PetFixture:
    """Specification for a single pet to be seeded.

    Attributes:
        name: Pet name.
        photo_urls: List of photo URLs.
        status: Availability status.
        category: Optional pet category.
        tags: Optional list of tags.
    """

    name: str
    photo_urls: list[str] = field(default_factory=list)
    status: PetStatus = PetStatus.available
    category: Category | None = None
    tags: list[Tag] | None = None


@dataclass
class OrderFixture:
    """Specification for a single order to be seeded.

    The ``pet_index`` refers to the position of the target pet in the
    enclosing :class:`FixtureDataset`'s ``pets`` list and is resolved to
    the assigned pet ID after that pet is created.

    Attributes:
        pet_index: Index into the dataset's pets list.
        quantity: Number of units ordered.
        status: Order fulfillment status.
        ship_date: Expected shipping date (UTC-aware).
        complete: Whether the order is complete.
    """

    pet_index: int
    quantity: int = 1
    status: OrderStatus = OrderStatus.placed
    ship_date: datetime | None = None
    complete: bool = False


@dataclass
class UserFixture:
    """Specification for a single user to be seeded.

    Attributes:
        username: Unique username.
        email: Email address.
        first_name: Given name.
        last_name: Family name.
        phone: Contact phone number.
        user_status: Numeric status code.
        password: Plain-text password stored by the repository.
    """

    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    user_status: int | None = None
    password: str = "secret"


@dataclass
class FixtureDataset:
    """A named, self-contained set of entities to seed the service with.

    Attributes:
        name: Unique dataset identifier (used as the SEED_DATASET value).
        description: Human-readable summary of the dataset contents.
        pets: Ordered list of pets to create.
        orders: Orders whose ``pet_index`` values reference ``pets``.
        users: Users to create.
    """

    name: str
    description: str
    pets: list[PetFixture] = field(default_factory=list)
    orders: list[OrderFixture] = field(default_factory=list)
    users: list[UserFixture] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dataset definitions
# ---------------------------------------------------------------------------

_EMPTY = FixtureDataset(
    name="empty",
    description="No seed data — the service starts with a clean slate.",
)

_BASIC = FixtureDataset(
    name="basic",
    description=(
        "Minimal golden dataset: a few available pets and two users. "
        "Suitable for smoke-testing basic CRUD flows."
    ),
    pets=[
        PetFixture(name="Buddy", status=PetStatus.available),
        PetFixture(name="Max", status=PetStatus.available),
        PetFixture(name="Bella", status=PetStatus.available),
    ],
    users=[
        UserFixture(
            username="johndoe",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
        ),
        UserFixture(
            username="janedoe",
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        ),
    ],
)

_MIXED_V1 = FixtureDataset(
    name="mixed_v1",
    description=(
        "Mixed dataset v1: dogs, cats, and fish across all pet statuses "
        "(available / pending / sold), two orders, and two users with "
        "contact details."
    ),
    pets=[
        # index 0 — available dog
        PetFixture(
            name="Buddy",
            status=PetStatus.available,
            category=Category(id=1, name="Dogs"),
            tags=[Tag(id=1, name="friendly"), Tag(id=2, name="trained")],
        ),
        # index 1 — available cat
        PetFixture(
            name="Whiskers",
            status=PetStatus.available,
            category=Category(id=2, name="Cats"),
            tags=[Tag(id=3, name="indoor")],
        ),
        # index 2 — pending dog
        PetFixture(
            name="Charlie",
            status=PetStatus.pending,
            category=Category(id=1, name="Dogs"),
            tags=[Tag(id=1, name="friendly")],
        ),
        # index 3 — sold fish
        PetFixture(
            name="Goldie",
            status=PetStatus.sold,
            category=Category(id=3, name="Fish"),
        ),
        # index 4 — sold dog
        PetFixture(
            name="Shadow",
            status=PetStatus.sold,
            category=Category(id=1, name="Dogs"),
            tags=[Tag(id=4, name="guard")],
        ),
    ],
    orders=[
        # Order for Goldie (index 3) — delivered and complete
        OrderFixture(
            pet_index=3,
            quantity=1,
            status=OrderStatus.delivered,
            ship_date=datetime(2024, 1, 10, 12, 0, tzinfo=UTC),
            complete=True,
        ),
        # Order for Shadow (index 4) — approved, in transit
        OrderFixture(
            pet_index=4,
            quantity=1,
            status=OrderStatus.approved,
            ship_date=datetime(2024, 2, 15, 9, 0, tzinfo=UTC),
            complete=False,
        ),
    ],
    users=[
        UserFixture(
            username="johndoe",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1-555-100-0001",
            user_status=1,
        ),
        UserFixture(
            username="janedoe",
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
            phone="+1-555-100-0002",
            user_status=1,
        ),
    ],
)

_MIXED_V2 = FixtureDataset(
    name="mixed_v2",
    description=(
        "Mixed dataset v2: exotic animals with richer categories and tags "
        "across all pet statuses, three orders, and four users including an "
        "admin and a guest account."
    ),
    pets=[
        # index 0 — available parrot
        PetFixture(
            name="Rio",
            status=PetStatus.available,
            category=Category(id=4, name="Birds"),
            tags=[Tag(id=5, name="talking"), Tag(id=6, name="colorful")],
        ),
        # index 1 — available rabbit
        PetFixture(
            name="Snowball",
            status=PetStatus.available,
            category=Category(id=5, name="Rabbits"),
            tags=[Tag(id=7, name="fluffy")],
        ),
        # index 2 — available turtle
        PetFixture(
            name="Shelly",
            status=PetStatus.available,
            category=Category(id=6, name="Reptiles"),
        ),
        # index 3 — pending hamster
        PetFixture(
            name="Peanut",
            status=PetStatus.pending,
            category=Category(id=7, name="Small Animals"),
            tags=[Tag(id=8, name="nocturnal")],
        ),
        # index 4 — pending parrot
        PetFixture(
            name="Kiwi",
            status=PetStatus.pending,
            category=Category(id=4, name="Birds"),
            tags=[Tag(id=5, name="talking")],
        ),
        # index 5 — sold dog
        PetFixture(
            name="Duke",
            status=PetStatus.sold,
            category=Category(id=1, name="Dogs"),
            tags=[Tag(id=9, name="purebred"), Tag(id=1, name="friendly")],
        ),
        # index 6 — sold cat
        PetFixture(
            name="Luna",
            status=PetStatus.sold,
            category=Category(id=2, name="Cats"),
            tags=[Tag(id=10, name="hypoallergenic")],
        ),
    ],
    orders=[
        # Placed order for Rio (index 0)
        OrderFixture(
            pet_index=0,
            quantity=1,
            status=OrderStatus.placed,
            ship_date=datetime(2024, 3, 1, 8, 0, tzinfo=UTC),
            complete=False,
        ),
        # Delivered order for Duke (index 5)
        OrderFixture(
            pet_index=5,
            quantity=1,
            status=OrderStatus.delivered,
            ship_date=datetime(2024, 1, 20, 14, 0, tzinfo=UTC),
            complete=True,
        ),
        # Delivered order for Luna (index 6)
        OrderFixture(
            pet_index=6,
            quantity=2,
            status=OrderStatus.delivered,
            ship_date=datetime(2024, 2, 5, 11, 0, tzinfo=UTC),
            complete=True,
        ),
    ],
    users=[
        UserFixture(
            username="admin",
            email="admin@petstore.example",
            first_name="Admin",
            last_name="User",
            phone="+1-555-000-0001",
            user_status=2,
        ),
        UserFixture(
            username="alice",
            email="alice@example.com",
            first_name="Alice",
            last_name="Smith",
            phone="+1-555-200-0001",
            user_status=1,
        ),
        UserFixture(
            username="bob",
            email="bob@example.com",
            first_name="Bob",
            last_name="Jones",
            phone="+1-555-200-0002",
            user_status=1,
        ),
        UserFixture(
            username="guest",
            email="guest@petstore.example",
            first_name="Guest",
            last_name="Account",
            user_status=0,
        ),
    ],
)

# Public registry of all available datasets keyed by name.
DATASETS: dict[str, FixtureDataset] = {d.name: d for d in [_EMPTY, _BASIC, _MIXED_V1, _MIXED_V2]}


def get_dataset(name: str) -> FixtureDataset:
    """Return a fixture dataset by name.

    Args:
        name: The dataset name (e.g. ``"basic"``, ``"mixed_v1"``).

    Returns:
        The matching :class:`FixtureDataset`.

    Raises:
        ValueError: When no dataset with the given name is registered.

    Example:
        >>> dataset = get_dataset("basic")
        >>> assert dataset.name == "basic"
    """
    try:
        return DATASETS[name]
    except KeyError:
        available = ", ".join(sorted(DATASETS))
        raise ValueError(
            f"Unknown fixture dataset {name!r}. Available datasets: {available}"
        ) from None

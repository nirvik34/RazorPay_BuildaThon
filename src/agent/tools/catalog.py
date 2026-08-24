from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CatalogItem:
    product: str
    merchant: str
    category: str
    price: int
    keywords: list[str] = field(default_factory=list)


CATALOG: list[CatalogItem] = [
    CatalogItem(
        "Sony WH-1000XM5",
        "amazon",
        "electronics",
        14499,
        [
            "headphones",
            "wireless headphones",
            "noise cancelling",
            "anc",
            "audio",
            "music",
            "sony",
        ],
    ),
    CatalogItem(
        "Boat Rockerz 550",
        "flipkart",
        "electronics",
        1899,
        ["headphones", "budget headphones", "bluetooth", "boat", "cheap"],
    ),
    CatalogItem(
        "Apple Studio Display",
        "amazon",
        "electronics",
        159000,
        ["monitor", "display", "screen", "4k", "apple", "imac"],
    ),
    CatalogItem(
        "LG UltraGear 27 Monitor",
        "croma",
        "electronics",
        18500,
        ["monitor", "display", "gaming monitor", "144hz", "lg", "screen"],
    ),
    CatalogItem(
        "MacBook Pro 14",
        "techmart",
        "electronics",
        42000,
        ["laptop", "macbook", "apple laptop", "computer", "mac"],
    ),
    CatalogItem(
        "Ergonomic Office Chair",
        "amazon",
        "office_supplies",
        8900,
        ["chair", "office chair", "ergonomic", "desk chair", "furniture"],
    ),
    CatalogItem(
        "Logitech MX Master 3S",
        "croma",
        "electronics",
        9800,
        ["mouse", "logitech", "wireless mouse", "productivity"],
    ),
    CatalogItem(
        "Keychron K3 Keyboard",
        "croma",
        "electronics",
        9700,
        ["keyboard", "mechanical keyboard", "keychron", "typing"],
    ),
    CatalogItem(
        "Anker USB-C Hub",
        "croma",
        "electronics",
        9900,
        ["usb hub", "dock", "adapter", "usb-c", "anker", "dongle"],
    ),
    CatalogItem(
        "Aashirvaad Atta 5kg",
        "bigbasket",
        "groceries",
        249,
        ["atta", "flour", "groceries", "staples", "wheat"],
    ),
    CatalogItem(
        "Monthly groceries basket",
        "bigbasket",
        "groceries",
        6400,
        ["groceries", "monthly groceries", "basket", "vegetables", "household"],
    ),
    CatalogItem(
        "Amazon Pay Gift Card ₹10,000",
        "flipkart",
        "gift_cards",
        10000,
        ["gift card", "giftcard", "voucher", "gift"],
    ),
    CatalogItem(
        "Casino Chips Pack",
        "royalgames",
        "gambling",
        25000,
        ["casino", "gambling", "betting", "chips", "poker"],
    ),
]


def search_catalog(query: str) -> list[CatalogItem]:
    q = query.lower().strip()
    if not q:
        return []
    words = q.split()
    scored: list[tuple[int, CatalogItem]] = []
    for item in CATALOG:
        haystack = " ".join(
            [item.product, item.merchant, item.category, *item.keywords]
        ).lower()
        score = sum(1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored]


def compare_products(items: list[CatalogItem]) -> list[CatalogItem]:
    return sorted(items, key=lambda i: i.price)


def select_product(items: list[CatalogItem], index: int = 0) -> CatalogItem:
    if not items:
        raise ValueError("No products matched the query")
    return items[min(index, len(items) - 1)]

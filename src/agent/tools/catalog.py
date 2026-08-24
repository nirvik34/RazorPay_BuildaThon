from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CatalogItem:
    product: str
    merchant: str
    category: str
    price: int


CATALOG: list[CatalogItem] = [
    CatalogItem("Sony WH-1000XM5", "amazon", "electronics", 14499),
    CatalogItem("Boat Rockerz 550", "flipkart", "electronics", 1899),
    CatalogItem("Apple Monitor Studio Display", "amazon", "electronics", 159000),
    CatalogItem('LG UltraGear Monitor 27"', "croma", "electronics", 18500),
    CatalogItem("MacBook Pro 14", "techmart", "electronics", 42000),
    CatalogItem("Ergonomic Office Chair", "amazon", "office_supplies", 8900),
    CatalogItem("Logitech MX Master 3S", "croma", "electronics", 9800),
    CatalogItem("Keychron K3 Keyboard", "croma", "electronics", 9700),
    CatalogItem("Anker USB-C Hub", "croma", "electronics", 9900),
    CatalogItem("Aashirvaad Atta 5kg", "bigbasket", "groceries", 249),
    CatalogItem("Monthly groceries basket", "bigbasket", "groceries", 6400),
    CatalogItem("Amazon Pay Gift Card ₹10,000", "flipkart", "gift_cards", 10000),
    CatalogItem("Casino Chips Pack", "royalgames", "gambling", 25000),
]


def search_catalog(query: str) -> list[CatalogItem]:
    q = query.lower()
    return [item for item in CATALOG if q in item.product.lower() or q in item.category]


def compare_products(items: list[CatalogItem]) -> list[CatalogItem]:
    return sorted(items, key=lambda i: i.price)


def select_product(items: list[CatalogItem], index: int = 0) -> CatalogItem:
    if not items:
        raise ValueError("No products matched the query")
    return items[min(index, len(items) - 1)]

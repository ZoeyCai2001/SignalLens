from app.schemas.watchlist import StockWatchlistItem


def initial_stock_watchlist() -> list[StockWatchlistItem]:
    return [
        StockWatchlistItem(
            ticker="MU",
            company_name="Micron Technology",
            exchange="NASDAQ",
            sector="Technology",
            industry="Semiconductors",
            priority="High",
            group_name="Memory / Storage",
            is_pinned=True,
            related_keywords=[
                "HBM",
                "DRAM",
                "NAND",
                "data center",
                "AI server",
                "memory pricing",
            ],
            related_companies=["NVDA", "AMD", "AVGO", "TSM"],
            related_ai_themes=[
                "HBM memory",
                "AI server memory",
                "data center capex",
            ],
            notes="Monitor AI infrastructure memory demand and pricing cycle signals.",
        ),
        StockWatchlistItem(
            ticker="MRVL",
            company_name="Marvell Technology",
            exchange="NASDAQ",
            sector="Technology",
            industry="Semiconductors",
            priority="High",
            group_name="AI Chips",
            is_pinned=True,
            related_keywords=[
                "custom silicon",
                "ASIC",
                "AI data center",
                "optical interconnect",
                "cloud AI",
            ],
            related_companies=["NVDA", "AMD", "AVGO", "TSM"],
            related_ai_themes=[
                "custom silicon",
                "AI data center networking",
                "optical interconnect",
            ],
            notes="Monitor AI custom silicon and data center connectivity growth.",
        ),
        StockWatchlistItem(
            ticker="SNDK",
            company_name="SanDisk",
            exchange="NASDAQ",
            sector="Technology",
            industry="Computer Hardware",
            priority="Medium",
            group_name="Memory / Storage",
            is_pinned=False,
            related_keywords=[
                "NAND",
                "SSD",
                "storage",
                "enterprise storage",
                "data center",
            ],
            related_companies=["MU", "WDC", "STX"],
            related_ai_themes=[
                "NAND storage",
                "enterprise SSD",
                "AI data storage",
            ],
            notes="Monitor AI storage demand and NAND cycle signals.",
        ),
    ]

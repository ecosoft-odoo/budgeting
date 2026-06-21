This module is a bridge between budget_control_stock and sale_stock.

When a Sale Order is confirmed, the system auto-creates a Delivery Order (DO).
At this point, the Budget Control may not yet be confirmed (the user needs to
set KPIs first). This module bypasses the stock budget commit check during SO
confirmation so the DO can be created without a budget error.

After SO confirmation, all subsequent DO operations (validate, unreserve, etc.)
enforce the budget check normally, requiring the user to confirm the Budget
Control before the DO can be processed.

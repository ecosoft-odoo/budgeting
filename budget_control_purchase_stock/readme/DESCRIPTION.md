This module is a bridge between budget_control_purchase and budget_control_stock.

When an outgoing delivery order (with lot tracing) is confirmed, the system traces
each lot back to its source purchase order line and creates a reversed
purchase.budget.move to uncommit the corresponding PO budget commitment.

When the vendor bill is posted, the uncommit quantity is automatically capped to
the remaining PO commitment (undelivered lots only), preventing double-uncommit.

When the delivery order is cancelled, the lot-traced PO uncommit entries are
removed and the PO commitment is restored.

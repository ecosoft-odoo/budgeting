This module bridges purchase and stock budget control with a product-category
inventory recognition policy and a company fallback:

- **Vendor Bill**: posting the bill releases the PO commitment and records budget
  actual. Outgoing stock operations do not affect budget.
- **Stock Issue Valuation**: posting the bill affects neither actual nor the PO
  commitment. Confirming an outgoing operation replaces the traceable PO
  commitment with a stock commitment; posting its valuation entry replaces that
  stock commitment with budget actual.

Each product category can use **Company Default**, **Vendor Bill**, or **Stock
Issue Valuation**. The resolved policy is captured independently on each
purchase order line and stock move, so mixed-policy purchase orders are
supported and later configuration changes do not rewrite confirmed
transactions. Returns preserve the original stock move policy.

Services and other non-storable products always use Vendor Bill. Stock Issue
requires automated inventory valuation. It also applies to outgoing quantities
that did not originate from a purchase (for example, manufactured stock) when
their product category uses Stock Issue; a Vendor Bill category intentionally
excludes all of its outgoing stock operations from budget.

Lot-tracked products release the exact source PO commitment. Non-lot products use
company- and budget-period-scoped product FIFO across received PO lines, ordered
by PO date. Quantity is converted between stock and purchase UoMs, and remaining
commitment caps use company-currency values. Cancelling an outgoing operation
restores its PO commitment, while a stock return reverses the issue actual
without recreating the fulfilled PO commitment.

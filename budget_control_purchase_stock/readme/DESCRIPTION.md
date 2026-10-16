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

Lot-tracked products trace their source PO lines through completed receipts.
When a lot was received on several PO lines, each outgoing move line prefers
the source with the same analytic accounts, then the oldest receipt. If no
source has matching analytics, receipt FIFO still releases the original PO
commitment when stock is issued to another project. Different outgoing moves
can therefore release different PO lines even when they share one lot.

Non-lot products use company- and budget-period-scoped product FIFO across
received PO lines, ordered by PO date. Quantity is converted between stock
and purchase UoMs, and remaining commitment caps use company-currency values.
Cancelling an outgoing operation restores its PO commitment. A stock return
reverses the issue actual and, for lot-tracked products, restores the source PO
commitment for the returned lots: they are unissued stock again. The restore is
a new entry dated on the return, so a return in a later period does not reopen
the period of the original issue. Returns of multi-step deliveries (e.g. OUT
after PICK) follow the delivery chain to the operation that committed budget.
Returning a return issues the lots again and releases the commitment again.
Non-lot product returns do not restore PO commitment yet. Returned stock that
is later scrapped or sent back to the vendor keeps its PO commitment until it
is closed manually.

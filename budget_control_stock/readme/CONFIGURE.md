To configure this module, you need to:

#. Go to *Inventory > Configuration > Operation Types*.
#. Open the operation type that issues goods from inventory (for example
   *Delivery Orders*) and enable `Commit Budget`. Confirming a transfer of this
   operation type will then create budget commitments.
#. Choose the `Budget Price Source` used to value the commitment:

   * *Move Unit Price* (default): uses ``price_unit`` from the stock move first.
     Falls back to ``product.standard_price`` when ``price_unit`` is empty.
   * *Lot Standard Price*: uses ``lot.standard_price`` per reserved lot
     (weighted average if multiple lots), for FIFO / lot-based costing.
     Falls back to Move Unit Price when no lots are reserved.

#. Go to *Budgeting > Configuration > Budget Periods*, open the relevant period
   and tick `On Stock` to control the budget against stock commitments. When
   `Control Budget` is enabled the flag follows it by default.

Notes:

* Stock moves must carry an analytic distribution (provided by the
  *stock_analytic* dependency); commitments are created per analytic account.
* Recording the related stock journal entry as budget *actual* relies on the
  standard journal-entry budget flow, so make sure the stock journal entries
  carry the analytic distribution of the moves.

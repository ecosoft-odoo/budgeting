This module will create budget commitment for contract (to be used as alternate actual source in mis_builder)

For the contract to commit budget, the field "Commit Budget" must be set.

* On Buget Commitment tab, click "Recompute" button, contract.budget.commit is created to commit budget
* When supplier invoice is posted, reversed contract.budget.commit is created to uncommit budget.

A new tab "Budget Commitment" is created on contract for budget user to keep track of the committed budget.

Note:

* Budget will commit only once, regardless of number of recurring invoices.
* As such, we normally enable commit budget when dealing with non-recurring invoices.

# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import ast
import re
from collections import defaultdict

from odoo.models import expression
from odoo.tools.float_utils import float_is_zero
from odoo.tools.safe_eval import safe_eval

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.aep import AccountingExpressionProcessor

_DOMAIN_START_RE = re.compile(r"\(|(['\"])[!&|]\1")


def _is_domain(s):
    """ Test if a string looks like an Odoo domain """
    return _DOMAIN_START_RE.match(s)


class AccountingExpressionProcessorActivity(AccountingExpressionProcessor):
    def _parse_match_object(self, mo):
        """Split a match object corresponding to an accounting variable

        Returns field, mode, account domain, move line domain.
        """
        domain_eval_context = {
            "ref": self.env.ref,
            "user": self.env.user,
        }
        field, mode, account_sel, ml_domain = mo.groups()
        # handle some legacy modes
        if not mode:
            mode = self.MODE_VARIATION
        elif mode == "s":
            mode = self.MODE_END
        # convert account selector to account domain
        if account_sel.startswith("_"):
            # legacy bal_NNN%
            acc_domain = self._account_codes_to_domain(account_sel[1:])
        else:
            assert account_sel[0] == "[" and account_sel[-1] == "]"
            inner_account_sel = account_sel[1:-1].strip()
            if not inner_account_sel:
                # empty selector: select all accounts
                acc_domain = tuple()
            elif _is_domain(inner_account_sel):
                # account selector is a domain
                acc_domain = tuple(safe_eval(account_sel, domain_eval_context))
            else:
                # account selector is a list of account codes
                acc_domain = self._account_codes_to_domain(inner_account_sel)
        ag_domain = ml_domain.replace("activity_id", "id")
        ag_domain = ast.literal_eval(ag_domain)
        acc_domain = (ag_domain[0],) + acc_domain
        # move line domain
        if ml_domain:
            assert ml_domain[0] == "[" and ml_domain[-1] == "]"
            ml_domain = tuple(safe_eval(ml_domain, domain_eval_context))
        else:
            ml_domain = tuple()
        return field, mode, acc_domain, ml_domain

    def _convert_activity_id(self, key):
        """ Convert activity_id to id on model budget.activity and return value list """
        activity_domain = key[0][0]
        activity = [x for x in activity_domain]
        activity[0] = "id"
        return activity

    def done_parsing(self):
        """ Replace account domains by account ids in map """
        for key, acc_domains in self._map_account_ids.items():
            all_account_ids = set()
            activity = self._convert_activity_id(key)
            for acc_domain in acc_domains:
                acc_domain_with_company = expression.AND(
                    [
                        acc_domain,
                        [("company_id", "in", self.companies.ids)],
                        [tuple(activity)],
                    ]
                )
                account_ids = self._account_model.search(
                    acc_domain_with_company
                ).ids
                self._account_ids_by_acc_domain[acc_domain].update(account_ids)
                all_account_ids.update(account_ids)
            self._map_account_ids[key] = list(all_account_ids)

    def do_queries(
        self,
        date_from,
        date_to,
        target_move="posted",
        additional_move_line_filter=None,
        aml_model=None,
        is_activity=False,
    ):
        """Query sums of debit and credit for all accounts and domains
        used in expressions.

        This method must be executed after done_parsing().
        """
        if not aml_model:
            aml_model = self.env["account.move.line"]
        else:
            aml_model = self.env[aml_model]
        aml_model = aml_model.with_context(active_test=False)
        company_rates = self._get_company_rates(date_to)
        # {(domain, mode): {account_id: (debit, credit)}}
        self._data = defaultdict(dict)
        domain_by_mode = {}
        ends = []
        for key in self._map_account_ids:
            domain, mode = key
            if mode == self.MODE_END and self.smart_end:
                # postpone computation of ending balance
                ends.append((domain, mode))
                continue
            if mode not in domain_by_mode:
                domain_by_mode[mode] = self.get_aml_domain_for_dates(
                    date_from, date_to, mode, target_move
                )
            domain = list(domain) + domain_by_mode[mode]
            if additional_move_line_filter:
                domain.extend(additional_move_line_filter)
            # fetch sum of debit/credit, grouped by account_id
            accs = aml_model.read_group(
                domain,
                ["activity_id", "debit", "credit", "account_id", "company_id"],
                ["activity_id", "company_id"],
                lazy=False,
            )
            for acc in accs:
                rate, dp = company_rates[acc["company_id"][0]]
                debit = acc["debit"] or 0.0
                credit = acc["credit"] or 0.0
                if (
                    mode
                    in (
                        self.MODE_INITIAL,
                        self.MODE_UNALLOCATED,
                    )
                    and float_is_zero(debit - credit, precision_digits=self.dp)
                ):
                    # in initial mode, ignore accounts with 0 balance
                    continue
                self._data[key][acc["activity_id"][0]] = (
                    debit * rate,
                    credit * rate,
                )
        # compute ending balances by summing initial and variation
        for key in ends:
            domain, mode = key
            initial_data = self._data[(domain, self.MODE_INITIAL)]
            variation_data = self._data[(domain, self.MODE_VARIATION)]
            account_ids = set(initial_data.keys()) | set(variation_data.keys())
            for account_id in account_ids:
                di, ci = initial_data.get(
                    account_id, (AccountingNone, AccountingNone)
                )
                dv, cv = variation_data.get(
                    account_id, (AccountingNone, AccountingNone)
                )
                self._data[key][account_id] = (di + dv, ci + cv)

    def get_aml_domain_for_expr(
        self, expr, date_from, date_to, target_move, account_id=None
    ):
        """Get a domain on account.move.line for an expression.

        Prerequisite: done_parsing() must have been invoked.

        Returns a domain that can be used to search on account.move.line.
        """
        aml_domains = []
        date_domain_by_mode = {}
        for mo in self._ACC_RE.finditer(expr):
            field, mode, acc_domain, ml_domain = self._parse_match_object(mo)
            aml_domain = list(ml_domain)
            activity_ids = set()
            activity_ids.update(self._account_ids_by_acc_domain[acc_domain])
            if not account_id:
                aml_domain.append(("activity_id", "in", tuple(activity_ids)))
            else:
                # filter on account_id
                if account_id in activity_ids:
                    aml_domain.append(("activity_id", "=", account_id))
                else:
                    continue
            if field == "crd":
                aml_domain.append(("credit", "<>", 0.0))
            elif field == "deb":
                aml_domain.append(("debit", "<>", 0.0))
            aml_domains.append(expression.normalize_domain(aml_domain))
            if mode not in date_domain_by_mode:
                date_domain_by_mode[mode] = self.get_aml_domain_for_dates(
                    date_from, date_to, mode, target_move
                )
        assert aml_domains
        # TODO we could do this for more precision:
        #      AND(OR(aml_domains[mode]), date_domain[mode]) for each mode
        return expression.OR(aml_domains) + expression.OR(
            date_domain_by_mode.values()
        )

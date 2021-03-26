# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def filtered_can_commit(func):
    """ Filter self on any function for records with can_commit = True """

    def filter_can_commit(self, *args, **kwargs):
        self = self.filtered("can_commit")
        return func(self, *args, **kwargs)

    return filter_can_commit

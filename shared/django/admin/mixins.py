from adminsortable2.admin import SortableAdminMixin


class CustomSortableAdminMixin(SortableAdminMixin):
    """
    Improved version of SortableAdminMixin that takes into account that a model may have
    multiple fields in ordering, and the 'order' field to sort on may not be the first one.
    """
    exclude = ['order']

    def __init__(self, model, admin_site):
        # Override initialization to use 'order' instead of first field in ordering
        self.default_order_field = 'order'
        self.default_order_direction = ''  # Empty string means direct order (no minus)

        super(SortableAdminMixin, self).__init__(model, admin_site)
        self.enable_sorting = False
        self.order_by = None
        self._add_reorder_method()

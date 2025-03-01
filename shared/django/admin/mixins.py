from adminsortable2.admin import SortableAdminMixin


class CustomSortableAdminMixin(SortableAdminMixin):
    exclude = ['order']

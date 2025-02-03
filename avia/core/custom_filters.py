from django.contrib import admin
from django.db.models import Count, IntegerField, F, ExpressionWrapper

from core.models import TGUser


class CustomUserSimFilter(admin.SimpleListFilter):
    title = "Есть сим-карта?"
    parameter_name = "sim-card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Да"],
            ["no", "Нет"],
        ]

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == "yes":
                queryset = queryset.filter(sim_cards__isnull=False)
            elif self.value() == "no":
                queryset = queryset.filter(sim_cards__isnull=True)

        return queryset

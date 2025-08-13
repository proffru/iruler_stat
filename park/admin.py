from django.contrib import admin
from park.models import (
    Park,
    Car,
    DriverWorkRule,
    Account,
    Driver,
    Order,
    Transaction,
    DateProcessing
)

admin.site.site_title = 'Iruler'
admin.site.site_header = 'Iruler'


@admin.register(Park)
class ParkAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'city', 'park_id', 'is_active')
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'city', 'park_id')
    list_editable = ('is_active',)
    ordering = ('city', 'name')


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('brand', 'model', 'year', 'number', 'park', 'status')
    list_filter = ('brand', 'status', 'park', 'year')
    search_fields = ('brand', 'model', 'number', 'vin')
    raw_id_fields = ('park',)
    ordering = ('brand', 'model')


@admin.register(DriverWorkRule)
class DriverWorkRuleAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'park', 'is_enabled')
    list_filter = ('is_enabled', 'park')
    search_fields = ('name', 'work_rule_id')
    raw_id_fields = ('park',)
    ordering = ('name',)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('account_id', 'balance', 'currency', 'account_type')
    search_fields = ('account_id',)
    ordering = ('account_id',)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'middle_name', 'park', 'work_status')
    list_filter = ('work_status', 'park')
    search_fields = ('last_name', 'first_name', 'middle_name', 'driver_id', 'phone')
    raw_id_fields = ('park', 'work_rule', 'account')
    ordering = ('last_name', 'first_name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('order_id', 'driver', 'status', 'created_at', 'price')
    list_filter = ('status', 'park', 'payment_method')
    search_fields = ('order_id', 'driver__last_name', 'driver__first_name')
    raw_id_fields = ('park', 'driver', 'car')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('transaction_id', 'driver', 'event_at', 'amount', 'category_name')
    list_filter = ('category_name', 'park')
    search_fields = ('transaction_id', 'driver__last_name', 'driver__first_name')
    raw_id_fields = ('park', 'driver')
    date_hierarchy = 'event_at'
    ordering = ('-event_at',)


@admin.register(DateProcessing)
class DateProcessingAdmin(admin.ModelAdmin):
    list_display = ('last_processed_date', 'created_at', 'updated_at')
    list_filter = ('last_processed_date',)
    search_fields = ('last_processed_date',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'last_processed_date'
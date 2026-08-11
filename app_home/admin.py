from django.contrib import admin

# Register your models here.
# app_home/admin.py
from .models import Product, TabathaPrompt, TabathaDailyMessage

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active', 'is_featured', 'created_at')
    list_filter = ('is_active', 'is_featured')
    search_fields = ('name', 'description')
    list_editable = ('is_active', 'is_featured') # Edit these directly in the list view
    

# Use the decorator OR the register function, NOT BOTH.
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ('name', 'price', 'is_featured', 'is_active')

@admin.register(TabathaPrompt)
class TabathaPromptAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('text',)
    list_editable = ('is_active',)

@admin.register(TabathaDailyMessage)
class TabathaDailyMessageAdmin(admin.ModelAdmin):
    list_display = ('date', 'created_at')
    search_fields = ('message', 'date')
from django.contrib import admin

# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, OTP

class UserAdmin(BaseUserAdmin):
    # Use 'email' as the first item so it becomes the link to the detail page
    list_display = ('email', 'get_full_name', 'is_staff', 'is_active')
    list_display_links = ('email',) # Explicitly set the link field
    ordering = ('email',)

    # Remove 'username' from fieldsets to prevent crash
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Groups', {'fields': ('groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password'),
        }),
    )

    def get_full_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile.full_name:
            return obj.profile.full_name
        return "No Name Set"
    get_full_name.short_description = 'Full Name'

admin.site.register(CustomUser, UserAdmin)
admin.site.register(OTP)



# class UserAdmin(admin.ModelAdmin):
#     list_display = ['id', 'email', 'is_staff', 'is_active', 'date_joined']

# admin.site.register(CustomUser, UserAdmin)
# admin.site.register(OTP)


# class UserAdmin(BaseUserAdmin):
#     # 1. Update List View: Use 'get_full_name' instead of 'full_name'
#     list_display = ('email', 'get_full_name', 'is_staff', 'is_active', 'date_joined')
    
#     # 2. Fix ordering (CustomUser uses email as ID)
#     ordering = ('email',)

#     # 3. FIX THE CRASH: Manually define fieldsets to REMOVE 'username'
#     fieldsets = (
#         (None, {'fields': ('email', 'password')}),
#         ('Personal info', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
#         ('Groups', {'fields': ('groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login', 'date_joined')}),
#     )

#     # 4. Fix the "Add User" form in Admin
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'password'),
#         }),
#     )

#     # 5. Method to fetch full_name from the UserProfile model
#     def get_full_name(self, obj):
#         # Reach into the related UserProfile model
#         if hasattr(obj, 'profile') and obj.profile.full_name:
#             return obj.profile.full_name
#         return "No Name Set"
    
#     get_full_name.short_description = 'Full Name'

# # Register the models
# admin.site.register(CustomUser, UserAdmin)




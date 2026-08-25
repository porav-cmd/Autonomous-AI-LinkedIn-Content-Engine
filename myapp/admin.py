from django.contrib import admin
from .models import Post, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'github_username', 'telegram_chat_id', 'cheat_sheet_theme', 'created_at')
    search_fields = ('user__username', 'github_username', 'telegram_chat_id')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'topic', 'post_type', 'image_type', 'date_posted')
    list_filter = ('post_type', 'image_type', 'date_posted')
    search_fields = ('topic', 'final_text')

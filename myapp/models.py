from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    github_username = models.CharField(max_length=255, default='porav-cmd')
    telegram_bot_token = models.CharField(max_length=255, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=255, blank=True, null=True)
    groq_api_key = models.CharField(max_length=255, blank=True, null=True)
    cheat_sheet_theme = models.CharField(max_length=50, default='cream_grid')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Post(models.Model):
    CHOICE_TYPE = (
        ('Project','Project'),
        ('News','News')
    )
    IMAGE_TYPE = (
        ('NONE', 'NONE'),
        ('FREE', 'FREE'),
        ('SCREENSHOT','SCREENSHOT'),
        ('AI_GENERATED','AI_GENERATED')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    topic = models.CharField(max_length=255)
    date_posted = models.DateField(auto_now_add=True)
    post_type = models.CharField(choices=CHOICE_TYPE, max_length=50)
    final_text = models.TextField()
    text_hash = models.CharField(max_length=64, db_index=True)
    image_type = models.CharField(choices=IMAGE_TYPE, max_length=20, default='NONE')
    image_path = models.URLField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return self.topic
    
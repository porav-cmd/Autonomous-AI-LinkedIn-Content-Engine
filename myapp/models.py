from django.db import models

# Create your models here.

class Post(models.Model):
    CHOICE_TYPE = (
        ('Project','Project'),
        ('News','News')
    )
    IMAGE_TYPE = (
        ('SCREENSHOT','SCREENSHOT'),
        ('AI_GENERATED','AI_GENERATED')
    )

    topic = models.CharField(max_length=255)
    date_posted = models.DateField(auto_now_add=True)
    post_type = models.CharField(choices = CHOICE_TYPE, max_length=50)
    final_text = models.TextField()
    text_hash = models.CharField(max_length=64, db_index=True)
    image_type = models.CharField(choices=IMAGE_TYPE, max_length=20, default='NONE')
    image_path = models.URLField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return self.topic
    
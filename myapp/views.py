from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Post, UserProfile
import subprocess
import sys

def get_or_create_default_user():
    user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return user, profile

def dashboard_view(request):
    user, profile = get_or_create_default_user()
    
    posts = Post.objects.all().order_by('-id')
    total_posts = posts.count()
    project_posts = posts.filter(post_type='Project').count()
    news_posts = posts.filter(post_type='News').count()

    context = {
        'profile': profile,
        'posts': posts[:15],
        'total_posts': total_posts,
        'project_posts': project_posts,
        'news_posts': news_posts,
    }
    return render(request, 'dashboard.html', context)

def save_settings_view(request):
    if request.method == 'POST':
        user, profile = get_or_create_default_user()
        profile.github_username = request.POST.get('github_username', 'porav-cmd').strip()
        profile.telegram_bot_token = request.POST.get('telegram_bot_token', '').strip()
        profile.telegram_chat_id = request.POST.get('telegram_chat_id', '').strip()
        profile.groq_api_key = request.POST.get('groq_api_key', '').strip()
        profile.cheat_sheet_theme = request.POST.get('cheat_sheet_theme', 'cream_grid').strip()
        profile.save()
        messages.success(request, 'Settings saved successfully!')
    return redirect('dashboard')

def trigger_generate_view(request):
    try:
        # Run agent in background thread or process
        result = subprocess.run(
            [sys.executable, "-m", "myapp.service.agent"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return JsonResponse({'status': 'success', 'message': 'Post generated and sent to Telegram successfully!'})
        else:
            return JsonResponse({'status': 'error', 'message': f'Generation output: {result.stderr[:300]}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
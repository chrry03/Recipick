from django.shortcuts import render

# Create your views here.

def log_create(request):
    """일지 작성 페이지 뷰"""
    return render(request, 'logs/log_create.html')

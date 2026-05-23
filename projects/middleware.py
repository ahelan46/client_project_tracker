# middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class FreezeUserMiddleware:
    """
    Middleware to check if a user is frozen and redirect them to a frozen page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Skip check for admin users
            if hasattr(request.user, 'profile'):
                # List of URLs that frozen users can access
                allowed_urls = [
                    'user_frozen_page',
                    'logout',
                    'login',
                ]
                
                # Check if user is frozen
                if request.user.profile.is_frozen:
                    # Allow access to logout and frozen page only
                    current_path = request.path
                    
                    # Check if current path is allowed
                    is_allowed = False
                    for url_name in allowed_urls:
                        try:
                            allowed_path = reverse(url_name)
                            if current_path == allowed_path or current_path.startswith('/logout'):
                                is_allowed = True
                                break
                        except:
                            pass
                    
                    # Also allow AJAX requests for frozen status check
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        is_allowed = True
                    
                    if not is_allowed:
                        messages.warning(request, 'Your account has been frozen. Please contact admin.')
                        return redirect('user_frozen_page')
        
        response = self.get_response(request)
        return response
from django.conf import settings

class DynamicLoginRedirectMiddleware:
    """
    Dynamically sets LOGIN_url depending on request path.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        #default login url from settings
        request.login_url = settings.LOGIN_REDIRECT_URL


        # if request is for /admin/, switch to admin login
        if request.path.startswith('/admin/'):
            request.login_url = '/admin/'

        return self.get_response(request)
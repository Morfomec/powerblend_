from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def get_pagination(request, queryset, per_page=10):
    """
    Resubale pagination function
    :param request: Django request object
    :param queryset: The queryset to paginate
    :param per_page: Number of items per page (default=10)
    :return: paginated queryset (page_obj)
    """

    paginator = Paginator(queryset, per_page)
    page = request.GET.get("page",1)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return page_obj
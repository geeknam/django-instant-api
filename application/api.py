from .models import Product
from .serializers import ProductSerializer
from rest_framework import filters, viewsets


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('code', 'name')
    paginate_by = 50

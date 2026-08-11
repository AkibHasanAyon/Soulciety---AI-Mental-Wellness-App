from django.urls import path
from .views import (
    DailyQuoteView, MoodCheckInView, DailyMoveView,
    PopularContentView, FeaturedProductsView, HomeDataView
)

urlpatterns = [
    path('quote/', DailyQuoteView.as_view(), name='daily-quote'),
    path('mood/', MoodCheckInView.as_view(), name='mood-checkin'),
    path('daily-move/', DailyMoveView.as_view(), name='daily-move'),
    path('popular/', PopularContentView.as_view(), name='popular-content'),
    path('shop/featured/', FeaturedProductsView.as_view(), name='featured-products'),
    
    # Recommended: one endpoint for the whole home screen
    path('home-data/', HomeDataView.as_view(), name='home-data'),
]
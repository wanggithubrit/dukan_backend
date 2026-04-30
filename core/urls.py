from django.urls import path, include
from .views import (
   
    create_item,
    delete_item,
    delete_shop_media,
    get_items,
    delete_banner,
    get_nearby_shops,
    get_shop_detail,
    submit_feedback,
    get_user,
    login,
    my_shop,
    signup,
    toggle_favorite, 
    get_favorites,
    update_shop,
    update_shop_status,
    upgrade_plan,
    upload_banner,
    get_notifications,
    upload_shop_media,
    get_featured_banners,
    update_avatar,
    shop_page,
    send_otp, 
    verify_otp, 
    reset_password,
    reward_user,
    create_payment_order,
    mark_notification_read,
    delete_notification,
    delete_all_notifications,
    delete_shop_cover,
    merchant_banners
)

from django.conf import settings
from django.conf.urls.static import static
from .views import merchant_dashboard
print("CORE URLS LOADED ✅")
urlpatterns = [
    path('reset-password/', reset_password),
    path('shops/', get_nearby_shops),


    path('shops/<int:shop_id>/', get_shop_detail),
  

    # 🔥 FAVORITE ROUTES
     # ❤️ FAVORITES (FIXED)
    path('favorite/toggle/', toggle_favorite),
    path('favorites/<int:user_id>/', get_favorites),
    path('my-shop/<int:user_id>/', my_shop),
    path('shop/status/', update_shop_status),
    path('auth/signup/', signup),
    path('auth/login/', login),

    path('user/<int:id>/', get_user),

    # urls.py
    # core/urls.py

    path('analytics/like/', toggle_favorite),
    path('merchant/dashboard/<int:user_id>/', merchant_dashboard),
    path('banner/upload/', upload_banner),
    path('notifications/<int:user_id>/', get_notifications),
    path('items/create/', create_item),
    path('shop/media/upload/', upload_shop_media),
    path('shop/media/delete/<int:media_id>/', delete_shop_media),
    path('shop/update/', update_shop),
    path('items/<int:shop_id>/', get_items),
    path('item/delete/<int:item_id>/', delete_item),
    path('shop/upgrade/', upgrade_plan),
    path('banner/delete/<int:banner_id>/', delete_banner),
    path('banners/featured/', get_featured_banners),
    path('feedback/', submit_feedback),
    path('avatar/update/', update_avatar),
    path('shop/<int:id>/', shop_page),
    path('send-otp/', send_otp),
    path('verify-otp/', verify_otp),
    path('reward/', reward_user),
    path('payment/create-order/', create_payment_order),
    path('notification/read/<int:notification_id>/', mark_notification_read),
    path('notification/delete/<int:notification_id>/', delete_notification),
    path('notifications/delete-all/<int:user_id>/', delete_all_notifications),
    path('shop/delete-cover/', delete_shop_cover),
    path('merchant/banners/', merchant_banners),
    path('banner/delete/<int:banner_id>/', delete_banner),
    path('shop/delete-cover/', delete_shop_cover),
    ]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
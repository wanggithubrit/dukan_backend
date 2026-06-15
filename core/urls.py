from django.urls import path, include
from django.views.generic import TemplateView
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
    update_profile,
    login,
    my_shop,
    signup,
    validate_referral,
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
    merchant_banners,
    update_item,
    create_quantity_order,
    verify_quantity_payment,
    submit_store_report,
    get_leaderboard,
    ondc_search,
    credit_status,
    buy_limit_slot,
    ad_complete,
    report_action,
    admin_metrics,
    delete_account,
    verify_payment,
    debug_error,
)

from django.conf import settings
from django.conf.urls.static import static
from .views import merchant_dashboard, check_app_update, notify_item_customers, create_support_order, verify_support_payment, submit_order, get_merchant_orders, update_order_status, update_delivery_settings, get_customer_orders
from rest_framework_simplejwt.views import TokenRefreshView
print("CORE URLS LOADED ✅")




urlpatterns = [
    path('reset-password/', reset_password),
    path('shops/', get_nearby_shops),

    path('shop/<int:id>/', shop_page),
    path('shops/<int:shop_id>/', get_shop_detail),
  

    # 🔥 FAVORITE ROUTES
     # ❤️ FAVORITES (FIXED)
    path('favorite/toggle/', toggle_favorite),
    path('favorites/', get_favorites),
    path('my-shop/<int:user_id>/', my_shop),
    path('shop/status/', update_shop_status),
    path('auth/signup/', signup),
    path('auth/validate-referral/', validate_referral),
    path('auth/login/', login),

    path('user/<int:id>/', get_user),
    path('profile/update/', update_profile),

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
    path('item/update/<int:item_id>/', update_item),
    path('shop/upgrade/', upgrade_plan),
    path('banner/delete/<int:banner_id>/', delete_banner),
    path('banners/featured/', get_featured_banners),
    path('feedback/', submit_feedback),
    path('avatar/update/', update_avatar),
    path('shop/<int:id>/', shop_page),
    path('send-otp/', send_otp),
    path('verify-otp/', verify_otp),
    path('reward/', reward_user),
    path('create-order/', create_payment_order),
    path('verify-payment/', verify_payment),
    path('payment/create/', create_payment_order),
    path('payment/verify/', verify_payment),
    path('payment/create-order/', create_payment_order),
    path('notification/read/<int:notification_id>/', mark_notification_read),
    path('notification/delete/<int:notification_id>/', delete_notification),
    path('notifications/delete-all/<int:user_id>/', delete_all_notifications),
    path('shop/delete-cover/', delete_shop_cover),
    path('merchant/banners/', merchant_banners),
    path('banner/delete/<int:banner_id>/', delete_banner),
    path('shop/delete-cover/', delete_shop_cover),
    path(
    'payment/quantity/create/',
    create_quantity_order
),

path(
    'payment/quantity/verify/',
    verify_quantity_payment
),
    path('reports/submit/', submit_store_report),
    path('reports/leaderboard/', get_leaderboard),
    path('ondc/search/', ondc_search),
    path('credits/status/', credit_status),
    path('credits/buy-limit/', buy_limit_slot),
    path('credits/ad-complete/', ad_complete),
    path('credits/report-action/', report_action),
    path('admin/metrics/', admin_metrics),
    path('app-update/check/', check_app_update),
    path('item/<int:item_id>/notify/', notify_item_customers),
    path('support/create-order/', create_support_order),
    path('support/verify-payment/', verify_support_payment),
    path('auth/delete/', delete_account),
    path('orders/', submit_order),
    path('customer/orders/', get_customer_orders),
    path('merchant/orders/', get_merchant_orders),
    path('merchant/orders/<int:order_id>/', update_order_status),
    path('merchant/delivery/settings/', update_delivery_settings),
    path('debug/error/', debug_error),
    ]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.contrib import admin
from django.urls import path
from .views import Login, Home, SignUp, UploadPhoto, MyProfile, PhotoView, CollectionView, CollectionDetail, Filter,\
    FilterViewDetail, Logout, GetNotifications

app_name = 'shared_photo_library'

urlpatterns = [
    path('', Home.as_view(), name="home"),
    path('login', Login.as_view(), name="login"),
    path('logout', Logout.as_view(), name="logout"),
    path('sign-up', SignUp.as_view(), name="signup"),
    path('upload-photo', UploadPhoto.as_view(), name="upload_photo"),
    path('my-profile', MyProfile.as_view(), name="my_profile"),
    path('photo', PhotoView.as_view(), name="update_photo"),
    path('photos', PhotoView.as_view(), name="photos"),
    path('collections', CollectionView.as_view(), name="collections"),
    path('collection/<int:id>', CollectionDetail.as_view(), name="collection_detail"),
    path('views', Filter.as_view(), name="views"),
    path('view/<int:id>', FilterViewDetail.as_view(), name="view_detail"),
    path('notifications', GetNotifications.as_view(), name="notifications"),

]

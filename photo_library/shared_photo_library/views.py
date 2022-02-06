import json
from json import JSONDecodeError

from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.views import View
from django.http import Http404, HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from .forms import *


class Login(View):
    def get(self, request):
        form = AuthenticationForm()
        # signup_form = UserCreationForm()
        return render(request, 'shared_photo_library/homepage.html', {'form': form})

    def post(self, request):
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            print("user  logged in")
            return redirect('shared_photo_library:home')
        return render(request, 'shared_photo_library/homepage.html', {'form': form, 'user_authenticated': False})


class Logout(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        return redirect('shared_photo_library:home')


class SignUp(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'shared_photo_library/signup.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('shared_photo_library:login')
        return render(request, 'shared_photo_library/signup.html', {'form': form})


class Home(View):
    def get(self, request):
        user = request.user
        user_authenticated = user.is_authenticated
        form = AuthenticationForm()
        cols = []
        photos = []
        views = []
        if user_authenticated:
            cols = list(Collection.objects.filter(Q(owner=user) | Q(shared_users=user)).order_by('-created_date')[:4])
            photos = list(Photo.objects.filter(added_by=user).order_by('-added_time')[:4])
            views = list(FilterView.objects.filter(Q(owner=user) | Q(shared_users=user)).order_by('-created_date')[:4])

        return render(request, 'shared_photo_library/homepage.html', {'form': form,
                                                                      'user_authenticated': user_authenticated,
                                                                      'user': user, 'photos': photos,
                                                                      'collections': cols, 'views': views})


class UploadPhoto(LoginRequiredMixin, View):
    def post(self, request):
        new_photo = Photo.objects.create(added_by=request.user)
        form = AddPhoto(request.POST, request.FILES, instance=new_photo)
        if form.is_valid():
            form.save()
            new_photo.load_meta_data()
            return redirect('shared_photo_library:photos')

    def get(self, request):
        form = AddPhoto()
        return render(request, "shared_photo_library/upload_photo.html", {'form': form})


class MyProfile(View):
    def get(self, request):
        logged_in_user = request.user
        return render(request, 'shared_photo_library/my_profile.html',
                      {'user': logged_in_user})


class PhotoView(LoginRequiredMixin, View):
    def get(self, request):
        logged_in_user = request.user
        photos = list(Photo.objects.filter(added_by=logged_in_user).order_by('-added_time'))
        photos = photo_tags_as_list(photos)
        shared_collections = list(Collection.objects.filter(shared_users=logged_in_user).values('id', 'collection_name'))
        users_collections = list(Collection.objects.filter(owner=logged_in_user).values('id', 'collection_name'))
        # return render(request, 'shared_photo_library/photos.html',
        #               {'user': logged_in_user, 'photos': photos, 'shared_collections': shared_collections,
        #                'users_collections': users_collections})
        form = AddPhoto()
        return render(request, 'shared_photo_library/all_photos.html',
                      {'user': logged_in_user, 'photos': photos, 'shared_collections': shared_collections,
                       'users_collections': users_collections, 'form': form})

    def post(self, request, **kwargs):
        user = request.user
        data = request.POST.dict()
        ph_id = data['id']
        photo = Photo.objects.get(id=ph_id)
        # print(data)
        if data.get('delete'):
            if user != photo.added_by:
                return HttpResponse("It's not your photo you cannot delete it.", status=403)
            photo.delete()
            return redirect('shared_photo_library:photos')

        if data.get('collections'):
            collections_ids = data['collections'].split(",")[1:]
            collections_ids = set(collections_ids)
            collections = {col.id: col for col in Collection.objects.all()}
            for col_id in collections_ids:
                col = collections[int(col_id)]
                if col.owner != user and (user not in col.shared_users.all()):
                    return HttpResponse(f"You don't have permission to add photo to collection = {col.collection_name}",
                                        status=403)
                col.add_photo_to_collection(photo)
                views_attached_to_col = FilterView.objects.filter(collection=col)
                for view in views_attached_to_col:
                    view.filter_by_view()
            return redirect('shared_photo_library:photos')

        photo.add_location(data['location'])
        if "-" in data['date']:
            photo.add_date(data['date'])
        photo.add_tags(data['tags-list'])

        # all views updated: if tag x is added to a photo all views includes tag x must be updated
        # and all views can be contain tag x
        all_views = FilterView.objects.all()
        for view in all_views:
            view.filter_by_view()
        if data.get('col_id'):
            col_id = int(data['col_id'])
            return redirect('shared_photo_library:collection_detail', id=col_id)
        return redirect('shared_photo_library:photos')


class CollectionView(LoginRequiredMixin, View):
    def get(self, request):
        form = CreateCollection()
        logged_in_user = request.user
        users_collections = list(Collection.objects.filter(owner=logged_in_user).annotate(photo_number=Count('photos')))
        shared_collections = list(Collection.objects.filter(shared_users=logged_in_user).annotate(photo_number=Count('photos')))
        collections = users_collections + shared_collections
        # return render(request, 'shared_photo_library/collections.html',
        #               {'user': logged_in_user, 'form': form, 'collections': collections,
        #                'users_collections': users_collections, 'shared_collections': shared_collections})
        return render(request, 'shared_photo_library/all_collections.html',
                      {'user': logged_in_user, 'form': form, 'collections': collections,
                       'users_collections': users_collections, 'shared_collections': shared_collections})

    def post(self, request):
        data = json.load(request)
        new_col = Collection.objects.create(owner=request.user, collection_name=data['col_name'])
        response = {'col': list(Collection.objects.filter(id=new_col.id).annotate(photo_number=Count('photos')).
                                values('id', 'collection_name', 'created_date', 'owner__username', 'photo_number'))[0]}
        return JsonResponse(response)


class CollectionDetail(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        col_id = int(kwargs['id'])
        col = Collection.objects.get(id=col_id)
        photos = col.photos.all().order_by('-added_time')
        photos = photo_tags_as_list(photos)
        view_form = CreateView()

        filter_tags = col.get_filter_tags()

        # if user wants to add a photo to the collection, he/she can select from  only his/her uploaded photos
        # to add to collection
        users_all_photos = list(Photo.objects.filter(added_by=request.user).order_by('-added_time'))
        users_not_added_photos = list(Photo.objects.filter(added_by=request.user).exclude(col_photos=col).order_by('-added_time'))

        # users that collection can be shared with
        not_shared_users = [user.username for user in User.objects.all().exclude(shared_collections=col)]

        # users that collection already shared with
        shared_users = {user.username: user for user in User.objects.filter(shared_collections=col)}

        # return render(request, 'shared_photo_library/collection_detail.html',
        #               {'user': request.user, 'col': col, 'photos': photos, 'users_all_photos': users_all_photos,
        #                'not_shared_users': not_shared_users, 'shared_users': shared_users, 'view_form': view_form,
        #                'filter_tags': list(filter_tags)})
        return render(request, 'shared_photo_library/col_detail.html',
                      {'user': request.user, 'col': col, 'photos': photos, 'users_all_photos': users_all_photos,
                       'not_shared_users': not_shared_users, 'shared_users': shared_users, 'view_form': view_form,
                       'filter_tags': list(filter_tags), 'users_not_added_photos': users_not_added_photos})

    def post(self, request, **kwargs):
        col_id = int(kwargs['id'])
        col = Collection.objects.get(id=col_id)
        try:
            data = json.load(request)
        except JSONDecodeError:
            data = request.POST.dict()

        user = request.user
        if col.owner != user and (user not in col.shared_users.all()):
            return HttpResponse(f"You don't have permission to make any changes in collection = {col.collection_name}",
                                status=403)
        if data.get('remove'):  # ajax request made to remove a photo from collection
            photo_id = int(data.get('ph_id'))
            col.remove_photo_from_collection(Photo.objects.get(id=photo_id))

            views_attached_to_col = FilterView.objects.filter(collection=col)
            for view in views_attached_to_col:
                view.filter_by_view()
            return JsonResponse({})
        elif data.get('add'):  # ajax request made to add a photo to collection
            photo_id = int(data.get('ph_id'))
            photo = Photo.objects.get(id=photo_id)
            col.add_photo_to_collection(photo)

            views_attached_to_col = FilterView.objects.filter(collection=col)
            for view in views_attached_to_col:
                view.filter_by_view()
            return JsonResponse({'url': photo.photo.url, 'id': photo.id, 'location': photo.location,
                                 'date': str(photo.date), 'tags': photo.tags})
        elif data.get('selected-photos'):
            selected_photos_ids = data['selected-photos'].split(',')[1:]
            col.add_photos_to_collection(selected_photos_ids)

            views_attached_to_col = FilterView.objects.filter(collection=col)
            for view in views_attached_to_col:
                view.filter_by_view()
        elif data.get('remove-selected-photos'):
            selected_photos_ids = data['remove-selected-photos'].split(',')[1:]
            col.remove_photos_from_collection(selected_photos_ids)

            views_attached_to_col = FilterView.objects.filter(collection=col)
            for view in views_attached_to_col:
                view.filter_by_view()

        elif data.get('unshare_with'):
            u_id = int(data.get('unshare_with'))
            user = User.objects.get(id=u_id)
            col.unshare_with(user)
            return JsonResponse({})

        elif data.get('share_with'):
            username = data.get('share_with')
            user = User.objects.get(username=username)
            col.share_with(user)
            return JsonResponse({})

        return redirect('shared_photo_library:collection_detail', id=col_id)


class Filter(LoginRequiredMixin, View):
    def get(self, request):
        logged_in_user = request.user
        users_views = list(FilterView.objects.filter(owner=logged_in_user).annotate(photo_number=Count('photos')))
        shared_views = list(FilterView.objects.filter(shared_users=logged_in_user).annotate(photo_number=Count('photos')))
        views = users_views + shared_views
        # return render(request, 'shared_photo_library/filter_views.html',
        #               {'user': logged_in_user, 'users_views': users_views, 'shared_views': shared_views,
        #               'views': views})

        return render(request, 'shared_photo_library/views.html',
                      {'user': logged_in_user, 'users_views': users_views, 'shared_views': shared_views,
                       'views': views})

    def post(self, request):
        data = request.POST.dict()
        # print(data)
        col_id = int(data.get('col_id'))
        col = Collection.objects.get(id=col_id)
        user = request.user
        if col.owner != user and (user not in col.shared_users.all()):
            return HttpResponse(f"You don't have permission to create view for the collection = {col.collection_name}",
                                status=403)
        if data.pop('create'):
            view = FilterView(owner=request.user, collection=col)
            view.update_view(data)

            return redirect('shared_photo_library:view_detail', id=view.id)
        return redirect('shared_photo_library:views')


class FilterViewDetail(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        logged_in_user = request.user
        view_id = int(kwargs['id'])
        view = FilterView.objects.get(id=view_id)
        photos = view.photos.all().order_by('-added_time')
        photos = photo_tags_as_list(photos)
        filter_tags = view.collection.get_filter_tags()

        # users that view can be shared with
        not_shared_users = [user.username for user in User.objects.all().exclude(shared_views=view)]

        # users that collection already shared with
        shared_users = {user.username: user for user in User.objects.filter(shared_views=view)}
        # return render(request, 'shared_photo_library/filter_view_detail.html',
        #               {'user': logged_in_user, 'photos': photos, 'view': view, 'filter_tags': filter_tags,
        #                'not_shared_users': not_shared_users, 'shared_users': shared_users})

        return render(request, 'shared_photo_library/view_detail.html',
                      {'user': logged_in_user, 'photos': photos, 'view': view, 'filter_tags': filter_tags,
                       'not_shared_users': not_shared_users, 'shared_users': shared_users})

    def post(self, request, **kwargs):
        data = request.POST.dict()
        # print(data)
        logged_in_user = request.user
        view_id = int(kwargs['id'])
        view = FilterView.objects.get(id=view_id)
        col = view.collection

        if col.owner != logged_in_user and (logged_in_user not in col.shared_users.all()):
            return HttpResponse(f"You don't have permission to see the view for the collection = {col.collection_name}",
                                status=403)

        if data.get('share-with'):
            username = data.get('share-with')
            user = User.objects.get(username=username)
            view.share_with(user)

        elif data.get('unshare-with'):
            u_id = int(data.get('unshare-with'))
            user = User.objects.get(id=u_id)
            view.unshare_with(user)

        else:  # set filter form submitted to update view filters
            view.update_view(data)
        return redirect('shared_photo_library:view_detail', id=view_id)


class GetNotifications(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        print(request.user)

    def post(self, request, **kwargs):
        print(request.user)
        data = json.load(request)
        data = json.loads(data)
        print("heyyyoo data: ", data)
        if data['change'] == "col":
            col_id = int(data['id'])
            col = Collection.objects.get(id=col_id)
            if data['type'] == "unshare":
                col_id = int(data['id'])
                col = Collection.objects.get(id=col_id)
                notification = f"Collection {col.collection_name} unshared with you."
                return JsonResponse({'change': True, 'notification': notification, 'type': data['type'],
                                     'id': col.id})
            if request.user in col.shared_users.all() or request.user == col.owner:
                if request.user.id != int(data['change_by']):
                    if data['type'] == "remove":
                        notification = f"{User.objects.get(id=int(data['change_by'])).username} removed a photo from the collection {col.collection_name}"
                        return JsonResponse({'change': True, 'notification': notification, 'ph_id': data['ph_id'], 'type': data['type']})
                    elif data['type'] == "add":
                        print("add here")
                        notification = f"{User.objects.get(id=int(data['change_by'])).username} added a photo to the collection {col.collection_name}"
                        res = {**{'change': True, 'notification': notification, 'type': data['type']}, **data['meta_data']}
                        print("res here: ", res)
                        return JsonResponse(res)
                    elif data['type'] == "share":
                        print(data)
                        col_id = int(data['id'])
                        col = Collection.objects.get(id=col_id)
                        notification = f"{User.objects.get(id=int(data['change_by'])).username} shared the collection {col.collection_name} with {data['shared_with']}"
                        return JsonResponse({'change': True, 'notification': notification, 'type': data['type'],
                                             'collection_name': col.collection_name, 'date': str(col.created_date),
                                             'created_by': col.owner.username, 'url': col.cover.url, 'id': col.id})



        else:  # there are changes in the view
            pass

        return JsonResponse({'change': False, 'notification': ""})






from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from exif import Image
# Create your models here.
import datetime
import pytz

utc = pytz.UTC


class Photo(models.Model):
    photo = models.ImageField(blank=True)
    location = models.CharField(max_length=100, null=True)
    date = models.DateTimeField(null=True)
    tags = models.CharField(max_length=100, null=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    added_time = models.DateTimeField(default=timezone.now)

    def load_meta_data(self):
        img = Image(self.photo.open(mode='rb'))  # open img in binary mode to get meta data using exif
        self.tags = ""
        self.location = "-"
        if img.has_exif:
            date = img.get('datetime')
            if date:
                dates = date.split(" ")
                yymmdd = [int(x) for x in dates[0].split(":")]
                saat = [int(x) for x in dates[1].split(":")]
                self.date = datetime.datetime(*(yymmdd + saat))
                # print(self.date, "date")

            latitude = img.get('gps_latitude')
            longitude = img.get('gps_longitude')

            # if gps info exists, set location attribute of object
            if longitude and latitude:
                self.location = (longitude, latitude)

        self.save()

    def add_tags(self, tags):
        self.tags = tags
        self.save()

    def add_location(self, loc):
        self.location = loc
        self.save()

    def add_date(self, date):
        if date == '-' or date == "":
            self.date = None
        else:
            date_list = date.split("-")
            yyyy_mm_dd = [int(x) for x in date_list]
            self.date = datetime.datetime(*yyyy_mm_dd)
        self.save()

    def remove_attr(self, attr):
        if attr == 'loc':
            self.location = None
        elif attr == 'date':
            self.date = None
        self.save()


def photo_tags_as_list(photos):
    for ph in photos:
        ph.tags = ph.tags.split(',')
    return photos


class Collection(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='col_owner')
    collection_name = models.CharField(max_length=100)
    shared_users = models.ManyToManyField(User, related_name='shared_collections')
    cover = models.ImageField(default='empty_col.jpg')
    created_date = models.DateTimeField(default=timezone.now)
    photos = models.ManyToManyField(Photo, related_name='col_photos')

    def remove_photo_from_collection(self, photo):
        self.photos.remove(photo)
        self.save()

    def add_photo_to_collection(self, photo):
        self.photos.add(photo)
        self.cover = photo.photo
        self.save()

    def add_photos_to_collection(self, photos_ids):
        photos_to_be_added = []
        # photo objects are kept in dictionary to avoid cost of fetching from database in loop
        all_photos = {ph.id: ph for ph in Photo.objects.all().order_by('-added_time')}
        cover_id = list(all_photos.keys())[0]
        print(cover_id)
        for ph_id in photos_ids:
            photos_to_be_added.append(all_photos[int(ph_id)])
        self.photos.add(*photos_to_be_added)
        self.cover = all_photos[cover_id].photo
        self.save()

    def remove_photos_from_collection(self, photos_ids):
        photos_to_be_removed = []
        # photo objects are kept in dictionary to avoid cost of fetching from database in loop
        all_photos = {ph.id: ph for ph in Photo.objects.all()}
        for ph_id in photos_ids:
            photos_to_be_removed.append(all_photos[int(ph_id)])
        self.photos.remove(*photos_to_be_removed)
        self.save()

    def unshare_with(self, user):
        self.shared_users.remove(user)
        self.save()

    def share_with(self, user):
        self.shared_users.add(user)
        self.save()

    def get_filter_tags(self):
        photos = self.photos.all()
        photos = photo_tags_as_list(photos)
        filter_tags = set()
        for ph in photos:
            if ph.tags != ['']:
                filter_tags = filter_tags.union(set(ph.tags))
        return filter_tags


class FilterView(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='view_owner')
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='attached_to')
    view_name = models.CharField(max_length=100)
    shared_users = models.ManyToManyField(User, related_name='shared_views')
    tags = models.CharField(max_length=100, null=True)
    conjunctive = models.BooleanField(default=False)
    login_required = models.BooleanField(default=True)
    location_rect = models.CharField(max_length=100, null=True)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    created_date = models.DateTimeField(default=timezone.now)
    photos = models.ManyToManyField(Photo, related_name='view_photos')
    cover = models.ImageField(default='empty_col.jpg')

    def unshare_with(self, user):
        self.shared_users.remove(user)
        self.save()

    def share_with(self, user):
        self.shared_users.add(user)
        self.save()

    def filter_by_view(self):
        self.photos.clear()
        self.save()
        # print(self.start_time, "start_time")
        # print(self.end_time, "end_time")
        # print(self.tags, "tags")
        col_photos = self.collection.photos.all()
        orj_photos = {ph.id: ph for ph in col_photos}
        col_photos = photo_tags_as_list(col_photos)
        filter_tags = self.tags
        if filter_tags:
            filter_tags = filter_tags.split(',')
            # print(filter_tags)
            if len(filter_tags) > 1 and filter_tags[0] == "":
                filter_tags = filter_tags[1:]
            # print(filter_tags)
            # print(filter_tags, " if icinde filter tags")
        # print(filter_tags, " if cikisi filter tags")
        for ph in col_photos:
            # print(ph.tags, "photo tags")
            if ph.date:
                ph.date = ph.date.replace(tzinfo=utc)
            if self.start_time:
                self.start_time = self.start_time.replace(tzinfo=utc)
                if ph.date and ph.date < self.start_time:
                    continue
            if self.end_time:
                self.end_time = self.end_time.replace(tzinfo=utc)
                if ph.date and ph.date > self.end_time:
                    continue
            if self.location_rect and self.location_rect != "-":
                filter_loc = eval(self.location_rect)
                if ph.location and ph.location != "-":
                    photo_loc = eval(ph.location)
                    if (filter_loc[0] > photo_loc[0]) or (filter_loc[1] < photo_loc[0]) or (filter_loc[2] > photo_loc[1]) or (filter_loc[3] < photo_loc[1]):
                        continue
            if filter_tags:
                if self.conjunctive:  # take photo if it contains at least one of the filter tags
                    # print("im here")
                    contains_one_tag = False
                    for ph_tag in ph.tags:
                        # print("ph_tag--->", ph_tag, "---->filter tags--->", filter_tags)
                        if ph_tag in filter_tags:
                            contains_one_tag = True
                            break
                    if not contains_one_tag:
                        continue
                else:
                    contains_all = True
                    for filter_tag in filter_tags:
                        # print(filter_tag, ph.tags)
                        if filter_tag not in ph.tags:
                            contains_all = False
                    if not contains_all:
                        continue

            self.photos.add(orj_photos[ph.id])
        ph = self.photos.all().last()
        if ph:
            self.cover = ph.photo
        self.save()

    def update_view(self, data):
        tags = data.pop('filter-tags')
        # print(tags)
        conj = False

        if data.pop('conj') == "true":
            conj = True
        start_time = None
        if data.get('start_time') != '-':
            yymmdd = [int(x) for x in data['start_time'].split("-")]
            start_time = datetime.datetime(*yymmdd)
        end_time = None
        if data.get('end_time') != '-':
            yymmdd = [int(x) for x in data['end_time'].split("-")]
            end_time = datetime.datetime(*yymmdd)

        self.view_name = data['view_name']
        self.tags = tags
        self.conjunctive = conj
        self.location_rect = data['location_rect']
        self.start_time = start_time
        self.end_time = end_time

        self.save()
        self.filter_by_view()




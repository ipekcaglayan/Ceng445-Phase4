from django import forms
from .models import *


class AddPhoto(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['photo']


class CreateCollection(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['collection_name']


class CreateView(forms.ModelForm):
    class Meta:
        model = FilterView
        fields = ['view_name', 'location_rect', 'start_time', 'end_time']


